"""Pure probe-forms/1 codecs. No host evaluation, I/O, imports from source, or repinning.

The existing L2 checker/evaluator remains the semantic boundary. Input arguments
are handed straight to L2; this module never traverses or copies them.
"""
from __future__ import annotations
import json
import re
import bagaev_l2 as l2

VERSION = 'probe-forms/1'
FORMS = ('json', 'sexpr', 'familiar')
OPS = frozenset(('literal var let call if and or not object set array get has null '
                 'shape int.range text array.bound eq lt length map all any unique '
                 'sort increasing sort.by').split())
FUNCTIONS = {'l2_' + op.replace('.', '_'): op for op in OPS}
BYTE_LIMIT, DEPTH_LIMIT, VALUE_LIMIT = 1048576, 256, 32768
WS = ' \t\r\n'
NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', re.ASCII)
NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_.]*', re.ASCII)

class FormError(ValueError):
    def __init__(self, code, location=''):
        self.code, self.location = code, location
        super().__init__(code)

def _need(test, code='FORM_SYNTAX'):
    if not test:
        raise FormError(code)

def _mode(form, mode):
    _need(type(form) is str and form in FORMS, 'FORM_VERSION')
    _need(type(mode) is str and mode in ('program', 'patch'), 'FORM_SHAPE')

def _text(source):
    _need(type(source) in (str, bytes))
    try:
        raw = source.encode('utf-8') if type(source) is str else source
        _need(len(raw) <= BYTE_LIMIT, 'FORM_BOUNDS')
        result = raw.decode('utf-8')
    except UnicodeError:
        raise FormError('FORM_SYNTAX') from None
    _need(not result.startswith('\ufeff'))
    return result

def _integer(token):
    """Exact bounded decimal conversion, without changing Python global limits."""
    negative = token.startswith('-')
    digits = token[1:] if negative else token
    def convert(part):
        if len(part) <= 1000:
            return int(part)
        middle = len(part) // 2
        return convert(part[:middle]) * 10 ** (len(part) - middle) + convert(part[middle:])
    value = convert(digits)
    return -value if negative else value

def _number(token):
    return float(token) if any(c in token for c in '.eE') else _integer(token)

def _json_exact(source, *, text_limit=True):
    # First retain the existing JSON transport/error-priority gate. Its integer
    # representatives are sufficient for L2 checking but not a lossless codec.
    value = l2._parse(source, text_limit=text_limit)
    text = source.decode('utf-8') if type(source) is bytes else source
    if re.search(r'[0-9]{21}', text) is None:
        return value
    decoder = json.JSONDecoder()
    def numbers():
        pos = 0
        while pos < len(text):
            char = text[pos]
            if char == '"':
                _, pos = decoder.raw_decode(text, pos)
            elif char == '-' or '0' <= char <= '9':
                match = NUMBER.match(text, pos)
                yield match.group()
                pos = match.end()
            else:
                pos += 1
    tokens = iter(numbers())
    box = [value]
    pending = [(box, 0)]
    while pending:
        parent, key = pending.pop()
        item = parent[key]
        if type(item) is dict:
            pending.extend((item, k) for k in reversed(item))
        elif type(item) is list:
            pending.extend((item, i) for i in range(len(item)-1, -1, -1))
        elif type(item) in (int, float):
            token = next(tokens)
            parent[key] = _number(token)
    assert next(tokens, None) is None
    return box[0]

