"""One explicit local L2 toolchain, including opt-in local store commands."""
from __future__ import annotations

import argparse
import errno
import json
import math
import os
import stat
import sys

from . import bagaev_l2 as L2
from . import bagaev_l2_backend as backend

SCHEMA = "bagaev-toolchain/1"
VERSION = "bagaev-toolchain/1 (L2; CPython backend/1; store/1)"
TEXT_LIMIT = 1048576
_FILE_ERRORS = {errno.ENOENT, errno.ENOTDIR, errno.EACCES, errno.EPERM,
                errno.ELOOP, errno.ENAMETOOLONG, errno.EISDIR, errno.ENXIO}
_MESSAGES = {
    "TOOL_USAGE": "Invalid command arguments",
    "TOOL_INPUT": "Input must be an accessible regular file",
    "TOOL_TRANSPORT": "Invalid or oversized JSON transport",
    "TOOL_OUTPUT": "Output must be a new writable regular file",
    "TOOL_ARTIFACT": "Artifact content does not match expected source and generator",
    "STORE_BOUND": "Store bound exceeded",
    "L2_JSON": "Invalid language JSON text",
    "L2_PROGRAM": "Invalid language program",
    "L2_REFERENCE": "Invalid language reference",
    "L2_CYCLE": "Cyclic language definitions",
    "L2_PIN": "Definition pin mismatch",
    "L2_BOUNDS": "Language bound exceeded",
    "L2_TYPE": "Invalid reached value type",
    "L2_FIELD": "Required field is absent",
    "L2_PATCH": "Invalid structural patch",
    "L2_STALE": "Patch base does not match source",
    "L2_TARGET": "Patch target does not match result",
}


class ToolError(ValueError):
    def __init__(self, code, location=None):
        self.code, self.location = code, location
        super().__init__(_MESSAGES[code])


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ToolError("TOOL_USAGE")


def _parser():
    parser = _Parser(prog="bagaev", description="Explicit local L2 toolchain")
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    for name in ("check", "run", "patch", "compile", "inspect", "diff"):
        command = commands.add_parser(name)
        if name == "diff":
            command.add_argument("before")
            command.add_argument("after")
        else:
            command.add_argument("program")
        if name == "run":
            command.add_argument("--input", required=True)
            command.add_argument("--artifact")
        elif name in ("patch", "compile"):
            if name == "patch":
                command.add_argument("patch")
            command.add_argument("--output", required=True)
    storage = commands.add_parser("store", help="Explicit durable L2 revisions")
    actions = storage.add_subparsers(dest="action", required=True, parser_class=_Parser)
    for name in ("init", "put", "check", "admit", "inspect", "export", "import", "restore"):
        command = actions.add_parser(name)
        command.add_argument("directory")
        if name in ("init", "import", "restore"):
            command.add_argument("--policy", required=True)
        if name in ("import", "restore"):
            command.add_argument("--package", required=True)
        if name == "restore":
            command.add_argument("--snapshot", required=True)
        if name == "put":
            command.add_argument("kind", choices=("source", "contract", "change", "evidence", "continuation"))
            command.add_argument("document")
        if name == "check":
            command.add_argument("source")
        if name == "admit":
            command.add_argument("operation")
            command.add_argument("continuation")
        if name == "inspect":
            selection = command.add_mutually_exclusive_group()
            selection.add_argument("--operation")
            selection.add_argument("--object")
        if name == "export":
            command.add_argument("--output", required=True)
    return parser


def _read(path, limit, overflow):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as error:
        if error.errno in _FILE_ERRORS:
            raise ToolError("TOOL_INPUT") from None
        raise
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ToolError("TOOL_INPUT")
        if info.st_size > limit:
            raise ToolError(overflow)
        chunks, total = [], 0
        while total <= limit:
            chunk = os.read(fd, min(65536, limit + 1 - total))
            if not chunk:
                return b"".join(chunks)
            total += len(chunk)
            chunks.append(chunk)
        raise ToolError(overflow)
    finally:
        os.close(fd)


