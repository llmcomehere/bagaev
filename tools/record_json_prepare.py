#!/usr/bin/env python3
"""Lossless data-only preparation for explicitly selected Json-only entries."""
import hashlib
import json
import sys
import record_text as transport


def arguments(raw, arity):
    depth = 0
    quoted = False
    escaped = False
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
            if depth > 128:
                raise transport.Refusal("RECORD_BOUNDS")
        elif byte in (93, 125):
            depth -= 1

    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate key")
            value[key] = item
        return value

    def constant(_):
        raise ValueError("non-JSON number")

    try:
        # Numbers are opaque validation markers, never binary floats or Int64.
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_int=lambda _: None, parse_float=lambda _: None,
                           parse_constant=constant)
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, str) and any(0xD800 <= ord(c) <= 0xDFFF for c in item):
                raise ValueError("unpaired surrogate")
            if isinstance(item, list):
                pending.extend(item)
            elif isinstance(item, dict):
                pending.extend(item.keys())
                pending.extend(item.values())
    except (ValueError, UnicodeError, RecursionError) as error:
        raise transport.Refusal("JSON_ARGUMENTS_FORMAT") from error
    if type(value) is not list or len(value) != arity:
        raise transport.Refusal("JSON_ARGUMENTS_ARITY")


def prepare(argv):
    p = transport.Parser(add_help=False, allow_abbrev=False)
    p.add_argument("source")
    p.add_argument("--form", choices=("4", "5", "6"), required=True)
    p.add_argument("--arguments", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args(argv)
    if a.form == "4":
        import bagaev_record_json_form as codec
    elif a.form == "5":
        import bagaev_record_wide_form as codec
    else:
        import bagaev_record_json_bool_form as codec
    source = transport.read_input(a.source)
    program = codec.decode(source)
    entry = program["functions"].get(program["entry"])
    if entry is None or any(param[1] != "Json" for param in entry["params"]):
        raise transport.Refusal("JSON_ENTRY")
    raw = transport.read_input(a.arguments)
    arguments(raw, len(entry["params"]))
    canonical = json.dumps(program, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    profile = {"4": b"10", "5": b"11", "6": b"12"}[a.form]
    invocation = (b'{"schema":"bagaev-typed-record-invocation/' + profile
                  + b'","program":' + canonical + b',"arguments":' + raw + b"}")
    if len(invocation) > transport.LIMIT:
        raise transport.Refusal("RECORD_BOUNDS")
    transport.write_output(a.output, invocation)
    return {"schema": "bagaev-json-preparation/1", "ok": True,
            "program_sha256": hashlib.sha256(canonical).hexdigest(),
            "arguments_sha256": hashlib.sha256(raw).hexdigest(),
            "invocation_sha256": hashlib.sha256(invocation).hexdigest(),
            "argument_bytes_preserved": True, "semantic_check": False,
            "execution_admission": False}


def main(argv=None):
    try:
        result = prepare(sys.argv[1:] if argv is None else argv)
        code = 0
    except (transport.Refusal, transport.form.FormError) as error:
        result = {"schema": "bagaev-json-preparation/1", "ok": False,
                  "error": {"code": error.code}}
        code = 2
    except (OSError, ValueError, UnicodeError) as error:
        result = {"schema": "bagaev-json-preparation/1", "ok": False,
                  "error": {"code": "JSON_PREPARATION"}}
        code = 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
