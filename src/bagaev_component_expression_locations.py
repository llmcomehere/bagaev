"""Source-bound form4 expression contexts; no semantic checking or execution."""
from array import array
from bisect import bisect_right
import hashlib
import json
import re
import bagaev_component_match_form as form

SCHEMA = 'component-form-location/1'
PIN = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)
HEADER = re.compile(r'\A[ \t\r\n]*bagaev[ \t\r\n]+component-form/[A-Za-z0-9_]+[ \t\r\n]*;')

class LocationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

class Reader(form.Reader):
    def __init__(self, source):
        super().__init__(source)
        self.raw = source.encode('utf8') if type(source) is str else source
        self.text = self.raw.decode('utf8')
        self.positions = {}
        self.locations = {}
        self.offsets = []
        cursor = HEADER.match(self.text).end()
        while cursor < len(self.text):
            if self.text[cursor] in form.old.WS:
                cursor += 1
                continue
            token = form.TOKEN.match(self.text, cursor)
            self.offsets.append((token.start(), token.end()))
            cursor = token.end()
        assert len(self.offsets) == len(self.tokens)

    def remember(self, node, start, end):
        # Retain the node itself so object identities cannot be reused.
        self.positions[id(node)] = (node, start, end)
        return node

    def expression(self, depth=1):
        start = self.pos
        return self.remember(super().expression(depth), start, self.pos)

    def atom(self, depth):
        start = self.pos
        node = super().atom(depth)
        chain = []
        inner = node
        while inner[0] == 'field':
            chain.append(inner)
            inner = inner[1]
        if chain and inner[0] == 'arg' and self.tokens[start] == inner[1]:
            self.remember(inner, start, start + 1)
            for index, part in enumerate(reversed(chain), 1):
                self.remember(part, start, start + 1 + 2 * index)
        return self.remember(node, start, self.pos)

    def sum(self, depth):
        start = self.pos
        left = self.product(depth)
        while self.peek() in ('+', '-'):
            op = self.take()
            left = self.remember(('add' if op == '+' else 'sub', left, self.product(depth + 1)), start, self.pos)
        return left

    def product(self, depth):
        start = self.pos
        left = self.atom(depth)
        while self.peek() == '*':
            self.take()
            left = self.remember(('mul', left, self.atom(depth + 1)), start, self.pos)
        return left

    def lower(self, node, scope=frozenset(), depth=1):
        result = super().lower(node, scope, depth)
        if depth == 1:
            name = next(name for name, f in self.functions.items() if f['body'] is node)
            self.map_node(node, '/program/functions/' + name + '/body')
        return result

    def map_node(self, node, pointer):
        # Generated pointer tokens are ASCII identifiers/indices. No admitted
        # query can name a longer path; do not multiply a huge source identifier
        # across every descendant before the independent core rejects it.
        if len(pointer) > 4096:
            return
        position = self.positions.get(id(node))
        if position is not None:
            self.locations[pointer] = position[1:]
        kind = node[0]
        children = []
        if kind in ('add', 'sub', 'mul', 'lt'):
            children = [(node[1], '/1'), (node[2], '/2')]
        elif kind == 'if':
            children = [(node[i], '/' + str(i)) for i in (1, 2, 3)]
        elif kind == 'let':
            children = [(node[2], '/2'), (node[3], '/3')]
        elif kind in ('field', 'unique'):
            children = [(node[1], '/1')]
        elif kind == 'variant':
            children = [(node[3], '/3')]
        elif kind == 'call':
            children = [(child, '/' + str(i + 2)) for i, child in enumerate(node[2])]
        elif kind == 'record':
            children = [(node[2][name], '/' + str(i + 2)) for i, name in enumerate(sorted(node[2]))]
        elif kind == 'match':
            children = [(node[1], '/1')] + [(arm[2], '/2/' + str(i) + '/2') for i, arm in enumerate(node[2])]
        for child, suffix in children:
            self.map_node(child, pointer + suffix)

    def span(self, position):
        start, end = position
        a, b = self.offsets[start][0], self.offsets[end - 1][1]
        byte_offsets = array('I', [0])
        lines = array('I', [0])
        for index, char in enumerate(self.text):
            byte_offsets.append(byte_offsets[-1] + len(char.encode('utf8')))
            if char == '\n':
                lines.append(index + 1)
        sl, el = bisect_right(lines, a), bisect_right(lines, b)
        return {'kind': 'expression', 'start_byte': byte_offsets[a], 'end_byte': byte_offsets[b],
                'start_line': sl, 'start_column': a - lines[sl - 1] + 1,
                'end_line': el, 'end_column': b - lines[el - 1] + 1}

def locate(source, pointer, *, source_sha256, component_sha256):
    if any(type(pin) is not str or PIN.fullmatch(pin) is None for pin in (source_sha256, component_sha256)):
        raise LocationError('LOCATION_PIN')
    try:
        valid_pointer = type(pointer) is str and len(pointer.encode('utf8')) <= 4096 and (not pointer or pointer.startswith('/')) and re.search(r'~(?![01])', pointer) is None
    except UnicodeError:
        valid_pointer = False
    if not valid_pointer:
        raise LocationError('LOCATION_POINTER')
    try:
        reader = Reader(source)
        if hashlib.sha256(reader.raw).hexdigest() != source_sha256:
            raise LocationError('LOCATION_SOURCE')
        component = reader.read()
        raw = json.dumps(component, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf8')
        if hashlib.sha256(raw).hexdigest() != component_sha256:
            raise LocationError('LOCATION_COMPONENT')
        position = reader.locations.get(pointer)
        return {'schema': SCHEMA, 'form': 'component-form/4', 'source_sha256': source_sha256,
                'component_sha256': component_sha256, 'pointer': pointer,
                'span': reader.span(position) if position is not None else None,
                'semantic_check': False, 'execution_admission': False}
    except RecursionError:
        raise form.FormError('FORM_BOUNDS') from None