def _write_new(path, data):
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW |
                     os.O_NONBLOCK | os.O_CLOEXEC, 0o600)
    except OSError as error:
        if error.errno in _FILE_ERRORS | {errno.EEXIST, errno.EROFS}:
            raise ToolError("TOOL_OUTPUT") from None
        raise
    identity = None
    closed = False
    try:
        identity = os.fstat(fd)
        if not stat.S_ISREG(identity.st_mode):
            raise ToolError("TOOL_OUTPUT")
        remaining = memoryview(data)
        while remaining:
            written = os.write(fd, remaining)
            if written == 0:
                raise OSError("Incomplete output write")
            remaining = remaining[written:]
        # close is part of success, but no fsync/durable-commit promise is made.
        closed = True
        os.close(fd)
    except BaseException:
        try:
            if not closed:
                closed = True
                os.close(fd)
        finally:
            if identity is not None:
                try:
                    current = os.lstat(path)
                except FileNotFoundError:
                    pass
                else:
                    if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                        os.unlink(path)
        raise


def _argument(data):
    """Bounded CLI transport only; never used by either value-level callable."""
    def invalid():
        raise ToolError("TOOL_TRANSPORT")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                invalid()
            result[key] = value
        return result

    def integer(token):
        digits = token.lstrip("-")
        if len(digits) > 4096:
            invalid()
        # Do not change global CPython decimal limits; convert bounded chunks.
        value = 0
        for offset in range(0, len(digits), 9):
            chunk = digits[offset:offset + 9]
            value = value * (10 ** len(chunk)) + int(chunk)
        return -value if token.startswith("-") else value

    try:
        text = data.decode("utf-8")
    except UnicodeError:
        invalid()
    # Preflight nesting before the stdlib parser's recursive descent. Bracket
    # correctness is still owned by the parser, not this surface depth scan.
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 128:
                invalid()
        elif char in "]}":
            depth -= 1
    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_int=integer,
                           parse_constant=lambda token: invalid())
    except (ValueError, RecursionError):
        invalid()
    count = 0
    pending = [(value, 1)]
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > 128 or count > 65536:
            invalid()
        if type(item) is float and not math.isfinite(item):
            invalid()
        if type(item) in (dict, list):
            pending.extend((child, depth + 1) for child in
                           (item.values() if type(item) is dict else item))
    return value


def _load(path):
    return L2.check_program(_read(path, TEXT_LIMIT, "L2_BOUNDS"))


def _dependencies(body):
    calls, pending = set(), [body]
    while pending:
        expression = pending.pop()
        if type(expression) is not list:
            continue
        op = expression[0]
        if op in ("literal", "var"):
            continue
        if op == "call":
            calls.add(expression[1])
            pending.extend(expression[2:])
        elif op == "let":
            pending.extend(pair[1] for pair in expression[1])
            pending.append(expression[2])
        elif op in ("object", "set"):
            pending.extend(expression[-1].values())
            if op == "set":
                pending.append(expression[1])
        elif op in ("map", "all", "any", "sort.by"):
            pending.extend((expression[1], expression[3]))
        elif op in ("get", "has", "shape", "int.range", "text", "array.bound"):
            pending.append(expression[1])
        else:
            pending.extend(expression[1:])
    return sorted(calls)


