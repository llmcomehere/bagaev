"""Pure reference library for bagaev-l2/2. No CLI or external effects.

check_program returns a byte-backed immutable snapshot; evaluate returns a new
JSON tree. apply_patch returns a separate snapshot, never edits its arguments.
All callable input navigation is shallow. Evaluation uses explicit continuations.
"""
from __future__ import annotations

import hashlib
import json
import re

PROGRAM_SCHEMA = "bagaev-l2/2"
DRAFT_SCHEMA = "bagaev-l2-draft/2"
PATCH_SCHEMA = "bagaev-l2-patch/2"
INT_MIN, INT_MAX = -(1 << 63), (1 << 63) - 1
BYTE_LIMIT = 1048576
_ID = re.compile(r"[A-Za-z][A-Za-z0-9._-]{0,63}\Z", re.ASCII)
_HASH = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", re.ASCII)


class L2Error(ValueError):
    """The code, rather than message wording, is the stable observation."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _need(condition, code="L2_PROGRAM"):
    if not condition:
        raise L2Error(code)


def _unicode(value, code="L2_TYPE"):
    _need(not any(0xD800 <= ord(c) <= 0xDFFF for c in value), code)


def _string(value, code="L2_PROGRAM"):
    _need(type(value) is str, code)
    _unicode(value, code)
    _need(len(value.encode("utf-8")) <= 4096, "L2_BOUNDS")


def _identifier(value):
    _need(type(value) is str and _ID.fullmatch(value) is not None)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash(value):
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _parse(text, text_limit=True):
    """Iterative JSON grammar: malformed deep text never uses Python recursion."""
    _need(type(text) in (str, bytes), "L2_JSON")
    try:
        data = text.encode("utf-8") if type(text) is str else text
        _need(not text_limit or len(data) <= BYTE_LIMIT, "L2_BOUNDS")
        source = data.decode("utf-8")
    except UnicodeError:
        raise L2Error("L2_JSON") from None
    decoder = json.JSONDecoder()
    pos, frames, root, assigned = 0, [], None, False

    def scalar():
        nonlocal pos
        if pos >= len(source):
            raise L2Error("L2_JSON")
        if source[pos] == '"':
            try:
                value, pos = decoder.raw_decode(source, pos)
            except (ValueError, RecursionError):
                raise L2Error("L2_JSON") from None
            return value
        for spelling, value in (("true", True), ("false", False), ("null", None)):
            if source.startswith(spelling, pos):
                pos += len(spelling)
                return value
        match = _NUMBER.match(source, pos)
        _need(match is not None, "L2_JSON")
        token = match.group()
        pos = match.end()
        if any(c in token for c in ".eE"):
            return float(token)
        if len(token.lstrip("-")) > 20:
            # Every such integer is outside the language's literal range.
            # Preserve its tag and overflow direction without an unbounded
            # decimal conversion; its semantic position determines the error.
            # No checked program can retain this out-of-range representative.
            return INT_MIN - 1 if token.startswith("-") else INT_MAX + 1
        return int(token)

    def attach(value):
        nonlocal root, assigned
        if not frames:
            _need(not assigned, "L2_JSON")
            root, assigned = value, True
        elif frames[-1][0] == "array":
            frames[-1][1].append(value)
            frames[-1][2] = "comma"
        else:
            frame = frames[-1]
            frame[1][frame[3]] = value
            frame[2] = "comma"

    while True:
        while pos < len(source) and source[pos] in " \t\r\n":
            pos += 1
        if not frames and assigned:
            _need(pos == len(source), "L2_JSON")
            return root
        if frames:
            kind, container, state, key = frames[-1]
            end = "]" if kind == "array" else "}"
            _need(pos < len(source), "L2_JSON")
            if state in ("first", "comma") and source[pos] == end:
                frames.pop()
                pos += 1
                continue
            if state == "comma":
                _need(source[pos] == ",", "L2_JSON")
                frames[-1][2] = "next"
                pos += 1
                continue
            if kind == "object" and state in ("first", "next"):
                _need(source[pos] == '"', "L2_JSON")
                name = scalar()
                _need(name not in container, "L2_JSON")
                frames[-1][3], frames[-1][2] = name, "colon"
                continue
            if state == "colon":
                _need(source[pos] == ":", "L2_JSON")
                frames[-1][2] = "value"
                pos += 1
                continue
        _need(pos < len(source), "L2_JSON")
        if source[pos] in "[{":
            kind = "array" if source[pos] == "[" else "object"
            value = [] if kind == "array" else {}
            attach(value)
            frames.append([kind, value, "first", None])
            pos += 1
        else:
            attach(scalar())


def _json_tree(value):
    """Program-only JSON surface/depth scan, never used on callable arguments."""
    pending = [(value, 1, frozenset())]
    while pending:
        item, depth, parents = pending.pop()
        _need(depth <= 128, "L2_BOUNDS")
        kind = type(item)
        _need(kind in (dict, list, str, int, bool, float, type(None)))
        if kind in (dict, list):
            _need(id(item) not in parents)
            next_parents = parents | {id(item)}
            if kind is dict:
                _need(all(type(k) is str for k in item))
                values = [item[k] for k in sorted(item)]
            else:
                values = item
            pending.extend((v, depth + 1, next_parents) for v in reversed(values))


def _export(value, type_error="L2_TYPE"):
    """Bounded detached copy and exact canonical-size accounting, iteratively."""
    box = [None]
    pending = [(value, box, 0, 1, frozenset())]
    count, size = 0, 0
    while pending:
        item, parent, slot, depth, ancestors = pending.pop()
        count += 1
        _need(depth <= 64 and count <= 65536, "L2_BOUNDS")
        kind = type(item)
        _need(kind in (dict, list, str, int, bool, type(None)), type_error)
        if kind in (dict, list):
            _need(id(item) not in ancestors, type_error)
            _need(len(item) <= (32 if kind is dict else 256), "L2_BOUNDS")
            lineage = ancestors | {id(item)}
            size += 2 + max(0, len(item) - 1)
            if kind is dict:
                _need(all(type(k) is str for k in item), type_error)
                keys = sorted(item)
                for key in keys:
                    _string(key, type_error)
                    size += len(_canonical(key)) + 1
                result = {}
                pending.extend((item[k], result, k, depth + 1, lineage) for k in reversed(keys))
            else:
                result = [None] * len(item)
                pending.extend((item[i], result, i, depth + 1, lineage)
                               for i in range(len(item) - 1, -1, -1))
            parent[slot] = result
        else:
            if kind is str:
                _string(item, type_error)
            if kind is int:
                _need(INT_MIN <= item <= INT_MAX, "L2_BOUNDS")
            size += len(_canonical(item))
            parent[slot] = item
        _need(size <= BYTE_LIMIT, "L2_BOUNDS")
    return box[0]


def _fields(value, fields, code="L2_PROGRAM"):
    _need(type(value) is dict and set(value) == set(fields), code)


def _metadata_strings(values):
    _need(type(values) is list)
    for value in values:
        _string(value)
    _need(len(values) == len(set(values)))


def _syntax(program):
    """All syntax first, then references; an explicit stack preserves that order."""
    definitions = program["definitions"]
    _need(type(definitions) is dict)
    _need(1 <= len(definitions) <= 64, "L2_BOUNDS")
    _need(all(type(k) is str for k in definitions))
    references, graph, count = [], {}, 0
    arities = {"literal": 2, "var": 2, "let": 3, "if": 4, "not": 2,
               "object": 2, "set": 3, "get": 3, "has": 3, "null": 2,
               "shape": 4, "int.range": 4, "text": 6, "array.bound": 3,
               "eq": 3, "lt": 3, "length": 2, "map": 4, "all": 4,
               "any": 4, "filter": 4, "unique": 2, "sort": 2, "increasing": 2, "sort.by": 4}
    for name in sorted(definitions):
        _identifier(name)
        definition = definitions[name]
        _fields(definition, ("params", "body"))
        params = definition["params"]
        _need(type(params) is list)
        _need(len(params) <= 8, "L2_BOUNDS")
        for param in params:
            _identifier(param)
        _need(len(params) == len(set(params)))
        graph[name] = set()
        pending = [(definition["body"], frozenset(params), 1)]
        while pending:
            expr, scope, depth = pending.pop()
            count += 1
            _need(depth <= 64 and count <= 8192, "L2_BOUNDS")
            if type(expr) is not list:
                _need(type(expr) in (str, int, bool, type(None)))
                _export(expr, "L2_PROGRAM")
                continue
            _need(expr and type(expr[0]) is str)
            op = expr[0]
            _need(op in arities or op in ("call", "array", "and", "or"))
            if op in arities:
                _need(len(expr) == arities[op])
            elif op == "call":
                _need(len(expr) >= 2)
            else:
                _need((1 if op == "array" else 2) <= len(expr))
                _need(len(expr) <= (257 if op == "array" else 33), "L2_BOUNDS")
            children = []
            if op == "literal":
                _export(expr[1], "L2_PROGRAM")
            elif op == "var":
                _identifier(expr[1])
                references.append(expr[1] in scope)
            elif op == "call":
                _identifier(expr[1])
                graph[name].add(expr[1])
                references.append((expr[1], len(expr) - 2))
                children = [(e, scope) for e in expr[2:]]
            elif op == "let":
                bindings = expr[1]
                _need(type(bindings) is list)
                _need(1 <= len(bindings) <= 32, "L2_BOUNDS")
                local = scope
                for pair in bindings:
                    _need(type(pair) is list and len(pair) == 2)
                    _identifier(pair[0])
                    _need(pair[0] not in local)
                    children.append((pair[1], local))
                    local = local | {pair[0]}
                children.append((expr[2], local))
            elif op in ("map", "all", "any", "sort.by", "filter"):
                _identifier(expr[2])
                _need(expr[2] not in scope)
                children = [(expr[1], scope), (expr[3], scope | {expr[2]})]
            elif op in ("object", "set"):
                fields = expr[-1]
                _need(type(fields) is dict)
                _need(len(fields) <= 32, "L2_BOUNDS")
                _need(all(type(k) is str for k in fields))
                for key in sorted(fields):
                    _string(key)
                children = ([(expr[1], scope)] if op == "set" else [])
                children += [(fields[k], scope) for k in sorted(fields)]
            elif op in ("get", "has", "shape", "int.range", "text", "array.bound"):
                children = [(expr[1], scope)]
                if op in ("get", "has"):
                    _string(expr[2])
                elif op == "shape":
                    _need(type(expr[2]) is list and type(expr[3]) is list)
                    _need(len(expr[2]) + len(expr[3]) <= 32, "L2_BOUNDS")
                    _metadata_strings(expr[2]); _metadata_strings(expr[3])
                    _need(not set(expr[2]) & set(expr[3]))
                elif op == "int.range":
                    _need(all(type(x) is int for x in expr[2:]))
                    _need(all(INT_MIN <= x <= INT_MAX for x in expr[2:]), "L2_BOUNDS")
                    _need(expr[2] <= expr[3])
                elif op == "array.bound":
                    _need(type(expr[2]) is int and 0 <= expr[2] <= 256)
                else:
                    _need(type(expr[2]) is int and type(expr[3]) is int
                          and 0 <= expr[2] <= expr[3] <= 4096)
                    for intervals in expr[4:]:
                        _need(type(intervals) is list)
                        _need(1 <= len(intervals) <= 16, "L2_BOUNDS")
                        previous = -1
                        for pair in intervals:
                            _need(type(pair) is list and len(pair) == 2
                                  and all(type(x) is int for x in pair)
                                  and previous < pair[0] <= pair[1] <= 127)
                            previous = pair[1]
            else:
                children = [(e, scope) for e in expr[1:]]
            pending.extend((e, local, depth + 1) for e, local in reversed(children))
    _need(type(program["pins"]) is dict)
    _json_tree(program)
    _need(program["entry"] in definitions, "L2_REFERENCE")
    _need(len(definitions[program["entry"]]["params"]) == 1, "L2_REFERENCE")
    for reference in references:
        if type(reference) is bool:
            _need(reference, "L2_REFERENCE")
        else:
            target, arity = reference
            _need(target in definitions and len(definitions[target]["params"]) == arity,
                  "L2_REFERENCE")
    order, remaining = [], dict(graph)
    while remaining:
        ready = sorted(k for k, deps in remaining.items() if not deps.intersection(remaining))
        _need(ready, "L2_CYCLE")
        order.extend(ready)
        for name in ready:
            del remaining[name]
    pins = {}
    for name in order:
        pins[name] = _hash({"schema": "bagaev-l2-definition/2",
                            "definition": definitions[name],
                            "dependencies": {k: pins[k] for k in sorted(graph[name])}})
    return pins


class CheckedProgram(tuple):
    """Only immutable bytes cross the checked-snapshot boundary."""

    __slots__ = ()

    def __new__(cls, canonical):
        _need(type(canonical) is bytes)
        return tuple.__new__(cls, (canonical,))

    @property
    def canonical(self):
        return self[0]

    @property
    def digest(self):
        return "sha256:" + hashlib.sha256(self.canonical).hexdigest()


def _check(program, repin=False):
    if type(program) is CheckedProgram:
        program = _parse(program.canonical, text_limit=False)
    elif type(program) in (str, bytes):
        program = _parse(program)
    _fields(program, ("schema", "entry", "definitions", "pins"))
    _need(type(program["schema"]) is str and program["schema"] == PROGRAM_SCHEMA)
    _identifier(program["entry"])
    pins = _syntax(program)
    if not repin:
        _need(program["pins"] == pins and all(type(v) is str and _HASH.fullmatch(v)
              for v in program["pins"].values()), "L2_PIN")
    value = {**program, "pins": pins}
    data = _canonical(value)
    return CheckedProgram(data), value


def prepare_program(draft):
    """Explicit data-only authoring: validate an unpinned /2 draft and derive pins.

    This does not repair a checked program or grant execution authority.
    """
    if type(draft) in (str, bytes):
        draft = _parse(draft)
    _fields(draft, ("schema", "entry", "definitions"))
    _need(type(draft["schema"]) is str and draft["schema"] == DRAFT_SCHEMA)
    program = {"schema": PROGRAM_SCHEMA, "entry": draft["entry"],
               "definitions": draft["definitions"], "pins": {}}
    prepared = _check(program, repin=True)[0]
    # The prepared file must also fit the ordinary program text interface.
    return check_program(prepared.canonical)


def check_program(program):
    """Validate a program value/text or revalidate an immutable snapshot."""
    return _check(program)[0]


def program_value(program):
    """Return a detached ordinary JSON representation of a checked snapshot."""
    return _parse(check_program(program).canonical, text_limit=False)


def program_digest(program):
    return check_program(program).digest


def prepare_patch(original, add, replace):
    """Prepare a structural proposal with mechanical pins; no evaluation."""
    before, value = _check(original)
    for changes in (add, replace):
        _need(type(changes) is dict, "L2_PATCH")
        for name, definition in changes.items():
            _need(type(name) is str and _ID.fullmatch(name) is not None
                  and type(definition) is dict, "L2_PATCH")
    _need(add or replace, "L2_PATCH")
    _need(not add.keys() & replace.keys(), "L2_PATCH")
    _need(not add.keys() & value["definitions"].keys()
          and replace.keys() <= value["definitions"].keys(), "L2_PATCH")
    definitions = {**value["definitions"], **add, **replace}
    candidate, _value = _check({**value, "definitions": definitions}, repin=True)
    patch = {"schema": PATCH_SCHEMA, "base": before.digest,
             "target": candidate.digest, "add": add, "replace": replace}
    data = _canonical(patch)
    _need(len(data) <= BYTE_LIMIT, "L2_BOUNDS")
    return _parse(data)


def apply_patch(original, patch):
    before, value = _check(original)
    if type(patch) in (str, bytes):
        patch = _parse(patch)
    _fields(patch, ("schema", "base", "target", "add", "replace"), "L2_PATCH")
    _need(type(patch["schema"]) is str and patch["schema"] == PATCH_SCHEMA, "L2_PATCH")
    _need(all(type(patch[k]) is str and _HASH.fullmatch(patch[k])
              for k in ("base", "target")), "L2_PATCH")
    for key in ("add", "replace"):
        _need(type(patch[key]) is dict, "L2_PATCH")
        for name, definition in patch[key].items():
            _need(type(name) is str and _ID.fullmatch(name) is not None
                  and type(definition) is dict, "L2_PATCH")
    _need(patch["add"] or patch["replace"], "L2_PATCH")
    _need(not patch["add"].keys() & patch["replace"].keys(), "L2_PATCH")
    _need(before.digest == patch["base"], "L2_STALE")
    _need(not patch["add"].keys() & value["definitions"].keys()
          and patch["replace"].keys() <= value["definitions"].keys(), "L2_PATCH")
    definitions = {**value["definitions"], **patch["add"], **patch["replace"]}
    candidate, _value = _check({**value, "definitions": definitions}, repin=True)
    _need(candidate.digest == patch["target"], "L2_TARGET")
    return candidate


def _array(value):
    _need(type(value) is list, "L2_TYPE")
    _need(len(value) <= 256, "L2_BOUNDS")


def _strings(values):
    _need(all(type(v) is str for v in values), "L2_TYPE")
    for value in values:
        _unicode(value)
    for value in values:
        _need(len(value.encode("utf-8")) <= 4096, "L2_BOUNDS")


def _key(value, previous):
    _need(type(value) is list, "L2_TYPE")
    _need(1 <= len(value) <= 8 and (previous is None or len(value) == len(previous)),
          "L2_BOUNDS")
    _need(all(type(v) in (int, str) for v in value), "L2_TYPE")
    if previous is not None:
        _need(all(type(a) is type(b) for a, b in zip(value, previous)), "L2_TYPE")
    for v in value:
        if type(v) is str:
            _unicode(v)
    for v in value:
        _need((INT_MIN <= v <= INT_MAX) if type(v) is int
              else len(v.encode("utf-8")) <= 4096, "L2_BOUNDS")
    return tuple(value)


def evaluate(checked_program, argument):
    """Run an admitted program with shallow borrowed input and detached output."""
    _need(type(checked_program) is CheckedProgram)
    _checked, program = _check(checked_program)
    definitions = program["definitions"]
    main = definitions[program["entry"]]
    tasks = [("eval", main["body"], {main["params"][0]: argument}, 1)]
    values, steps = [], 0

    def charge(amount=1):
        nonlocal steps
        steps += amount
        _need(steps <= 100000, "L2_BOUNDS")

    def schedule(exprs, env, depth):
        tasks.extend(("eval", e, env, depth) for e in reversed(exprs))

    def take(n):
        if not n:
            return []
        result = values[-n:]
        del values[-n:]
        return result

    while tasks:
        task = tasks.pop()
        action = task[0]
        if action == "eval":
            _, expr, env, depth = task
            charge()
            if type(expr) is not list:
                values.append(expr)
                continue
            op = expr[0]
            if op == "var":
                values.append(env[expr[1]])
            elif op == "literal":
                values.append(expr[1])
            elif op == "if":
                tasks.append(("branch", expr, env, depth))
                schedule([expr[1]], env, depth)
            elif op in ("and", "or"):
                tasks.append(("boolean", expr, env, depth, 1))
                schedule([expr[1]], env, depth)
            elif op == "let":
                tasks.append(("bind", expr, dict(env), depth, 0))
                schedule([expr[1][0][1]], env, depth)
            elif op in ("map", "all", "any", "sort.by", "filter"):
                tasks.append(("start-loop", expr, env, depth))
                schedule([expr[1]], env, depth)
            else:
                if op == "call":
                    operands = expr[2:]
                elif op == "object":
                    operands = [expr[1][k] for k in sorted(expr[1])]
                elif op == "set":
                    operands = [expr[1]] + [expr[2][k] for k in sorted(expr[2])]
                elif op in ("get", "has", "shape", "text", "int.range", "array.bound"):
                    operands = [expr[1]]
                else:
                    operands = expr[1:]
                tasks.append(("apply", expr, env, depth, len(operands)))
                schedule(operands, env, depth)
        elif action == "branch":
            _, expr, env, depth = task
            condition = values.pop()
            _need(type(condition) is bool, "L2_TYPE")
            schedule([expr[2] if condition else expr[3]], env, depth)
        elif action == "boolean":
            _, expr, env, depth, index = task
            result = values.pop()
            _need(type(result) is bool, "L2_TYPE")
            if result is (expr[0] == "or") or index == len(expr) - 1:
                values.append(result)
            else:
                tasks.append(("boolean", expr, env, depth, index + 1))
                schedule([expr[index + 1]], env, depth)
        elif action == "bind":
            _, expr, env, depth, index = task
            env[expr[1][index][0]] = values.pop()
            if index + 1 == len(expr[1]):
                schedule([expr[2]], env, depth)
            else:
                tasks.append(("bind", expr, env, depth, index + 1))
                schedule([expr[1][index + 1][1]], env, depth)
        elif action == "start-loop":
            _, expr, env, depth = task
            array = values.pop()
            _array(array)
            if expr[0] == "sort.by":
                charge(len(array) ** 2)
            tasks.append(("loop", expr, env, depth, array, 0, []))
        elif action == "loop":
            _, expr, env, depth, array, index, accumulated = task
            op = expr[0]
            if index:
                result = values.pop()
                if op in ("all", "any"):
                    _need(type(result) is bool, "L2_TYPE")
                    if result is (op == "any"):
                        values.append(result)
                        continue
                elif op == "sort.by":
                    result = _key(result, accumulated[0] if accumulated else None)
                if op == "filter":
                    _need(type(result) is bool, "L2_TYPE")
                    if result:
                        accumulated.append(array[index - 1])
                else:
                    accumulated.append(result)
            if index == len(array):
                if op in ("all", "any"):
                    result = op == "all"
                elif op == "sort.by":
                    result = [array[i] for i in sorted(range(len(array)), key=accumulated.__getitem__)]
                else:
                    result = accumulated
                values.append(result)
            else:
                tasks.append(("loop", expr, env, depth, array, index + 1, accumulated))
                schedule([expr[3]], {**env, expr[2]: array[index]}, depth)
        else:
            _, expr, env, depth, number = task
            args, op = take(number), expr[0]
            if op == "call":
                _need(depth < 64, "L2_BOUNDS")
                definition = definitions[expr[1]]
                schedule([definition["body"]], dict(zip(definition["params"], args)), depth + 1)
                continue
            if op == "array":
                result = args
            elif op == "object":
                result = dict(zip(sorted(expr[1]), args))
            elif op == "set":
                _need(type(args[0]) is dict, "L2_TYPE")
                _need(len(args[0]) <= 32, "L2_BOUNDS")
                result = {**args[0], **dict(zip(sorted(expr[2]), args[1:]))}
                _need(len(result) <= 32, "L2_BOUNDS")
            elif op == "get":
                _need(type(args[0]) is dict, "L2_TYPE")
                _need(expr[2] in args[0], "L2_FIELD")
                result = args[0][expr[2]]
            elif op == "has":
                result = type(args[0]) is dict and expr[2] in args[0]
            elif op == "null":
                result = args[0] is None
            elif op == "shape":
                v, required, optional = args[0], expr[2], expr[3]
                result = (type(v) is dict and len(required) <= len(v) <= len(required) + len(optional)
                          and all(k in v for k in required) and all(k in required or k in optional for k in v))
            elif op == "int.range":
                result = type(args[0]) is int and expr[2] <= args[0] <= expr[3]
            elif op == "array.bound":
                result = type(args[0]) is list and len(args[0]) <= expr[2]
            elif op == "text":
                v = args[0]
                result = (type(v) is str and expr[2] <= len(v) <= expr[3]
                          and all(any(lo <= ord(c) <= hi for lo, hi in expr[4 if i == 0 else 5])
                                  for i, c in enumerate(v)))
            elif op == "eq":
                result = (type(args[0]) in (str, int, float, bool, type(None))
                          and type(args[0]) is type(args[1]) and args[0] == args[1])
            elif op == "lt":
                _need(type(args[0]) in (str, int) and type(args[0]) is type(args[1]), "L2_TYPE")
                if type(args[0]) is str:
                    _strings(args)
                else:
                    _need(all(INT_MIN <= v <= INT_MAX for v in args), "L2_BOUNDS")
                result = args[0] < args[1]
            elif op == "not":
                _need(type(args[0]) is bool, "L2_TYPE")
                result = not args[0]
            else:
                _array(args[0])
                if op == "length":
                    result = len(args[0])
                else:
                    _strings(args[0])
                    charge(len(args[0]) ** 2)
                    if op == "unique":
                        result = list(dict.fromkeys(args[0]))
                    elif op == "sort":
                        result = sorted(args[0])
                    else:
                        result = all(a < b for a, b in zip(args[0], args[0][1:]))
            values.append(result)
    _need(len(values) == 1)
    return _export(values[0])
