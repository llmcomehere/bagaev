"""Pure model handoff and named changes. Parsing never executes candidate code.

The caller owns transport, authority, persistence, public/hidden separation,
checks and model calls. No provider, filesystem or scheduler is used here.
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import re
import tokenize

from . import bagaev_l2 as L2

PACKET = "bagaev-model-task/1"
RESPONSE = "bagaev-model-response/1"
ATTEMPT = "bagaev-model-attempt/1"
COST = "bagaev-model-cost/1"
LIMIT = 65_536
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")
_CATEGORIES = ("preparation", "attempts", "maintenance", "operation")


class ModelError(ValueError):
    """Stable code; diagnostics contain neither supplied text nor paths."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code="MODEL_FORMAT"):
    if not condition:
        raise ModelError(code)


def _fields(value, names):
    _need(type(value) is dict and set(value) == set(names.split()))


def _text(value, limit=1024, empty=False):
    _need(type(value) is str and (empty or bool(value)))
    _need(len(value) <= limit, "MODEL_BOUND")
    try:
        _need(len(value.encode("utf-8")) <= limit, "MODEL_BOUND")
    except UnicodeError:
        raise ModelError("MODEL_FORMAT") from None


def _id(value):
    _need(type(value) is str and _ID.fullmatch(value) is not None)


def _hash(value):
    _need(type(value) is str and _HASH.fullmatch(value) is not None)


def _integer(value, maximum=(1 << 63) - 1):
    _need(type(value) is int and 0 <= value <= maximum)


def _list(value, maximum=16):
    _need(type(value) is list)
    _need(len(value) <= maximum, "MODEL_BOUND")


def canonical(value):
    """Bounded exact JSON bytes (integers only), without mutating caller data."""
    pending = [(value, 1, frozenset())]
    count, size = 0, 0
    while pending:
        item, depth, parents = pending.pop()
        count += 1
        _need(depth <= 128 and count <= 32768, "MODEL_BOUND")
        kind = type(item)
        _need(kind in (dict, list, str, int, bool, type(None)))
        if kind in (dict, list):
            _need(id(item) not in parents)
            _need(len(item) <= 32768, "MODEL_BOUND")
            _need(count + len(pending) + len(item) <= 32768, "MODEL_BOUND")
            lineage = parents | {id(item)}
            size += 2 + max(0, len(item) - 1)
            if kind is dict:
                for key in item:
                    _text(key, LIMIT, empty=True)
                    size += len(json.dumps(key, ensure_ascii=False).encode("utf-8")) + 1
                    _need(size <= LIMIT, "MODEL_BOUND")
                values = item.values()
            else:
                values = item
            pending.extend((child, depth + 1, lineage) for child in values)
        elif kind is str:
            _text(item, LIMIT, empty=True)
            size += len(json.dumps(item, ensure_ascii=False).encode("utf-8"))
        elif kind is int:
            _need(-(1 << 63) <= item < (1 << 63), "MODEL_BOUND")
            size += len(str(item))
        else:
            size += 4 if item is None or item is True else 5
        _need(size <= LIMIT, "MODEL_BOUND")
    try:
        data = json.dumps(value, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (ValueError, RecursionError, UnicodeError):
        raise ModelError("MODEL_FORMAT") from None
    _need(len(data) <= LIMIT, "MODEL_BOUND")
    return data


def decode(data):
    """Read bounded UTF-8 JSON, refusing duplicates, BOM and noninteger numbers."""
    _need(type(data) is bytes)
    _need(len(data) <= LIMIT, "MODEL_BOUND")

    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result)
            result[key] = value
        return result

    def integer(token):
        _need(len(token.lstrip("-")) <= 19, "MODEL_BOUND")
        return int(token)

    def invalid(_):
        raise ModelError("MODEL_FORMAT")

    try:
        source = data.decode("utf-8")
        _need(not source.startswith("\ufeff"))
        value = json.loads(source, object_pairs_hook=pairs, parse_int=integer,
                           parse_float=invalid, parse_constant=invalid)
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, ModelError):
            raise
        raise ModelError("MODEL_FORMAT") from None
    canonical(value)
    return value


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def _clone(value):
    return decode(canonical(value))