class _Reader:
    def __init__(self, source, form, mode):
        self.source, self.form, self.mode = source, form, mode
        self.pos = self.count = 0
        self.decoder = json.JSONDecoder()

    def ws(self):
        while self.pos < len(self.source) and self.source[self.pos] in WS:
            self.pos += 1

    def peek(self, token):
        self.ws()
        return self.source.startswith(token, self.pos)

    def take(self, token):
        _need(self.peek(token))
        self.pos += len(token)

    def name(self):
        self.ws()
        match = NAME.match(self.source, self.pos)
        _need(match is not None)
        self.pos = match.end()
        return match.group()

    def string(self):
        self.ws()
        _need(self.pos < len(self.source) and self.source[self.pos] == '"')
        try:
            value, self.pos = self.decoder.raw_decode(self.source, self.pos)
        except (ValueError, RecursionError):
            raise FormError('FORM_SYNTAX') from None
        _need(type(value) is str)
        return value

    def boundary(self):
        if self.pos < len(self.source):
            allowed = WS + ('()' if self.form == 'sexpr' else ',)]}')
            _need(self.source[self.pos] in allowed)

    def scalar(self):
        self.ws()
        if self.peek('"'):
            value = self.string()
            self.boundary()
            return value
        literals = (('null', None), ('true', True), ('false', False)) if self.form == 'sexpr' else (('None', None), ('True', True), ('False', False))
        for word, value in literals:
            if self.source.startswith(word, self.pos):
                self.pos += len(word)
                self.boundary()
                return value
        match = NUMBER.match(self.source, self.pos)
        _need(match is not None)
        self.pos = match.end()
        self.boundary()
        return _number(match.group())

    def value(self, depth=1, context='root'):
        self.ws()
        _need(self.pos < len(self.source))
        self.count += 1
        _need(depth <= DEPTH_LIMIT and self.count <= VALUE_LIMIT, 'FORM_BOUNDS')
        if self.form == 'sexpr':
            if not self.peek('('):
                return self.scalar()
            self.take('(')
            op = self.name()
            self.boundary()
            _need(op in OPS or op in ('arr', 'obj'))
            if op == 'obj':
                result = {}
                while not self.peek(')'):
                    self.take('(')
                    key = self.string()
                    self.boundary()
                    _need(key not in result)
                    result[key] = self.value(depth + 1, 'normal')
                    self.take(')')
                self.take(')')
                return result
            result = [] if op == 'arr' else [op]
            while not self.peek(')'):
                result.append(self.value(depth + 1, 'normal'))
            self.take(')')
            return result
        if self.peek('['):
            self.take('[')
            return self.sequence(']', depth, 'normal')
        if self.peek('{'):
            self.take('{')
            result = {}
            if self.peek('}'):
                self.take('}')
                return result
            while True:
                key = self.string()
                _need(key not in result)
                self.take(':')
                child = 'def' if context == 'defs' else 'normal'
                maps = ('definitions',) if self.mode == 'program' else ('add', 'replace')
                if context == 'root' and key in maps:
                    child = 'defs'
                result[key] = self.value(depth + 1, child)
                if self.peek('}'):
                    self.take('}')
                    return result
                self.take(',')
                _need(not self.peek('}'))
        if self.peek('l2_'):
            name = self.name()
            self.take('(')
            if name in ('l2_program', 'l2_def'):
                if name == 'l2_program':
                    _need(context == 'root' and self.mode == 'program')
                    keys = ('entry', 'definitions', 'pins')
                    result = {'schema': l2.PROGRAM_SCHEMA}
                else:
                    _need(context == 'def')
                    keys = ('params', 'body')
                    result = {}
                for i, key in enumerate(keys):
                    if i:
                        self.take(',')
                    _need(self.name() == key)
                    self.take('=')
                    result[key] = self.value(depth + 1, 'defs' if key == 'definitions' else 'normal')
                self.take(')')
                return result
            _need(name in FUNCTIONS)
            return [FUNCTIONS[name], *self.sequence(')', depth, 'normal')]
        return self.scalar()

    def sequence(self, end, depth, context):
        values = []
        if self.peek(end):
            self.take(end)
            return values
        while True:
            values.append(self.value(depth + 1, context))
            if self.peek(end):
                self.take(end)
                return values
            self.take(',')
            _need(not self.peek(end))

    def read(self):
        result = self.value()
        self.ws()
        _need(self.pos == len(self.source))
        return result

def decode(source, form='json', *, mode='program'):
    """Recover data, without checking semantics or repairing pins.

    JSON deliberately retains the existing L2 parser and its error codes/order.
    Other source forms enforce grammar-value depth/count before further descent.
    """
    _mode(form, mode)
    if form == 'json':
        return _json_exact(source)
    return _Reader(_text(source), form, mode).read()

