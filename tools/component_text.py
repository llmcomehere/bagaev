#!/usr/bin/env python3
"""Bounded data-only component/2 conversion. No semantic check or execution."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import bagaev_component_outcome_form as form
LIMIT = 1048576
SCHEMA = "bagaev-component-text/1"

class Refusal(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refusal("TOOL_USAGE")

def path_value(value):
    if not value or "\x00" in value:
        raise Refusal("COMPONENT_PATH")
    return Path(value)

def read_input(value):
    path = path_value(value)
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise Refusal("COMPONENT_PATH")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise Refusal("COMPONENT_PATH")
            if metadata.st_size > LIMIT:
                raise Refusal("COMPONENT_BOUNDS")
            raw = stream.read(LIMIT + 1)
    except OSError as error:
        raise Refusal("COMPONENT_IO") from error
    if len(raw) > LIMIT:
        raise Refusal("COMPONENT_BOUNDS")
    return raw

def parse_json(raw):
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
                raise Refusal("COMPONENT_BOUNDS")
        elif byte in (93, 125):
            depth -= 1
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    def integer(text):
        if len(text) > 20:
            raise ValueError("integer bound")
        value = int(text)
        if not -(1 << 63) <= value < (1 << 63):
            raise ValueError("integer bound")
        return value
    def unsupported(text):
        raise ValueError("unsupported number")
    try:
        text = raw.decode("utf-8")
        return json.loads(text, object_pairs_hook=pairs, parse_int=integer,
                          parse_float=unsupported, parse_constant=unsupported)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise Refusal("COMPONENT_JSON") from error

def write_output(value, raw):
    path = path_value(value)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
    except FileExistsError as error:
        raise Refusal("COMPONENT_PATH") from error
    except OSError as error:
        raise Refusal("COMPONENT_IO") from error

def convert(argv):
    parser = Parser(add_help=False, allow_abbrev=False)
    parser.add_argument("operation", choices=("decode", "encode"))
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--form", choices=("2", "3", "4", "5", "6"), default="2")
    args = parser.parse_args(argv)
    raw = read_input(args.input)
    codec = form
    if args.form == "3":
        import bagaev_component_arithmetic_form as codec
    elif args.form == "4":
        import bagaev_component_match_form as codec
    elif args.form == "5":
        import bagaev_component_text_list_form as codec
    elif args.form == "6":
        import bagaev_component_fold_form as codec
    if args.operation == "decode":
        value = codec.decode(raw)
        output = json.dumps(value, sort_keys=True, ensure_ascii=False,
                            separators=(",", ":"), allow_nan=False).encode("utf-8")
    else:
        output = codec.encode(parse_json(raw))
    if len(output) > LIMIT:
        raise Refusal("COMPONENT_BOUNDS")
    write_output(args.output, output)
    return {"operation": args.operation, "source_schema": "bagaev-component-source/2",
            "output_bytes": len(output), "output_sha256": hashlib.sha256(output).hexdigest(),
            "semantic_check": False, "execution_admission": False}

def main(argv=None):
    try:
        result = convert(sys.argv[1:] if argv is None else argv)
        observation = {"schema": SCHEMA, "ok": True, "result": result}
        code = 0
    except (Refusal, form.FormError) as error:
        observation = {"schema": SCHEMA, "ok": False, "error": {"code": error.code}}
        code = 2
    print(json.dumps(observation, sort_keys=True, separators=(",", ":")))
    return code

if __name__ == "__main__":
    raise SystemExit(main())
