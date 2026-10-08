"""Data-only selected /11 requests, harness rendering and captured-result checks.

Never compiles, launches a subprocess, loads a kernel or grants execution authority.
Run without Python optimization: the structural wire extractor uses assertions.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from native_wide_wire import decode

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "examples/probes/native-wide-qualification"


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def read(path, limit):
    if path.is_symlink() or not path.is_file():
        raise ValueError("regular file required")
    with path.open("rb") as f:
        raw = f.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("file exceeds bound")
    return raw


def packet(program, case):
    envelope = json.loads(read(DATA / (program + ".binding.json"), 2097152))
    binding = envelope["binding"]
    description = json.dumps(binding, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    if envelope["binding_pin"] != "sha256:" + hashlib.sha256(description).hexdigest():
        raise ValueError("binding identity mismatch")
    source = binding["source"].encode()
    pin = hashlib.sha256(source).digest()
    if binding["source_pin"] != "sha256:" + pin.hex():
        raise ValueError("source identity mismatch")
    invocation = json.loads(read(DATA / (program + ".invocation.json"), 1048576))
    if not same(invocation["program"], json.loads(source)):
        raise ValueError("invocation source mismatch")
    if program == "sum":
        if case != "sum":
            raise ValueError("unknown sum case")
        expected = 120
    else:
        cases = json.loads(read(ROOT / "examples/probes/catalog-wide/cases.json", 1048576))
        found = next((x for x in cases if x["id"] == case), None)
        if found is None:
            raise ValueError("unknown catalog case")
        invocation["arguments"] = [found["request"]]
        expected = {"case": "Ok" if found["expected"]["kind"] == "success" else "Error",
                    "value": found["expected"]}
    observed = json.loads(read(DATA / "observations.json", 1048576))
    row = next(x for x in observed["observations"] if x["program"] == program and x["case"] == case)
    wire = bytes.fromhex(row["wire_hex"])
    value, work = decode(invocation["program"], wire, pin)
    if (len(wire) != row["wire_bytes"] or hashlib.sha256(wire).hexdigest() != row["wire_sha256"]
            or not same(value, expected) or work != row["work"]
            or not same(row["reference"]["value"], expected)
            or row["reference"]["status"] != "success"
            or row["reference"]["work"] != work):
        raise ValueError("captured observation disagrees with frozen value")
    return binding, source, pin, invocation, expected, row, wire


def harness(binding, source, pin, backend):
    # The returned Rust source remains unadmitted data. No file or process writes.
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", backend) or ".." in Path(backend).parts:
        raise ValueError("backend requires an absolute plain ASCII path without parent traversal")
    template = read(ROOT / "tests/probes/backend/native_wide_qualified_harness.rs.in", 65536).decode()
    description = json.dumps(binding, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    array = lambda raw: "[" + ",".join(map(str, raw)) + "]"
    program = json.loads(source)
    replacements = {
        "BACKEND": backend.rstrip("/"),
        "SOURCE": "const SOURCE:&[u8]=&" + array(source) + ";",
        "DESCRIPTION": "const DESCRIPTION:&[u8]=&" + array(description) + ";",
        "BINDING": "const BINDING:[u8;32]=" + array(pin) + ";",
        "ARG_COUNT": "const ARG_COUNT:usize=" + str(len(program["functions"][program["entry"]]["params"])) + ";",
    }
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", value)
    if "{{" in template:
        raise ValueError("unresolved template")
    return template


def main():
    if not __debug__:
        raise ValueError("structural assertions must remain enabled")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["request", "harness", "check-native", "check-reference"])
    p.add_argument("program", choices=["sum", "catalog"])
    p.add_argument("case")
    p.add_argument("--output", type=Path)
    p.add_argument("--backend")
    a = p.parse_args()
    binding, source, pin, invocation, expected, row, captured = packet(a.program, a.case)
    if a.mode == "harness":
        if a.backend is None or a.output is not None:
            raise ValueError("harness requires only --backend")
        print(harness(binding, source, pin, a.backend), end="")
    elif a.mode == "request":
        if a.backend is not None or a.output is not None:
            raise ValueError("request takes no options")
        print(json.dumps(invocation, ensure_ascii=True, separators=(",", ":")))
    else:
        if a.output is None or a.backend is not None:
            raise ValueError("check requires only --output")
        raw = read(a.output, 4325440)
        if a.mode == "check-native":
            value, work = decode(invocation["program"], raw, pin)
            if not same(value, expected) or work != row["work"] or raw != captured:
                raise ValueError("complete native value/work/wire mismatch")
        else:
            if not same(json.loads(raw), row["reference"]):
                raise ValueError("complete reference observation mismatch")
        print(json.dumps({"program": a.program, "case": a.case, "checked": a.mode,
                          "work": row["work"], "measurement": False}))


if __name__ == "__main__":
    main()
