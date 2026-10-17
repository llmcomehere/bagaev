"""Lossless bounded JSON views; no language checking, execution or admission."""
import json
from types import MappingProxyType

BYTE_LIMIT = 1048576
DEPTH_LIMIT = 128
VALUE_LIMIT = 16384
_MISSING = object()


class JsonInputError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class _Integer(str):
    pass


class _Number(str):
    pass


def _key(value):
    if type(value) is not str:
        raise JsonInputError('JP_INPUT')
    try:
        if len(value.encode('utf-8')) > 64:
            raise JsonInputError('JP_INPUT')
    except UnicodeError:
        raise JsonInputError('JP_INPUT') from None
    return value


class View:
    """Opaque API view over immutable values; not a Python security boundary."""
    __slots__ = ('__value',)

    def __init__(self, value):
        self.__value = value

    def kind(self):
        v = self.__value
        if v is _MISSING:
            return 'missing'
        if v is None:
            return 'null'
        return {bool:'bool', _Integer:'int', _Number:'number', str:'text',
                tuple:'array', MappingProxyType:'object'}[type(v)]

    def integer(self):
        v = self.__value
        if type(v) is not _Integer or len(v) > 20:
            return None
        n = int(v)
        return n if -(1 << 63) <= n < (1 << 63) else None

    def int_charge(self):
        v = self.__value
        return len(v) if type(v) is _Integer else 0

    def text(self):
        v = self.__value
        return v if type(v) is str and len(v) <= 256 and len(v.encode('utf-8')) <= 1024 else None

    def text_bytes(self):
        v = self.text()
        return None if v is None else len(v.encode('utf-8'))

    def length(self):
        v = self.__value
        return len(v) if type(v) in (tuple, MappingProxyType) else None

    def boolean(self):
        v = self.__value
        return v if type(v) is bool else None

    def field(self, key):
        key = _key(key)
        v = self.__value
        return View(v.get(key, _MISSING) if type(v) is MappingProxyType else _MISSING)

    def field_charge(self, key):
        key = _key(key)
        v = self.__value
        return len(v) * (len(key.encode('utf-8')) + 1) if type(v) is MappingProxyType else 0

    def at(self, index):
        if type(index) is not int or not -(1 << 63) <= index < (1 << 63):
            raise JsonInputError('JP_INPUT')
        v = self.__value
        return View(v[index] if type(v) is tuple and 0 <= index < len(v) else _MISSING)


def parse(raw):
    if type(raw) is not bytes:
        raise JsonInputError('JP_INPUT')
    if len(raw) > BYTE_LIMIT:
        raise JsonInputError('JP_BOUNDS')
    depth = 0
    quoted = escaped = False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > DEPTH_LIMIT:
                raise JsonInputError('JP_BOUNDS')
        elif byte in (93, 125):
            depth -= 1

    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('duplicate key')
            value[key] = item
        return value

    def constant(_):
        raise ValueError('non-JSON number')

    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_int=_Integer, parse_float=_Number,
                           parse_constant=constant)
        pending = [value]
        while pending:
            item = pending.pop()
            if type(item) is str:
                item.encode('utf-8')
            elif type(item) is list:
                pending.extend(item)
            elif type(item) is dict:
                for key in item:
                    key.encode('utf-8')
                pending.extend(item.values())
    except (ValueError, UnicodeError, RecursionError):
        raise JsonInputError('JP_FORMAT') from None

    count = 0
    pending = [value]
    while pending:
        item = pending.pop()
        count += 1
        if count > VALUE_LIMIT:
            raise JsonInputError('JP_BOUNDS')
        if type(item) is list:
            pending.extend(item)
        elif type(item) is dict:
            pending.extend(item.values())

    def immutable(item):
        if type(item) is list:
            return tuple(immutable(v) for v in item)
        if type(item) is dict:
            return MappingProxyType({k:immutable(v) for k,v in item.items()})
        return item
    return View(immutable(value))
