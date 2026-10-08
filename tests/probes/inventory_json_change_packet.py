"""Data-only Changed Json inventory requests, native harness source and result checks."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import native_wide_qualification as q
from native_wide_wire import decode

D = q.ROOT / "examples/probes/inventory-json-change"


def packet(case_id):
    cases = json.loads(q.read(D / "cases.json", 1048576))
    case = next(c for c in cases if c["id"] == case_id)
    program = json.loads(q.read(D / "program.json", 1048576))
    env = json.loads(q.read(D / "native.binding.json", 2097152))
    binding = env["binding"]
    source = binding["source"].encode()
    pin = hashlib.sha256(source).digest()
    description = json.dumps(binding, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    if (binding["source_pin"] != "sha256:" + pin.hex()
            or env["binding_pin"] != "sha256:" + hashlib.sha256(description).hexdigest()
            or not q.same(program, json.loads(source))):
        raise ValueError("source/binding mismatch")
    row = next(x for x in json.loads(q.read(D / "native-observations.json", 1048576))["observations"]
               if x["case"] == case_id)
    invocation = {"schema": "bagaev-typed-record-invocation/11", "program": program,
                  "arguments": [case["request"]]}
    return case, invocation, binding, source, pin, row


def check(case_id, raw):
    case, invocation, _, _, pin, row = packet(case_id)
    value, work = decode(invocation["program"], raw, pin)
    if (not q.same(value, case["value"]) or work != row["work"]
            or len(raw) != row["wire_bytes"]
            or hashlib.sha256(raw).hexdigest() != row["wire_sha256"]):
        raise ValueError("complete native response mismatch")


def main():
    if not __debug__:
        raise ValueError("structural assertions must remain enabled")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["request", "harness", "check-native"])
    p.add_argument("case")
    p.add_argument("--output", type=Path)
    p.add_argument("--backend")
    a = p.parse_args()
    _, invocation, binding, source, pin, _ = packet(a.case)
    if a.mode == "request":
        if a.output is not None or a.backend is not None:
            raise ValueError("request takes no options")
        print(json.dumps(invocation, ensure_ascii=False, separators=(",", ":")))
    elif a.mode == "harness":
        if a.output is not None or a.backend is None:
            raise ValueError("harness requires only --backend")
        print(q.harness(binding, source, pin, a.backend), end="")
    else:
        if a.output is None or a.backend is not None:
            raise ValueError("check requires only --output")
        check(a.case, q.read(a.output, 4325440))
        print(json.dumps({"case": a.case, "complete_native_response": True, "measurement": False}))


if __name__ == "__main__":
    main()
