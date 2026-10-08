"""Data-only followthrough packet: owned state handoff and literal failure metadata.

Never launches compilers or kernels. Source, artifact and execution admission
remain external. Failure metadata is only meaningful with its exact source.
"""
import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path
import native_wide_qualification as q

DATA = q.ROOT / "examples/probes/native-wide-followthrough"


def cases():
    return json.loads(q.read(DATA / "continuation-cases.json", 1048576))


def checked_previous(case_id, raw):
    case = next(x for x in cases() if x["id"] == case_id)
    _, _, pin, inv, _, _, _ = q.packet("catalog", "sixteen-set")
    value, work = q.decode(inv["program"], raw, pin)
    row = json.loads(q.read(DATA / "continuation-observations.json", 1048576))["observations"][case_id]
    expected = {"case": "Ok" if case["expected"]["kind"] == "success" else "Error",
                "value": case["expected"]}
    if (not q.same(value, expected) or work != row["work"]
            or len(raw) != row["wire_bytes"]
            or hashlib.sha256(raw).hexdigest() != row["wire_sha256"]):
        raise ValueError("complete predecessor result mismatch")
    return value


def continuation_request(case_id, previous):
    case = next(x for x in cases() if x["id"] == case_id)
    _, _, _, invocation, _, _, _ = q.packet("catalog", "sixteen-set")
    request = copy.deepcopy(case["request"])
    predecessor = case["previous_success"]
    if predecessor is None:
        if previous is not None:
            raise ValueError("initial request has no predecessor")
    else:
        if previous is None:
            raise ValueError("owned predecessor result required")
        value = checked_previous(predecessor, previous)
        if value["case"] != "Ok" or not q.same(value["value"]["state"], request["state"]):
            raise ValueError("only the declared last successful state can continue")
        request["state"] = copy.deepcopy(value["value"]["state"])
    invocation["arguments"] = [request]
    return invocation


def failure_packet(case_id):
    row = next(x for x in json.loads(q.read(DATA / "failure-expectations.json", 65536))
               if x["id"] == case_id)
    invocation = json.loads(q.read(DATA / (case_id + ".invocation.json"), 1048576))
    env = json.loads(q.read(DATA / (case_id + ".binding.json"), 2097152))
    binding = env["binding"]
    source = binding["source"].encode()
    pin = hashlib.sha256(source).digest()
    description = json.dumps(binding, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    if (binding["source_pin"] != "sha256:" + pin.hex()
            or env["binding_pin"] != "sha256:" + hashlib.sha256(description).hexdigest()
            or not q.same(json.loads(source), invocation["program"])):
        raise ValueError("failure source/binding mismatch")
    m = row["native_metadata"]
    wire = struct.pack("<IIqQII", *(m[x] for x in
                       ("status", "value_type", "value", "work", "reason", "location")))
    return row, invocation, binding, source, pin, wire


def failure_harness(case_id, backend):
    _, _, binding, source, pin, wire = failure_packet(case_id)
    text = q.harness(binding, source, pin, backend)
    before = "assert_eq!((owned.meta.status,owned.meta.reason,owned.meta.location),(0,0,0));"
    after = "assert_eq!(owned.bytes.as_slice(),&" + str(list(wire)).replace(" ", "") + ");"
    if text.count(before) != 1 or text.count('assert_eq!(&bytes[..8],b"BCMPRES4");') != 1:
        raise ValueError("qualified template changed")
    return text.replace(before, after).replace('assert_eq!(&bytes[..8],b"BCMPRES4");',
                                                "assert_eq!(bytes.len(),32);")


def main():
    if not __debug__:
        raise ValueError("structural assertions must remain enabled")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["continuation-request", "continuation-check",
                                   "failure-request", "failure-check", "failure-harness"])
    p.add_argument("case")
    p.add_argument("--previous", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--backend")
    a = p.parse_args()
    if a.mode == "continuation-request":
        if a.output is not None or a.backend is not None:
            raise ValueError("request accepts only --previous")
        prior = None if a.previous is None else q.read(a.previous, 4325440)
        print(json.dumps(continuation_request(a.case, prior), separators=(",", ":")))
    elif a.mode == "failure-request":
        if any(x is not None for x in (a.previous, a.output, a.backend)):
            raise ValueError("failure request takes no options")
        print(json.dumps(failure_packet(a.case)[1], separators=(",", ":")))
    elif a.mode == "failure-harness":
        if a.backend is None or a.previous is not None or a.output is not None:
            raise ValueError("failure harness requires only --backend")
        print(failure_harness(a.case, a.backend), end="")
    else:
        if a.output is None or a.previous is not None or a.backend is not None:
            raise ValueError("check requires only --output")
        raw = q.read(a.output, 4325440)
        if a.mode == "continuation-check":
            checked_previous(a.case, raw)
        elif raw != failure_packet(a.case)[-1]:
            raise ValueError("complete scoped failure metadata mismatch")
        print(json.dumps({"case": a.case, "checked": a.mode, "measurement": False}))


if __name__ == "__main__":
    main()
