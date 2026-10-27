"""Independent DATA reference algorithms; never import the tested engine.

This reference uses plain JSON values and a generator of deferred Work actions.
A driver checks cancellation and budget before executing each action. It has no
imports from the tested engine, frozen CORE, OBS or CALL. Accepted-input semantics
and selected physical boundaries are compared; this is not a second prelaunch
typechecker or a proof of the full language.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from copy import deepcopy
from hashlib import sha256
import json


@dataclass(frozen=True)
class UTF8Failure:
    reason: str
    sequence_start: int
    detected_at: int


def scalar_octets(character: str) -> tuple[int, ...]:
    """Scalar-to-octets arithmetic independent of a host Unicode codec."""
    if len(character) != 1:
        raise ValueError("one Unicode scalar required")
    value = ord(character)
    if 0xD800 <= value <= 0xDFFF or value > 0x10FFFF:
        raise ValueError("not a Unicode scalar")
    if value < 0x80:
        return (value,)
    if value < 0x800:
        return (0xC0 | (value >> 6), 0x80 | (value & 0x3F))
    if value < 0x10000:
        return (0xE0 | (value >> 12), 0x80 | ((value >> 6) & 0x3F),
                0x80 | (value & 0x3F))
    return (0xF0 | (value >> 18), 0x80 | ((value >> 12) & 0x3F),
            0x80 | ((value >> 6) & 0x3F), 0x80 | (value & 0x3F))


def utf8_literal(text: str) -> list[int]:
    """Unmetered reference conversion, only for authored wire-value assertions."""
    return [byte for scalar in text for byte in scalar_octets(scalar)]


def decode_utf8_literal(octets: Iterable[int]) -> tuple[str | None, UTF8Failure | None]:
    """Reference scalar grammar; no replacement, normalization or host decode.

    Both the sequence start and the byte exposing the defect are retained.  The
    public error-offset choice belongs to the exact published DATA operation.
    """
    source = tuple(octets)
    if any(type(byte) is not int or not 0 <= byte <= 255 for byte in source):
        raise ValueError("not a byte sequence")
    result: list[str] = []
    cursor = 0
    while cursor < len(source):
        start = cursor
        lead = source[cursor]
        cursor += 1
        if lead <= 0x7F:
            result.append(chr(lead))
            continue
        if 0xC2 <= lead <= 0xDF:
            length, scalar, minimum = 2, lead & 0x1F, 0x80
        elif 0xE0 <= lead <= 0xEF:
            length, scalar, minimum = 3, lead & 0x0F, 0x800
        elif 0xF0 <= lead <= 0xF4:
            length, scalar, minimum = 4, lead & 0x07, 0x10000
        else:
            return None, UTF8Failure("invalid_lead", start, start)
        for index in range(1, length):
            if cursor == len(source):
                return None, UTF8Failure("truncated", start, cursor)
            byte = source[cursor]
            detected = cursor
            cursor += 1
            if not 0x80 <= byte <= 0xBF:
                return None, UTF8Failure("invalid_continuation", start, detected)
            if index == 1:
                if (lead == 0xE0 and byte < 0xA0) or (lead == 0xF0 and byte < 0x90):
                    return None, UTF8Failure("overlong", start, detected)
                if lead == 0xED and byte > 0x9F:
                    return None, UTF8Failure("surrogate", start, detected)
                if lead == 0xF4 and byte > 0x8F:
                    return None, UTF8Failure("out_of_range", start, detected)
            scalar = (scalar << 6) | (byte & 0x3F)
        if scalar < minimum or 0xD800 <= scalar <= 0xDFFF or scalar > 0x10FFFF:
            raise AssertionError("independent UTF-8 range checks disagree")
        result.append(chr(scalar))
    return "".join(result), None


def unsigned32_octets(value: int) -> tuple[int, ...]:
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("length outside unsigned32")
    return tuple((value >> shift) & 0xFF for shift in (24, 16, 8, 0))


def int64_octets(value: int) -> tuple[int, ...]:
    if type(value) is not int or not -(2 ** 63) <= value < 2 ** 63:
        raise ValueError("not an Int64")
    magnitude = value if value >= 0 else value + 2 ** 64
    return tuple((magnitude >> shift) & 0xFF for shift in range(56, -1, -8))


def unsigned_octets_value(octets: Iterable[int]) -> int:
    result = 0
    for byte in octets:
        if type(byte) is not int or not 0 <= byte <= 255:
            raise ValueError("not a byte")
        result = result * 256 + byte
    return result


def int64_octets_value(octets: Iterable[int]) -> int:
    source = tuple(octets)
    if len(source) != 8:
        raise ValueError("Int64 wire width is eight octets")
    unsigned = unsigned_octets_value(source)
    return unsigned - 2 ** 64 if unsigned >= 2 ** 63 else unsigned


PROFILE_REVISION = "data-core/r07-v1"
CODEC_REVISION = "data-wire/r07-v1"
ERROR_CODES = {"DuplicateKey", "Utf8Leading", "Utf8Continuation", "Utf8Overlong",
               "Utf8Surrogate", "Utf8Range", "Utf8Truncated", "UnexpectedEnd",
               "ContextMismatch", "InvalidEncoding", "UnknownVariant",
               "NonCanonicalMap", "TrailingBytes"}


def canonical_digest(value):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)
    return sha256(text.encode("utf-8")).hexdigest()


def raw_node_count(raw):
    """Objects, arrays and scalar values count once; object keys do not."""
    count, pending = 0, [raw]
    while pending:
        item = pending.pop()
        count += 1
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return count


def result_type(ok, err="DataError"):
    return {"tag": "result", "ok": ok, "err": err}


def option_type(item):
    return {"tag": "option", "item": item}


def value(typ, data):
    return {"type": deepcopy(typ), "data": data}


def substitute(typ, arguments):
    if isinstance(typ, str):
        return typ
    if typ["tag"] == "var":
        return deepcopy(arguments[typ["id"]])
    output = {}
    for key, item in typ.items():
        if key in ("params", "args"):
            output[key] = [substitute(child, arguments) for child in item]
        elif key in ("item", "key", "value", "ok", "err", "result"):
            output[key] = substitute(item, arguments)
        else:
            output[key] = item
    return output


class Registry:
    """Plain authored schema model, independent of the implementation indexes."""
    def __init__(self, schemas):
        self.schemas = deepcopy(schemas)
        self.definitions = {(d["id"], d["revision"]): d for d in self.schemas}
        self.stamp = canonical_digest({"profile_revision": PROFILE_REVISION,
                                       "codec_revision": CODEC_REVISION,
                                       "schemas": self.schemas})

    def type_stamp(self, typ):
        return canonical_digest({"profile_revision": PROFILE_REVISION,
                                 "codec_revision": CODEC_REVISION, "type": typ})

    def header(self, typ):
        return [66, 68, 48, 55, 1] + list(bytes.fromhex(self.stamp + self.type_stamp(typ)))

    def declaration(self, typ):
        return self.definitions[(typ["id"], typ["revision"])]

    def kind(self, typ):
        if isinstance(typ, str):
            return "record" if typ == "DataError" else typ
        if typ["tag"] == "nominal":
            return self.declaration(typ)["kind"]
        return "sum" if typ["tag"] in ("option", "result") else typ["tag"]

    def fields(self, typ):
        if typ == "DataError":
            return [("code", "String"), ("first", "Int64"), ("second", "Int64")]
        declaration = self.declaration(typ)
        environment = dict(zip((p["id"] for p in declaration["type_params"]), typ["args"]))
        return [(p["id"], substitute(p["type"], environment)) for p in declaration["fields"]]

    def variants(self, typ):
        if typ["tag"] == "option":
            return [("None", "Unit"), ("Some", typ["item"])]
        if typ["tag"] == "result":
            return [("Ok", typ["ok"]), ("Err", typ["err"])]
        declaration = self.declaration(typ)
        environment = dict(zip((p["id"] for p in declaration["type_params"]), typ["args"]))
        return [(p["id"], substitute(p["type"], environment)) for p in declaration["variants"]]

    def predicate(self, typ, name):
        kind = self.kind(typ)
        if kind in {"Bool", "Int64", "Unit", "String", "Bytes", "record"} and isinstance(typ, str):
            return True
        if kind in {"fn", "Capability", "HostHandle"}:
            return False
        if kind == "seq":
            return self.predicate(typ["item"], name)
        if kind == "map":
            if name == "Key":
                return False
            return self.predicate(typ["key"], "Key") and self.predicate(typ["value"], name) and (
                name != "Persistable" or self.predicate(typ["key"], "Persistable"))
        if kind in {"record", "sum"}:
            if name == "Persistable" and isinstance(typ, dict) and typ["tag"] == "nominal":
                if self.declaration(typ)["codec"] != CODEC_REVISION:
                    return False
            children = self.fields(typ) if kind == "record" else self.variants(typ)
            return all(self.predicate(child, name) for _, child in children)
        raise ValueError("unsupported oracle predicate type")


class Fault(Exception):
    def __init__(self, code, first, second=-1):
        self.data = {"code": code, "first": first, "second": second}


class Physical(Exception):
    def __init__(self, code):
        self.code = code


@dataclass(frozen=True)
class Work:
    rule: str
    path: tuple
    action: object


def unit(rule, path=(), action=lambda: None):
    answer = yield Work(rule, tuple(path), action)
    return answer


def sign(left, right):
    return (left > right) - (left < right)


class UTF8Cursor:
    """Independent arithmetic DFA; one accept call consumes one charged octet."""
    def __init__(self, absolute_base=0):
        self.base = absolute_base
        self.need = 0
        self.position = 0
        self.start = 0
        self.lead = 0
        self.accumulator = 0
        self.characters = []

    def accept(self, byte, absolute):
        if self.need == 0:
            if byte < 128:
                char = chr(byte)
                if len(self.characters) == 1024:
                    raise Physical("VALUE_LIMIT")
                self.characters.append(char)
                return
            self.start, self.lead, self.position = absolute, byte, 1
            if 0xC2 <= byte <= 0xDF:
                self.need, self.accumulator = 1, byte & 31
            elif 0xE0 <= byte <= 0xEF:
                self.need, self.accumulator = 2, byte & 15
            elif 0xF0 <= byte <= 0xF4:
                self.need, self.accumulator = 3, byte & 7
            else:
                raise Fault("Utf8Leading", absolute)
            return
        if not 0x80 <= byte <= 0xBF:
            raise Fault("Utf8Continuation", absolute)
        if self.position == 1:
            if (self.lead == 0xE0 and byte < 0xA0) or (self.lead == 0xF0 and byte < 0x90):
                raise Fault("Utf8Overlong", absolute)
            if self.lead == 0xED and byte > 0x9F:
                raise Fault("Utf8Surrogate", absolute)
            if self.lead == 0xF4 and byte > 0x8F:
                raise Fault("Utf8Range", absolute)
        accumulator = self.accumulator * 64 + (byte & 63)
        if self.need == 1 and len(self.characters) == 1024:
            raise Physical("VALUE_LIMIT")
        self.accumulator = accumulator
        self.need -= 1
        self.position += 1
        if self.need == 0:
            self.characters.append(chr(self.accumulator))

    def finish(self):
        if self.need:
            raise Fault("Utf8Truncated", self.start)
        return "".join(self.characters)


class Evaluator:
    def __init__(self, job):
        self.job = deepcopy(job)
        self.registry = Registry(job["schemas"])
        self.operation = self.job["operation"]
        self.wire = []
        self.input_wire = []
        self.cursor = 0
        self.output_type = None
        self.wire_limit = 32768
        if self.operation["op"] == "encode":
            prospective = {"source_id": self.job["source_id"], "revision": self.job["revision"],
                           "profile_revision": self.job["profile_revision"],
                           "schemas": self.job["schemas"],
                           "operation": {"op": "decode", "type": self.operation["value"]["type"],
                                         "bytes": {"type": "Bytes", "data": []}}}
            self.wire_limit = min(32768, 65536 - raw_node_count(prospective))

    def compare(self, typ, left, right, path):
        kind = self.registry.kind(typ)
        answer = yield from unit("COMPARE_NODE", path, lambda: self.atomic_compare(kind, typ, left, right))
        if answer is not None:
            return answer
        if kind in ("String", "Bytes"):
            for i in range(min(len(left), len(right))):
                result = yield from unit("COMPARE_UNIT", path + (i,),
                                         lambda i=i: sign(left[i], right[i]))
                if result:
                    return result
            return (yield from unit("COMPARE_END", path, lambda: sign(len(left), len(right))))
        if kind == "seq":
            children = ((typ["item"], left[i], right[i], path + (i,))
                        for i in range(min(len(left), len(right))))
            end = lambda: sign(len(left), len(right))
        elif kind == "record":
            children = ((child, left[name], right[name], path + (name,))
                        for name, child in self.registry.fields(typ))
            end = lambda: 0
        elif kind == "sum":
            tag = left["tag"]
            child = dict(self.registry.variants(typ))[tag]
            children = [(child, left["value"], right["value"], path + (tag,))]
            end = lambda: 0
        elif kind == "map":
            def pairs():
                for i in range(len(left)):
                    for name, child in (("key", typ["key"]), ("value", typ["value"])):
                        yield child, left[i][name], right[i][name], path + (i, name)
            children, end = pairs(), lambda: 0
        else:
            raise ValueError("unsupported oracle comparison")
        for child, a, b, child_path in children:
            yield from unit("COMPARE_NEXT", child_path)
            result = yield from self.compare(child, a, b, child_path)
            if result:
                return result
        return (yield from unit("COMPARE_END", path, end))

    def atomic_compare(self, kind, typ, left, right):
        if kind in ("Bool", "Int64", "Unit"):
            return 0 if kind == "Unit" else sign(left, right)
        if kind == "map" and len(left) != len(right):
            return 1
        if kind == "sum":
            tags = [tag for tag, _ in self.registry.variants(typ)]
            compared = sign(tags.index(left["tag"]), tags.index(right["tag"]))
            return compared if compared else None
        return None

    def write(self, byte, rule="ENCODE_WRITE", root="wire"):
        path = (root, len(self.wire))
        def put():
            limit = self.wire_limit if rule == "ENCODE_WRITE" else 32768
            if len(self.wire) >= limit:
                raise Physical("OUTPUT_LIMIT")
            self.wire.append(byte)
        yield from unit(rule, path, put)

    def write_many(self, octets):
        for byte in octets:
            yield from self.write(byte)

    def encode_node(self, typ, data, path):
        kind = self.registry.kind(typ)
        yield from unit("ENCODE_NODE", path)
        if kind == "Unit":
            return
        if kind == "Bool":
            yield from self.write(1 if data else 0)
            return
        if kind == "Int64":
            yield from self.write_many(int64_octets(data))
            return
        if kind == "String":
            length = 0
            for i, character in enumerate(data):
                length += yield from unit("ENCODE_SCAN", path + (i,),
                                          lambda character=character: len(scalar_octets(character)))
            yield from self.write_many(unsigned32_octets(length))
            for i, character in enumerate(data):
                pending = yield from unit("ENCODE_SCALAR", path + (i,),
                                          lambda character=character: scalar_octets(character))
                yield from self.write_many(pending)
            return
        if kind == "Bytes":
            yield from self.write_many(unsigned32_octets(len(data)))
            yield from self.write_many(data)
            return
        if kind in ("seq", "map"):
            yield from self.write_many(unsigned32_octets(len(data)))
        if kind == "seq":
            children = ((typ["item"], child, path + (i,)) for i, child in enumerate(data))
        elif kind == "map":
            def pairs():
                for i, pair in enumerate(data):
                    yield typ["key"], pair["key"], path + (i, "key")
                    yield typ["value"], pair["value"], path + (i, "value")
            children = pairs()
        elif kind == "record":
            children = ((child, data[name], path + (name,)) for name, child in self.registry.fields(typ))
        elif kind == "sum":
            variants = self.registry.variants(typ)
            ordinal = [name for name, _ in variants].index(data["tag"])
            yield from self.write_many(unsigned32_octets(ordinal))
            children = [(variants[ordinal][1], data["value"], path + (data["tag"],))]
        else:
            raise ValueError("nonpersistable oracle encode")
        for child, payload, child_path in children:
            yield from unit("ENCODE_NEXT", child_path)
            yield from self.encode_node(child, payload, child_path)

    def read(self, hook=None):
        offset = self.cursor
        def get():
            if self.cursor == len(self.input_wire):
                raise Fault("UnexpectedEnd", self.cursor)
            byte = self.input_wire[self.cursor]
            if hook is not None:
                hook(byte, self.cursor)
            self.cursor += 1
            return byte
        return (yield from unit("DECODE_READ", ("wire", offset), get))

    def read_number(self, count):
        values = []
        for _ in range(count):
            values.append((yield from self.read()))
        return values

    def decode_node(self, typ, path):
        kind = self.registry.kind(typ)
        start = self.cursor
        yield from unit("DECODE_NODE", path)
        if kind == "Unit":
            return None
        if kind in ("Bool", "Int64"):
            raw = yield from self.read_number(1 if kind == "Bool" else 8)
            def scalar():
                if kind == "Bool":
                    if raw[0] not in (0, 1):
                        raise Fault("InvalidEncoding", start)
                    return bool(raw[0])
                return int64_octets_value(raw)
            return (yield from unit("DECODE_SCALAR", path, scalar))
        if kind in ("String", "Bytes", "seq", "map"):
            raw_length = yield from self.read_number(4)
            def length():
                count = unsigned_octets_value(raw_length)
                limit = 4096 if kind == "String" else 32768 if kind == "Bytes" else 256
                if count > limit:
                    raise Physical("VALUE_LIMIT")
                return count
            count = yield from unit("DECODE_LENGTH", path, length)
        if kind == "String":
            cursor = UTF8Cursor()
            for _ in range(count):
                yield from self.read(cursor.accept)
            return (yield from unit("DECODE_SCALAR", path, cursor.finish))
        if kind == "Bytes":
            result = []
            for _ in range(count):
                result.append((yield from self.read()))
            return (yield from unit("DECODE_SCALAR", path, lambda: result))
        if kind == "seq":
            output = []
            for i in range(count):
                child_path = path + (i,)
                yield from unit("DECODE_NEXT", child_path)
                output.append((yield from self.decode_node(typ["item"], child_path)))
        elif kind == "map":
            output = []
            for i in range(count):
                key_start = self.cursor
                pair = {}
                for name, child in (("key", typ["key"]), ("value", typ["value"])):
                    child_path = path + (i, name)
                    yield from unit("DECODE_NEXT", child_path)
                    pair[name] = yield from self.decode_node(child, child_path)
                if i:
                    order_path = path + (i, "order")
                    order = yield from self.compare(typ["key"], output[-1]["key"], pair["key"], order_path)
                    def check_order():
                        if order >= 0:
                            raise Fault("NonCanonicalMap", key_start)
                    yield from unit("DECODE_MAP_ORDER", order_path, check_order)
                output.append(pair)
        elif kind == "record":
            output = {}
            for name, child in self.registry.fields(typ):
                child_path = path + (name,)
                yield from unit("DECODE_NEXT", child_path)
                output[name] = yield from self.decode_node(child, child_path)
        elif kind == "sum":
            raw = yield from self.read_number(4)
            variants = self.registry.variants(typ)
            def choose():
                ordinal = unsigned_octets_value(raw)
                if ordinal >= len(variants):
                    raise Fault("UnknownVariant", start)
                return variants[ordinal]
            tag, child = yield from unit("DECODE_TAG", path, choose)
            child_path = path + (tag,)
            yield from unit("DECODE_NEXT", child_path)
            output = {"tag": tag, "value": (yield from self.decode_node(child, child_path))}
        else:
            raise ValueError("unsupported oracle decode")
        def assemble():
            if typ == "DataError" and output["code"] not in ERROR_CODES:
                raise Fault("InvalidEncoding", start)
            return output
        return (yield from unit("DECODE_ASSEMBLE", path, assemble))

    def map_build(self, op):
        staged = []
        for j, entry in enumerate(op["entries"]):
            yield from unit("MAP_STAGE", ("entries", j), lambda entry=entry, j=j: staged.append((entry, j)))
        ordered = []
        for j, (entry, source_index) in enumerate(staged):
            position = len(ordered)
            for i, (old, original) in enumerate(ordered):
                path = ("entries", j, "probe", i)
                yield from unit("MAP_PROBE", path)
                order = yield from self.compare(op["key_type"], entry["key"]["data"], old["key"]["data"], path)
                def decide():
                    if order == 0:
                        raise Fault("DuplicateKey", original, source_index)
                    return order
                answer = yield from unit("MAP_DECIDE", path, decide)
                if answer < 0:
                    position = i
                    break
            fresh = []
            for i in range(len(ordered) + 1):
                if i == position:
                    yield from unit("MAP_ADD", ("entries", j), lambda: fresh.append((entry, source_index)))
                if i < len(ordered):
                    yield from unit("MAP_COPY", ("entries", j, "copy", i), lambda i=i: fresh.append(ordered[i]))
            ordered = yield from unit("MAP_COMMIT", ("entries", j), lambda: fresh)
        return {"tag": "Ok", "value": [{"key": e["key"]["data"], "value": e["value"]["data"]} for e, _ in ordered]}

    def operation_type(self):
        op = self.operation
        name = op["op"]
        if name in ("record", "variant"):
            return op["type"]
        if name == "sequence":
            return {"tag": "seq", "item": op["item_type"]}
        if name == "map_build":
            return result_type({"tag": "map", "key": op["key_type"], "value": op["value_type"]})
        if name == "field":
            return dict(self.registry.fields(op["record"]["type"]))[op["field"]]
        if name == "equal":
            return "Bool"
        if name in ("compare", "length"):
            return "Int64"
        if name == "seq_get":
            return option_type(op["sequence"]["type"]["item"])
        if name == "seq_append":
            return op["sequence"]["type"]
        if name == "map_get":
            return option_type(op["map"]["type"]["value"])
        if name in ("utf8_encode", "encode"):
            return "Bytes"
        if name == "utf8_decode":
            return result_type("String")
        if name == "decode":
            return result_type(op["type"])
        raise ValueError("unknown oracle operation")

    def work(self):
        self.output_type = self.operation_type()
        yield from unit("JOB_START")
        op = self.operation
        name = op["op"]
        if name == "record":
            staged = {}
            for i, field in enumerate(op["fields"]):
                yield from unit("RECORD_FIELD", ("fields", i),
                                lambda field=field: staged.update({field["id"]: field["value"]["data"]}))
            output = {field: staged[field] for field, _ in self.registry.fields(op["type"])}
        elif name == "variant":
            output = yield from unit("VARIANT_WRAP", ("value",),
                                     lambda: {"tag": op["tag"], "value": op["value"]["data"]})
        elif name == "sequence":
            output = []
            for i, item in enumerate(op["items"]):
                yield from unit("SEQUENCE_ITEM", ("items", i), lambda item=item: output.append(item["data"]))
        elif name == "field":
            output = yield from unit("FIELD_SELECT", ("record", op["field"]),
                                     lambda: op["record"]["data"][op["field"]])
        elif name in ("equal", "compare"):
            ordering = yield from self.compare(op["left"]["type"], op["left"]["data"], op["right"]["data"], ("compare",))
            output = ordering == 0 if name == "equal" else ordering
        elif name == "length":
            output = 0
            for i in range(len(op["value"]["data"])):
                output += yield from unit("LENGTH_ITEM", ("value", i), lambda: 1)
        elif name == "seq_get":
            sequence, index = op["sequence"]["data"], op["index"]["data"]
            output = yield from unit("SEQ_GET", ("sequence",), lambda: (
                {"tag": "Some", "value": sequence[index]} if 0 <= index < len(sequence)
                else {"tag": "None", "value": None}))
        elif name == "seq_append":
            output = []
            for i, item in enumerate(op["sequence"]["data"]):
                yield from unit("SEQUENCE_ITEM", ("sequence", i), lambda item=item: output.append(item))
            def append():
                if len(output) == 256:
                    raise Physical("VALUE_LIMIT")
                output.append(op["value"]["data"])
            yield from unit("SEQUENCE_APPEND", ("value",), append)
        elif name == "map_build":
            output = yield from self.map_build(op)
        elif name == "map_get":
            output = None
            for i, pair in enumerate(op["map"]["data"]):
                path = ("map", i)
                yield from unit("MAP_LOOKUP", path)
                ordering = yield from self.compare(op["key"]["type"], op["key"]["data"], pair["key"], path)
                ordering = yield from unit("MAP_LOOKUP_DECIDE", path, lambda: ordering)
                if ordering <= 0:
                    output = {"tag": "Some", "value": pair["value"]} if ordering == 0 else {"tag": "None", "value": None}
                    break
            if output is None:
                yield from unit("MAP_LOOKUP_END", ("map",))
                output = {"tag": "None", "value": None}
        elif name == "utf8_encode":
            for i, character in enumerate(op["value"]["data"]):
                octets = yield from unit("UTF8_SCALAR", ("value", i), lambda character=character: scalar_octets(character))
                for byte in octets:
                    yield from self.write(byte, "UTF8_WRITE", "bytes")
            output = self.wire
        elif name == "utf8_decode":
            cursor = UTF8Cursor()
            for i, byte in enumerate(op["value"]["data"]):
                yield from unit("UTF8_READ", ("bytes", i), lambda i=i, byte=byte: cursor.accept(byte, i))
            text = yield from unit("UTF8_END", ("bytes",), cursor.finish)
            output = {"tag": "Ok", "value": text}
        elif name == "encode":
            yield from self.write_many(self.registry.header(op["value"]["type"]))
            yield from self.encode_node(op["value"]["type"], op["value"]["data"], ("value",))
            output = self.wire
        elif name == "decode":
            self.input_wire = op["bytes"]["data"]
            for expected in self.registry.header(op["type"]):
                def check(byte, offset, expected=expected):
                    if byte != expected:
                        raise Fault("ContextMismatch", offset)
                yield from self.read(check)
            decoded = yield from self.decode_node(op["type"], ("value",))
            def end():
                if self.cursor < len(self.input_wire):
                    raise Fault("TrailingBytes", self.cursor)
            yield from unit("DECODE_END", ("wire", self.cursor), end)
            output = {"tag": "Ok", "value": decoded}
        else:
            raise ValueError("unsupported oracle job")
        return (yield from unit("JOB_FINISH", (), lambda: value(self.output_type, output)))


def run(job, budget, *, cancel_at=None, cancel_request_id="cancel"):
    """Consume actions only after guards; every action is real bounded data work.

    The verifier supplies accepted fixtures.  This reference does not duplicate
    prelaunch typechecking or every physical allocation guard of the engine.
    It compares the full declared observation within the stated finite corpus.
    """
    evaluator = Evaluator(job)
    generator = evaluator.work()
    pending = next(generator)
    trace = []
    remaining = budget
    returned = None
    while True:
        if cancel_at is not None and len(trace) >= cancel_at:
            termination, code = "SEMANTIC_STOP", "CANCELLED"
            break
        if remaining == 0:
            termination, code = "SEMANTIC_STOP", "BUDGET_EXCEEDED"
            break
        fault = None
        try:
            answer = pending.action()
        except Physical as error:
            termination, code = "IMPLEMENTATION_STOP", error.code
            break
        except Fault as error:
            fault = error
        remaining -= 1
        trace.append({"step_index": len(trace) + 1, "rule": pending.rule, "path": list(pending.path)})
        if fault is not None:
            returned = value(evaluator.output_type, {"tag": "Err", "value": fault.data})
            termination = code = "RETURNED"
            break
        try:
            pending = generator.send(answer)
        except StopIteration as final:
            returned = final.value
            termination = code = "RETURNED"
            break
    return {
        "profile_revision": PROFILE_REVISION, "codec_revision": CODEC_REVISION,
        "content_digest": canonical_digest({"profile_revision": PROFILE_REVISION,
                                             "codec_revision": CODEC_REVISION, "job": job}),
        "registry_digest": evaluator.registry.stamp,
        "termination": termination, "code": code, "value": returned,
        "steps": len(trace), "remaining": remaining, "trace": trace,
        "cancel_request_id": cancel_request_id if code == "CANCELLED" else None,
    }