def _execute(args):
    if args.command == "store":
        return _store_execute(args)
    if args.command == "diff":
        before, after = _load(args.before), _load(args.after)
        a, b = L2.program_value(before), L2.program_value(after)
        left, right = a["definitions"], b["definitions"]
        common = left.keys() & right.keys()
        return {"before": before.digest, "after": after.digest,
                "entry_changed": a["entry"] != b["entry"],
                "added": sorted(right.keys() - left.keys()),
                "removed": sorted(left.keys() - right.keys()),
                "changed": sorted(k for k in common if backend.canonical(left[k]) != backend.canonical(right[k])),
                "pins_changed": sorted(k for k in common if a["pins"][k] != b["pins"][k])}
    program = _load(args.program)
    value = L2.program_value(program)
    if args.command == "check":
        return {"source": program.digest, "entry": value["entry"],
                "definitions": len(value["definitions"])}
    if args.command == "inspect":
        return {"source": program.digest, "entry": value["entry"],
                "definitions": [{"id": name, "pin": value["pins"][name],
                    "params": value["definitions"][name]["params"],
                    "dependencies": [{"id": dep, "pin": value["pins"][dep]}
                        for dep in _dependencies(value["definitions"][name]["body"])]}
                    for name in sorted(value["definitions"])]}
    if args.command == "patch":
        patched = L2.apply_patch(program, _read(args.patch, TEXT_LIMIT, "L2_BOUNDS"))
        if len(patched.canonical) > TEXT_LIMIT:
            raise ToolError("TOOL_TRANSPORT")
        _write_new(args.output, patched.canonical)
        return {"source": patched.digest, "base": program.digest, "bytes": len(patched.canonical)}
    if args.command == "compile":
        artifact = backend.compile_program(program)
        if len(artifact) > backend.ARTIFACT_LIMIT:
            raise ToolError("TOOL_TRANSPORT")
        metadata = json.loads(artifact)
        _write_new(args.output, artifact)
        return {key: metadata[key] for key in ("source", "generator", "artifact")} | {"bytes": len(artifact)}
    argument = _argument(_read(args.input, TEXT_LIMIT, "TOOL_TRANSPORT"))
    if args.artifact is None:
        result, engine = L2.evaluate(program, argument), "reference"
    else:
        captured = _read(args.artifact, backend.ARTIFACT_LIMIT, "TOOL_TRANSPORT")
        python = backend.verify_artifact(captured, program)
        namespace = {"__name__": "bagaev_compiled"}
        exec(compile(python, "<bagaev-l2>", "exec"), namespace)
        try:
            result = namespace["evaluate"](argument)
        except namespace["L2RuntimeError"] as error:
            raise ToolError(error.code, error.location) from None
        engine = "cpython"
    return {"source": program.digest, "engine": engine, "value": result}


def _store_execute(args):
    from . import bagaev_store as store

    def document(path):
        return store.decode(_read(path, store.LIMIT, "STORE_BOUND"))

    if args.action == "init":
        return {"snapshot": store.create(args.directory, document(args.policy))}
    if args.action in ("import", "restore"):
        data = _read(args.package, store.LIMIT, "STORE_BOUND")
        policy = document(args.policy)
        snapshot = (store.import_package(args.directory, data, policy) if args.action == "import"
                    else store.restore(args.directory, data, policy, args.snapshot))
        return {"snapshot": snapshot}
    with store.Store(args.directory) as current:
        if args.action == "put":
            return {"object": current.put(args.kind, document(args.document))}
        if args.action == "check":
            return {"source": args.source, "evidence": current.check(args.source)}
        if args.action == "admit":
            return current.admit(args.operation, args.continuation)
        if args.action == "inspect":
            return current.get(args.object) if args.object else current.inspect(args.operation)
        data = current.export()
        store.backup(args.output, data)
        return {"snapshot": store.decode(data)["snapshot"], "bytes": len(data)}


def main(argv=None):
    command = None
    store_errors = ()
    try:
        args = _parser().parse_args(argv)
        command = args.command
        if command == "store":
            # The original six commands do not require an installed SQLite module.
            from . import bagaev_store as store
            store_errors = (store.StoreError,)
        result = _execute(args)
        envelope = {"schema": SCHEMA, "command": command, "ok": True, "result": result}
        status = 0
    except (ToolError, L2.L2Error, backend.ArtifactError) + store_errors as error:
        envelope = {"schema": SCHEMA, "command": command, "ok": False,
                    "error": {"code": error.code, "message": _MESSAGES.get(error.code, str(error)),
                              "location": getattr(error, "location", None)}}
        status = 2
    except Exception:
        sys.stderr.write("Toolchain host failure\n")
        return 1
    try:
        sys.stdout.write(backend.canonical(envelope).decode("utf-8") + "\n")
    except Exception:
        sys.stderr.write("Toolchain host failure\n")
        return 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