def _python(source):
    _text(source, LIMIT)
    try:
        tree = ast.parse(source, filename="<candidate>", mode="exec")
    except (SyntaxError, ValueError, RecursionError):
        raise ModelError("MODEL_SOURCE") from None
    functions = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _need(node.name not in functions, "MODEL_SOURCE")
            functions[node.name] = node
    _need(len(functions) <= 64, "MODEL_BOUND")
    return tree, functions


def inspect_source(variant, source):
    """Return identity and named inventory; no evaluation/compile is performed."""
    _need(variant in ("python", "l2"))
    if variant == "l2":
        checked = L2.check_program(source)
        value = L2.program_value(checked)
        definitions = [{"id": name, "signature": value["definitions"][name]["params"],
                        "pin": value["pins"][name]} for name in sorted(value["definitions"])]
        return _clone({"source": checked.digest, "definitions": definitions})
    _, functions = _python(source)
    _need("evaluate" in functions and isinstance(functions["evaluate"], ast.FunctionDef),
          "MODEL_SOURCE")
    args = functions["evaluate"].args
    _need(len(args.posonlyargs) + len(args.args) == 1 and not args.kwonlyargs
          and args.vararg is None and args.kwarg is None, "MODEL_SOURCE")
    try:
        definitions = [{"id": name, "signature": ast.unparse(functions[name].args),
                        "pin": None} for name in sorted(functions)]
    except RecursionError:
        raise ModelError("MODEL_SOURCE") from None
    return _clone({"source": "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest(),
                   "definitions": definitions})


def _head(value):
    if value is None:
        return
    _fields(value, "generation source")
    _integer(value["generation"])
    if value["source"] is not None:
        _hash(value["source"])
    _need((value["generation"] == 0) == (value["source"] is None))


def _continuation(value):
    _fields(value, "next_question unresolved hypotheses checkpoints effects receipt")
    _text(value["next_question"])
    _list(value["unresolved"])
    for text in value["unresolved"]:
        _text(text)
    _list(value["hypotheses"])
    for item in value["hypotheses"]:
        _fields(item, "status text sources")
        _need(item["status"] in ("current", "historical"))
        _text(item["text"])
        _list(item["sources"])
        for source in item["sources"]:
            _hash(source)
    _list(value["checkpoints"])
    for item in value["checkpoints"]:
        _fields(item, "source step status")
        _hash(item["source"])
        _id(item["step"])
        _need(item["status"] in ("candidate", "public_passed", "public_failed", "unknown"))
    _list(value["effects"])
    seen = set()
    for item in value["effects"]:
        _fields(item, "id status")
        _id(item["id"])
        _need(item["id"] not in seen)
        seen.add(item["id"])
        _need(item["status"] in ("unknown", "succeeded", "failed"))
    receipt = value["receipt"]
    if receipt is not None:
        _fields(receipt, "operation status source")
        _id(receipt["operation"])
        _need(receipt["status"] in ("committed", "absent", "unknown"))
        if receipt["source"] is not None:
            _hash(receipt["source"])
        _need((receipt["status"] == "committed") == (receipt["source"] is not None))


def continuation_view(*, next_question, unresolved, hypotheses, checkpoints, effects, receipt):
    """Explicit public facts only; never accepts a Store export or auto-discloses it."""
    value = _clone({"next_question": next_question, "unresolved": unresolved,
                    "hypotheses": hypotheses, "checkpoints": checkpoints,
                    "effects": effects, "receipt": receipt})
    _continuation(value)
    return value