def _quote(value, *, integer_byte_limit=BYTE_LIMIT):
    # Valid Unicode scalars use canonical JSON; isolated surrogate code units
    # stay escaped for the unchanged L2 semantic checker to reject in context.
    if type(value) is int:
        _need(value.bit_length() <= integer_byte_limit * 4, 'FORM_BOUNDS')
        def decimal(n):
            if n.bit_length() <= 3300:
                return str(n)
            width = (n.bit_length() * 30103 // 100000) // 2
            high, low = divmod(n, 10 ** width)
            return decimal(high) + decimal(low).zfill(width)
        return ('-' if value < 0 else '') + decimal(abs(value))
    result = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return ''.join('\\u%04x' % ord(c) if 0xd800 <= ord(c) <= 0xdfff else c for c in result)

def encode(value, form='json', *, mode='program'):
    """Canonical exact form for program/patch data; no implicit semantic check."""
    _mode(form, mode)
    if form == 'json':
        # Validate only JSON representation/resource shape, never L2 semantics.
        pending = [(value, 1, frozenset())]
        occurrences = size = 0
        while pending:
            item, depth, parents = pending.pop()
            occurrences += 1
            _need(depth <= DEPTH_LIMIT and occurrences <= VALUE_LIMIT, 'FORM_BOUNDS')
            kind = type(item)
            _need(kind in (dict, list, str, int, bool, float, type(None)), 'FORM_SHAPE')
            if kind in (dict, list):
                _need(id(item) not in parents, 'FORM_SHAPE')
                ancestors = parents | {id(item)}
                _need(len(item) <= VALUE_LIMIT - occurrences, 'FORM_BOUNDS')
                size += 2 + max(0, len(item) - 1)
                if kind is dict:
                    _need(all(type(k) is str for k in item), 'FORM_SHAPE')
                    for key in item:
                        _need(len(key) <= BYTE_LIMIT, 'FORM_BOUNDS')
                        size += len(_quote(key).encode('utf-8')) + 1
                    children = item.values()
                else:
                    children = item
                _need(size <= BYTE_LIMIT, 'FORM_BOUNDS')
                pending.extend((x, depth + 1, ancestors) for x in children)
            else:
                if kind is str:
                    _need(len(item) <= BYTE_LIMIT, 'FORM_BOUNDS')
                try:
                    size += len(_quote(item).encode('utf-8'))
                except FormError:
                    raise
                except (ValueError, TypeError):
                    raise FormError('FORM_SHAPE') from None
            _need(size <= BYTE_LIMIT, 'FORM_BOUNDS')
        def render_json(item):
            if type(item) is dict:
                return '{' + ','.join(_quote(k) + ':' + render_json(item[k]) for k in sorted(item)) + '}'
            if type(item) is list:
                return '[' + ','.join(render_json(x) for x in item) + ']'
            return _quote(item)
        try:
            result = render_json(value).encode('utf-8')
        except FormError:
            raise
        except (ValueError, TypeError, RecursionError):
            raise FormError('FORM_SHAPE') from None
        _need(len(result) <= BYTE_LIMIT, 'FORM_BOUNDS')
        return result
    count = 0
    scalar_bytes = 0
    def scalar_text(item):
        nonlocal scalar_bytes
        if type(item) is str:
            _need(len(item) <= BYTE_LIMIT, 'FORM_BOUNDS')
        text = _quote(item)
        scalar_bytes += len(text.encode('utf-8'))
        _need(scalar_bytes <= BYTE_LIMIT, 'FORM_BOUNDS')
        return text
    def render(item, depth=1, context='root', parents=frozenset()):
        nonlocal count
        count += 1
        _need(depth <= DEPTH_LIMIT and count <= VALUE_LIMIT, 'FORM_BOUNDS')
        kind = type(item)
        _need(kind in (dict, list, str, int, bool, float, type(None)), 'FORM_SHAPE')
        if kind not in (dict, list):
            if form == 'familiar' and (item is None or kind is bool):
                return 'None' if item is None else 'True' if item else 'False'
            try:
                return scalar_text(item)
            except FormError:
                raise
            except (ValueError, TypeError):
                raise FormError('FORM_SHAPE') from None
        _need(id(item) not in parents, 'FORM_SHAPE')
        parents = parents | {id(item)}
        def child(x, ctx='normal'):
            return render(x, depth + 1, ctx, parents)
        if kind is list:
            op = item[0] if item and type(item[0]) is str and item[0] in OPS else None
            body = item[1:] if op else item
            parts = [child(x) for x in body]
            if form == 'sexpr':
                return '(' + ' '.join([op or 'arr', *parts]) + ')'
            return ('l2_' + op.replace('.', '_') + '(' if op else '[') + ', '.join(parts) + (')' if op else ']')
        _need(all(type(k) is str for k in item), 'FORM_SHAPE')
        if form == 'sexpr':
            return '(obj' + ''.join(' (' + scalar_text(k) + ' ' + child(item[k]) + ')' for k in sorted(item)) + ')'
        if context == 'root' and mode == 'program' and set(item) == {'schema','entry','definitions','pins'} and type(item['schema']) is str and item['schema'] == l2.PROGRAM_SCHEMA:
            return 'l2_program(entry=' + child(item['entry']) + ', definitions=' + child(item['definitions'], 'defs') + ', pins=' + child(item['pins']) + ')'
        if context == 'def' and set(item) == {'params', 'body'}:
            return 'l2_def(params=' + child(item['params']) + ', body=' + child(item['body']) + ')'
        maps = ('definitions',) if mode == 'program' else ('add', 'replace')
        parts = []
        for k in sorted(item):
            ctx = 'def' if context == 'defs' else 'defs' if context == 'root' and k in maps else 'normal'
            parts.append(scalar_text(k) + ': ' + child(item[k], ctx))
        return '{' + ', '.join(parts) + '}'
    result = render(value).encode('utf-8')
    _need(len(result) <= BYTE_LIMIT, 'FORM_BOUNDS')
    return result

def check(source, form='json'):
    value = decode(source, form)
    # A reconstructed string is DATA, never a second source document. The
    # normative first semantic gate requires an object before checking fields.
    if type(value) is not dict:
        raise l2.L2Error('L2_PROGRAM')
    return l2.check_program(value)

def evaluate(source, argument, form='json'):
    """Borrow argument directly; no inspection, copying, hashing or normalization."""
    return l2.evaluate(check(source, form), argument)
