"""Data-only form5 expression source map; no evaluation or execution admission."""
from array import array
from bisect import bisect_right
import hashlib
import json
import re
import bagaev_record_wide_form as form
from bagaev_record_draft import digest

HEADER = re.compile(r'\A[ \t\r\n]*bagaev[ \t\r\n]+record-form/([A-Za-z0-9_]+)[ \t\r\n]*;')


class _Node(tuple):
    """A distinct parse occurrence, even for equal or interned literal tuples."""
    def __new__(cls, value, span):
        obj = super().__new__(cls, value)
        obj.span = span
        return obj


class _Reader(form.Reader):
    def __init__(self, source):
        super().__init__(source)
        text = source.decode('utf8') if type(source) is bytes else source
        self.ranges = []
        tokens = []
        pos = HEADER.match(text).end()
        while pos < len(text):
            if text[pos] in form.old.WS:
                pos += 1
                continue
            match = form.TOKEN.match(text, pos)
            form.need(match is not None, 'SPAN_TOKENS')
            tokens.append(match[0])
            self.ranges.append((pos, match.end()))
            pos = match.end()
        form.need(tokens == self.tokens, 'SPAN_TOKENS')
        self.locations = {}
        self.parents = []

    def _capture(self, method, depth):
        start = self.pos
        node = method(depth)
        form.need(self.pos > start, 'SPAN_TOKENS')
        return _Node(node, (self.ranges[start][0], self.ranges[self.pos - 1][1]))

    def expression(self, depth=1):
        return self._capture(super().expression, depth)

    def sum(self, depth):
        return self._capture(super().sum, depth)

    def product(self, depth):
        return self._capture(super().product, depth)

    def atom(self, depth):
        return self._capture(super().atom, depth)

    def lower(self, node, scope=frozenset(), depth=1):
        exact = isinstance(node, _Node)
        span = node.span if exact else self.parents[-1]
        self.parents.append(span)
        try:
            value = super().lower(node, scope, depth)
        finally:
            self.parents.pop()
        self.locations[id(value)] = (value, span, 'exact-expression' if exact else 'enclosing-expression')
        form.need(len(self.locations) <= 2048, 'SPAN_BOUNDS')
        return value


def source_map(source):
    """Return layout-bound expression ranges, not semantic/native validation."""
    expected = form.decode(source)
    try:
        reader = _Reader(source)
        graph = reader.read()
    except RecursionError:
        raise form.FormError('FORM_BOUNDS') from None
    form.need(graph == expected, 'SPAN_GRAPH')
    raw = source.encode('utf8') if type(source) is str else source
    text = raw.decode('utf8')
    offsets = array('I', [0])
    lines = [0]
    for index, char in enumerate(text):
        offsets.append(offsets[-1] + len(char.encode('utf8')))
        if char == '\n':
            lines.append(index + 1)
    def point(index):
        line = bisect_right(lines, index)
        return line, index - lines[line - 1] + 1
    entries = []
    def walk(value, pointer):
        if type(value) is list:
            item = reader.locations.get(id(value))
            if item is not None:
                form.need(item[0] is value, 'SPAN_GRAPH')
                start, end = item[1]
                sl, sc = point(start)
                el, ec = point(end)
                entries.append(dict(program_pointer=pointer, operation=value[0], precision=item[2],
                                    start_byte=offsets[start], end_byte=offsets[end],
                                    start_line=sl, start_column=sc, end_line=el, end_column=ec))
            for index, child in enumerate(value):
                if type(child) is list:
                    walk(child, pointer + '/' + str(index))
    for name, function in graph['functions'].items():
        walk(function['body'], '/program/functions/' + name + '/body')
    form.need(len(entries) == len(reader.locations), 'SPAN_GRAPH')
    result = dict(schema='bagaev-record-source-map/1', form='record-form/5',
                  source_sha256=hashlib.sha256(raw).hexdigest(), program_pin='sha256:' + digest(graph),
                  semantic_check=False, execution_admission=False,
                  locations=sorted(entries, key=lambda item: item['program_pointer']))
    form.need(len(json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode('utf8')) <= 1048576,
              'SPAN_BOUNDS')
    return result