def _packet(value):
    _fields(value, "schema packet_id task revision run step attempt variant profile base goal "
                   "source references observations continuation limits")
    _need(value["schema"] == PACKET)
    _hash(value["packet_id"])
    for key in ("task", "run", "step"):
        _id(value[key])
    for key in ("revision", "attempt"):
        _integer(value[key])
        _need(value[key] > 0)
    _need(value["variant"] in ("python", "l2"))
    _fields(value["profile"], "model reasoning harness history")
    for key in ("model", "reasoning", "harness"):
        _text(value["profile"][key])
    _need(value["profile"]["history"] in ("fresh", "same_run", "successor"))
    _fields(value["base"], "source checkpoint head")
    _hash(value["base"]["source"])
    _integer(value["base"]["checkpoint"])
    _head(value["base"]["head"])
    _fields(value["goal"], "contract text")
    _hash(value["goal"]["contract"])
    _text(value["goal"]["text"], 16384)
    _need(inspect_source(value["variant"], value["source"])["source"] == value["base"]["source"],
          "MODEL_BINDING")
    _list(value["references"])
    seen = set()
    for item in value["references"]:
        _fields(item, "id text")
        _id(item["id"])
        _need(item["id"] not in seen)
        seen.add(item["id"])
        _text(item["text"], 16384)
    _list(value["observations"])
    for item in value["observations"]:
        _fields(item, "source checker status detail")
        _hash(item["source"])
        _text(item["checker"])
        _need(item["status"] in ("public_passed", "public_failed", "unknown"))
        _text(item["detail"], 4096)
    _continuation(value["continuation"])
    _fields(value["limits"], "packet_bytes response_bytes proposals_left wall_ms")
    _need(value["limits"]["packet_bytes"] == LIMIT
          and type(value["limits"]["packet_bytes"]) is int)
    _need(value["limits"]["response_bytes"] == LIMIT
          and type(value["limits"]["response_bytes"]) is int)
    _integer(value["limits"]["proposals_left"], 2)
    _need(value["limits"]["proposals_left"] > 0)
    _integer(value["limits"]["wall_ms"])
    unsigned = {k: v for k, v in value.items() if k != "packet_id"}
    _need(digest(unsigned) == value["packet_id"], "MODEL_BINDING")


def make_packet(fields):
    """Supply every packet field except packet_id; returns pinned canonical bytes."""
    value = _clone(fields)
    _need(type(value) is dict and "packet_id" not in value)
    value["packet_id"] = digest(value)
    _packet(value)
    return canonical(value)


def read_packet(data):
    value = decode(data)
    _packet(value)
    return value


def read_response(packet_bytes, response_bytes):
    packet = read_packet(packet_bytes)
    value = decode(response_bytes)
    _fields(value, "schema packet_id task revision run step attempt variant base status "
                   "add replace unresolved hypotheses")
    _need(value["schema"] == RESPONSE)
    for key in ("packet_id", "task", "revision", "run", "step", "attempt", "variant", "base"):
        _need(canonical(value[key]) == canonical(packet[key]), "MODEL_BINDING")
    _need(value["status"] in ("proposed", "cannot_complete"))
    for key in ("add", "replace"):
        _need(type(value[key]) is dict)
        _need(len(value[key]) <= 16, "MODEL_BOUND")
        for name in value[key]:
            _id(name)
    _need(len(value["add"]) + len(value["replace"]) <= 16, "MODEL_BOUND")
    _need(not value["add"].keys() & value["replace"].keys(), "MODEL_EDIT")
    _need(bool(value["add"] or value["replace"]) == (value["status"] == "proposed"))
    for key in ("unresolved", "hypotheses"):
        _list(value[key])
        for text in value[key]:
            _text(text)
    return value


def _python_change(source, add, replace):
    _, functions = _python(source)
    _need(not add.keys() & functions.keys() and replace.keys() <= functions.keys(), "MODEL_EDIT")
    replacements = {}
    for name, definition in {**add, **replace}.items():
        tree, nodes = _python(definition)
        _need(len(tree.body) == 1 and len(nodes) == 1 and name in nodes, "MODEL_EDIT")
        replacements[name] = definition + ("" if definition.endswith(("\n", "\r")) else "\n")
    # AST rows count physical Python lines, not Unicode separators in literals.
    # Keep the original terminators: normalization is only for token positions.
    lines = re.split(r"(?<=\n)|(?<=\r)(?!\n)", source)
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    decorator_starts = [token.start for token in
                        tokenize.generate_tokens(io.StringIO(normalized).readline)
                        if token.type == tokenize.OP and token.string == "@"]
    spans = []
    for name in replace:
        node = functions[name]
        start = node.lineno - 1
        if node.decorator_list:
            first = node.decorator_list[0]
            # A decorator expression can start after leading parentheses/newlines.
            # Its nearest preceding @ token owns those delimiters as well.
            preceding = [position for position in decorator_starts
                         if position < (first.lineno, first.col_offset)]
            _need(bool(preceding), "MODEL_SOURCE")
            start = max(preceding)[0] - 1
        spans.append((start, node.end_lineno, replacements[name]))
    for start, end, definition in sorted(spans, reverse=True):
        lines[start:end] = [definition]
    result = "".join(lines)
    if add:
        result += ("" if result.endswith("\n") else "\n") + "\n"
        result += "\n".join(replacements[k] for k in sorted(add))
    _text(result, LIMIT)
    inspect_source("python", result)
    return result


def propose(packet_bytes, response_bytes):
    """Construct detached candidate data, never check behavior or admit/run it."""
    packet = read_packet(packet_bytes)
    response = read_response(packet_bytes, response_bytes)
    _need(response["status"] == "proposed", "MODEL_EDIT")
    add, replace = response["add"], response["replace"]
    if packet["variant"] == "l2":
        patch = L2.prepare_patch(packet["source"], add, replace)
        checked = L2.apply_patch(packet["source"], patch)
        source, identity, change = L2.program_value(checked), checked.digest, patch
    else:
        source = _python_change(packet["source"], add, replace)
        identity = inspect_source("python", source)["source"]
        change = {"schema": "bagaev-python-change/1", "base": packet["base"]["source"],
                  "target": identity, "add": add, "replace": replace}
    return _clone({"source": source, "source_id": identity, "change": change,
                   "changed": sorted(set(add) | set(replace))})


def _attempt(value):
    _fields(value, "schema task revision run step attempt variant packet response outcome")
    _need(value["schema"] == ATTEMPT)
    for key in ("task", "run", "step"):
        _id(value[key])
    for key in ("revision", "attempt"):
        _integer(value[key])
        _need(value[key] > 0)
    _need(value["variant"] in ("python", "l2"))
    _hash(value["packet"])
    _need(value["outcome"] in ("received", "rejected", "timeout", "interrupted"))
    if value["response"] is not None:
        _fields(value["response"], "digest bytes")
        _hash(value["response"]["digest"])
        _integer(value["response"]["bytes"])
    _need(value["response"] is not None or value["outcome"] in ("timeout", "interrupted"))


def _attempt_key(value):
    return tuple(value[k] for k in ("task", "revision", "run", "step", "attempt", "variant"))


def append_attempt(records, packet_bytes, response, outcome):
    """Record an observed response receipt, including oversized/rejected output.

    response is null or {digest, bytes}, measured by the transport owner; this
    library does not claim those supplied observations are authenticated.
    Exact replay is idempotent; conflicting attempt identity refuses.
    """
    result = _clone(records)
    _list(result, 64)
    seen = set()
    for record in result:
        _attempt(record)
        key = _attempt_key(record)
        _need(key not in seen, "MODEL_REPLAY")
        seen.add(key)
    packet = read_packet(packet_bytes)
    value = {"schema": ATTEMPT, **{k: packet[k] for k in
             ("task", "revision", "run", "step", "attempt", "variant")},
             "packet": packet["packet_id"], "response": _clone(response), "outcome": outcome}
    _attempt(value)
    for record in result:
        if _attempt_key(record) == _attempt_key(value):
            _need(canonical(record) == canonical(value), "MODEL_REPLAY")
            return result
    _need(len(result) < 64, "MODEL_BOUND")
    result.append(value)
    return _clone(result)


def cost_totals(records):
    """Validate nonoverlapping expense observations and sum within each unit.

    Rows: schema,id,category,unit,amount,basis. amount is a nonnegative integer
    or null (unknown). basis identifies the measured expense, not a narrative.
    One basis/unit may be attributed once. Missing buckets remain unknown.
    Units are separate additive measures; peak memory is not an additive unit.
    """
    values = _clone(records)
    _list(values, 256)
    seen_ids, seen_basis, units = set(), set(), set()
    for row in values:
        _fields(row, "schema id category unit amount basis")
        _need(row["schema"] == COST)
        for key in ("id", "unit", "basis"):
            _id(row[key])
        _need(row["category"] in _CATEGORIES)
        _need(row["id"] not in seen_ids and (row["basis"], row["unit"]) not in seen_basis,
              "MODEL_COST")
        seen_ids.add(row["id"])
        seen_basis.add((row["basis"], row["unit"]))
        units.add(row["unit"])
        if row["amount"] is not None:
            _integer(row["amount"])
    result = {}
    for unit in sorted(units):
        buckets = {}
        for category in _CATEGORIES:
            amounts = [r["amount"] for r in values if r["unit"] == unit and r["category"] == category]
            buckets[category] = None if not amounts or None in amounts else sum(amounts)
            if buckets[category] is not None:
                _integer(buckets[category])
        dev = [buckets["preparation"], buckets["attempts"]]
        full = list(buckets.values())
        result[unit] = {**buckets, "C_dev": None if None in dev else sum(dev),
                        "C_full": None if None in full else sum(full)}
    return _clone(result)
