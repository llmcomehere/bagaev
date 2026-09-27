"""Standalone CLI integration; execute only under an authorized test profile.

The development interruption is a completed process boundary after persisted
A1 admission and unfinished work. SQLite pre/postcommit interruption belongs
to test_store.StoreTests.test_fresh_process_precommit_and_postcommit_recovery.
This scenario samples each new behavior before admission; its fixed receiver
policy covers earlier revision-0 behavior, not the complete application oracle.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY_CASES = ("REV-0", "LIST-0", "REPEAT-0", "CHAIN-0", "EMPTY-0",
                "REINDEX-COLLISION-0", "STORED-COLLISION-0")
PATCHES = ("catalog-01.patch", "catalog-12.patch", "catalog-23.patch")
RECEIPT_LIMIT = 2 * 1024 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write_new(path, value):
    data = canonical(value)
    if len(data) > RECEIPT_LIMIT:
        raise AssertionError("Integration document exceeds capture bound")
    with Path(path).open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def capture(argv, cwd, timeout, *, group=False):
    """Reap the exact owned child; a phase owns all its nested CLI processes."""
    process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=group,
        env={"PATH": os.defpath, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"})
    timed_out = False
    def stop():
        try:
            if group:
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass
    try:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            stop()
            stdout, stderr = process.communicate(timeout=5)
    finally:
        if process.poll() is None:
            stop()
            process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()
    return {"argv": list(map(str, argv)), "pid": process.pid,
            "returncode": process.returncode, "timed_out": timed_out,
            "stdout_base64": base64.b64encode(stdout).decode("ascii"),
            "stderr_base64": base64.b64encode(stderr).decode("ascii")}


def streams(record):
    return (base64.b64decode(record["stdout_base64"], validate=True),
            base64.b64decode(record["stderr_base64"], validate=True))


class _Flow:
    """Only the public CLI touches programs, artifacts and the receiver Store."""

    def __init__(self, root):
        self.root = root
        self.output = root / "output"
        self.records = []
        self.check = unittest.TestCase()
        self.oracle = read(root / "examples/beta/catalog-cases.json")
        self.check.assertEqual(len(self.oracle["cases"]), 99)
        self.check.assertEqual(self.oracle["oracle"], "catalog-cases/2.0.0")

    def equal(self, actual, expected):
        # Typed JSON comparison: True, 1 and 1.0 are distinct observations.
        self.check.assertEqual(canonical(actual), canonical(expected))

    def cli(self, *arguments, error=None):
        argv = [sys.executable, "-B", "-S", "-m", "src.bagaev",
                *map(str, arguments)]
        record = capture(argv, self.root, 20)
        self.records.append(record)
        stdout, stderr = streams(record)
        self.check.assertFalse(record["timed_out"])
        self.equal(record["returncode"], 0 if error is None else 2)
        self.equal(stderr.decode("utf-8"), "")
        self.check.assertTrue(stdout.endswith(b"\n"))
        self.equal(len(stdout.splitlines()), 1)
        value = json.loads(stdout)
        self.check.assertEqual(set(value), {"schema", "command", "ok",
                                           "result" if error is None else "error"})
        self.equal(value["schema"], "bagaev-toolchain/1")
        self.equal(value["command"], arguments[0])
        self.equal(value["ok"], error is None)
        if error is not None:
            self.equal(value["error"]["code"], error)
            return value["error"]
        return value["result"]

    def case(self, identity):
        case = next(c for c in self.oracle["cases"] if c["id"] == identity)
        return self.oracle["requests"][case["request"]], self.oracle["responses"][case["expect"]]

    def source(self, step):
        return "examples/l2/catalog.json" if step == 0 else f"output/catalog-a{step}.json"

    def source_id(self, step):
        if step == 0:
            return digest(read(self.root / self.source(0)))
        return read(self.root / "examples/l2" / PATCHES[step - 1])["target"]

    def put(self, kind, path):
        wanted = digest(read(self.root / path))
        self.equal(self.cli("store", "put", "output/store", kind, path), {"object": wanted})
        return wanted

    def policy(self):
        return read(self.output / "policy.json")

    def continuation(self, step, base, changes, evidence, unresolved=()):
        policy = self.policy()
        return {"schema": "bagaev-store-continuation/1", "task": "catalog-evolution",
            "intent": "Preserve the fixed revision-0 receiver obligations",
            "base": base, "target": self.source_id(step), "changes": changes,
            "contract": digest(policy["contract"]),
            "required": sorted(c["id"] for c in policy["contract"]["cases"]),
            "evidence": evidence, "unresolved": list(unresolved),
            "effects": [], "hypotheses": []}

    def behavior(self, step):
        program = self.source(step)
        value = read(self.root / program)
        self.equal(self.cli("check", program), {"source": self.source_id(step),
            "entry": value["entry"], "definitions": len(value["definitions"])})
        argument, expected = self.case(f"REV-{step}")
        input_path = f"output/input-{step}.json"
        write_new(self.root / input_path, argument)
        artifact = f"output/artifact-{step}.json"
        compiled = self.cli("compile", program, "--output", artifact)
        bundle = read(self.root / artifact)
        self.equal(compiled["source"], self.source_id(step))
        self.equal(compiled["artifact"], digest({k: v for k, v in bundle.items() if k != "artifact"}))
        for extra, engine in (((), "reference"), (("--artifact", artifact), "cpython")):
            self.equal(self.cli("run", program, "--input", input_path, *extra),
                {"source": self.source_id(step), "engine": engine, "value": expected})
        self.equal(read(self.root / input_path), argument)

    def advance(self, step):
        base = {"generation": step, "source": None if step == 0 else self.source_id(step - 1)}
        if step:
            patch = "examples/l2/" + PATCHES[step - 1]
            changed = self.cli("patch", self.source(step - 1), patch, "--output", self.source(step))
            self.equal(changed["source"], self.source_id(step))
            self.equal(changed["base"], base["source"])
        # New behavior is checked against frozen literal expectations BEFORE admission.
        self.behavior(step)
        self.put("source", self.source(step))
        changes = [] if step == 0 else [self.put("change", "examples/l2/" + PATCHES[step - 1])]
        policy = self.policy()
        checker = {"version": "bagaev-store-checker/1", "implementation": digest({
            name: hashlib.sha256((self.root / "src" / name).read_bytes()).hexdigest()
            for name in ("bagaev_store.py", "bagaev_l2.py")})}
        expected_evidence = [{"schema": "bagaev-store-evidence/1", "source": self.source_id(step),
            "contract": digest(policy["contract"]), "case": case["id"],
            "input": digest(case["input"]), "checker": checker,
            "assumptions": policy["contract"]["assumptions"],
            "result": {"status": "passed", "actual": case["expected"]}}
            for case in policy["contract"]["cases"]]
        evidence = [digest(e) for e in expected_evidence]
        self.equal(self.cli("store", "check", "output/store", self.source_id(step)),
                   {"source": self.source_id(step), "evidence": evidence})
        self.equal(self.cli("store", "inspect", "output/store")["head"], base)
        continuation = self.continuation(step, base, changes, evidence)
        path = f"output/continue-{step}.json"
        write_new(self.root / path, continuation)
        identity = self.put("continuation", path)
        receipt = {"operation": f"catalog-{step}", "request": digest({"continuation": identity}),
            "continuation": identity, "head": {"generation": step + 1, "source": self.source_id(step)}}
        self.equal(self.cli("store", "admit", "output/store", f"catalog-{step}", identity), receipt)
        write_new(self.output / f"receipt-{step}.json", receipt)
        return receipt

    def predecessor(self):
        self.output.mkdir()
        cases = []
        for identity in POLICY_CASES:
            argument, expected = self.case(identity)
            self.equal(argument["behavior_revision"], 0)
            cases.append({"id": identity, "input": argument, "expected": {"value": expected}})
        policy = {"schema": "bagaev-store-policy/1", "contract": {
            "schema": "bagaev-store-contract/1", "assumptions": ["Selected frozen revision-0 catalog cases"],
            "cases": cases}}
        write_new(self.output / "policy.json", policy)
        self.cli("store", "init", "output/store", "--policy", "output/policy.json")
        inspected = self.cli("inspect", self.source(0))
        self.equal(inspected["source"], self.source_id(0))
        original = read(self.root / self.source(0))
        self.equal({d["id"]: d["pin"] for d in inspected["definitions"]}, original["pins"])
        self.advance(0)
        receipt = self.advance(1)
        pending = self.continuation(1, receipt["head"], [], [],
            ["Apply catalog-12.patch, check revision 2, admit; then repeat with catalog-23.patch and revision 3."])
        write_new(self.output / "unfinished.json", pending)
        identity = self.put("continuation", "output/unfinished.json")
        before = self.cli("store", "inspect", "output/store")
        self.cli("store", "admit", "output/store", "unfinished", identity, error="STORE_CHECK")
        self.equal(self.cli("store", "inspect", "output/store"), before)
        write_new(self.output / "handoff.json", {"schema": "catalog-development-handoff/1",
            "pending": identity, "head": receipt["head"], "remaining": [2, 3],
            "policy": digest(policy), "snapshot": before["snapshot"],
            "receipt_operation": "catalog-1",
            "retained_files": {path: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                for path in (self.source(0), self.source(1),
                             *("examples/l2/" + name for name in PATCHES))}})
        # Return ends this interpreter. No live connection or in-memory state is transferred.
        return {"phase": "predecessor", "boundary": "persisted-admitted-A1-with-unfinished-work",
                "head": receipt["head"]}

    def successor(self):
        handoff = read(self.output / "handoff.json")
        self.equal(handoff["schema"], "catalog-development-handoff/1")
        self.equal(handoff["remaining"], [2, 3])
        self.equal(handoff["policy"], digest(self.policy()))
        retained = handoff["retained_files"]
        self.equal({path: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                    for path in retained}, retained)
        inspected = self.cli("store", "inspect", "output/store")
        self.equal(inspected["snapshot"], handoff["snapshot"])
        self.equal(inspected["head"], handoff["head"])
        pending = self.cli("store", "inspect", "output/store", "--object", handoff["pending"])
        self.equal(pending, {"kind": "continuation", "value": read(self.output / "unfinished.json")})
        self.check.assertTrue(pending["value"]["unresolved"])
        self.equal(pending["value"]["evidence"], [])
        old_receipt = read(self.output / "receipt-1.json")
        self.equal(self.cli("store", "inspect", "output/store", "--operation", handoff["receipt_operation"]),
            {"operation": "catalog-1", "status": "committed", "receipt": old_receipt, "head": handoff["head"]})
        for step in handoff["remaining"]:
            self.advance(step)
        final = self.cli("store", "inspect", "output/store")
        self.equal(final["head"], {"generation": 4, "source": self.source_id(3)})
        comparison = self.cli("diff", self.source(0), self.source(3))
        self.equal((comparison["before"], comparison["after"]), (self.source_id(0), self.source_id(3)))
        self.check.assertTrue(comparison["changed"] or comparison["added"])
        self.cli("patch", self.source(3), "examples/l2/catalog-01.patch", "--output", "output/stale.json", error="L2_STALE")
        self.check.assertFalse((self.output / "stale.json").exists())
        self.cli("store", "admit", "output/store", "stale", digest(read(self.output / "continue-0.json")), error="STORE_STALE")
        self.equal(self.cli("store", "admit", "output/store", "catalog-1", old_receipt["continuation"]), old_receipt)
        self.cli("store", "admit", "output/store", "catalog-1", digest(read(self.output / "continue-3.json")), error="STORE_OPERATION")
        artifact = read(self.output / "artifact-3.json")
        artifact["python"] += "\n# changed artifact\n"
        write_new(self.output / "tampered-artifact.json", artifact)
        self.cli("run", self.source(3), "--input", "output/input-3.json", "--artifact", "output/tampered-artifact.json", error="TOOL_ARTIFACT")
        self.cli("run", self.source(3), "--input", "output/input-3.json", "--artifact", "output/artifact-1.json", error="TOOL_ARTIFACT")
        self.equal(self.cli("store", "inspect", "output/store"), final)
        # Capture the independently selected expected identity before creating the backup.
        write_new(self.output / "expected-backup.json", {"snapshot": final["snapshot"]})
        exported = self.cli("store", "export", "output/store", "--output", "output/backup.json")
        expected_snapshot = read(self.output / "expected-backup.json")["snapshot"]
        self.equal(exported["snapshot"], expected_snapshot)
        self.cli("store", "restore", "output/wrong-restore", "--package", "output/backup.json",
            "--policy", "output/policy.json", "--snapshot", "sha256:" + "0" * 64, error="STORE_CORRUPT")
        self.check.assertFalse((self.output / "wrong-restore").exists())
        self.equal(self.cli("store", "restore", "output/restored", "--package", "output/backup.json",
            "--policy", "output/policy.json", "--snapshot", expected_snapshot), {"snapshot": expected_snapshot})
        self.equal(self.cli("store", "inspect", "output/restored"), final)
        for step in range(4):
            receipt = read(self.output / f"receipt-{step}.json")
            self.equal(self.cli("store", "inspect", "output/restored", "--operation", f"catalog-{step}"),
                {"operation": f"catalog-{step}", "status": "committed", "receipt": receipt, "head": final["head"]})
        self.cli("store", "export", "output/restored", "--output", "output/restored-backup.json")
        self.check.assertEqual((self.output / "backup.json").read_bytes(),
                               (self.output / "restored-backup.json").read_bytes())
        objects = read(self.output / "backup.json")["state"]["objects"]
        for step in range(4):
            self.equal(objects[self.source_id(step)], {"kind": "source", "value": read(self.root / self.source(step))})
        for name in PATCHES:
            patch = read(self.root / "examples/l2" / name)
            self.equal(objects[digest(patch)], {"kind": "change", "value": patch})
        self.equal({path: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                    for path in retained}, retained)
        return {"phase": "successor", "boundary": "continued-from-persisted-state",
                "head": final["head"], "snapshot": expected_snapshot, "restore_exact": True}


class BetaTests(unittest.TestCase):
    def test_cli_persisted_continuation_and_restore(self):
        report = {"schema": "bagaev-beta-primary/1", "status": "FAILED", "phases": []}
        receipt_path = os.environ.get("BAGAEV_BETA_RECEIPT")
        try:
            with tempfile.TemporaryDirectory(prefix="bagaev-beta-") as directory:
                clean = Path(directory)
                for name in ("src", "examples"):
                    shutil.copytree(ROOT / name, clean / name,
                                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                (clean / "tests").mkdir()
                shutil.copyfile(Path(__file__), clean / "tests/test_beta.py")
                frozen = {p.relative_to(clean).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for name in ("src", "examples") for p in (clean / name).rglob("*") if p.is_file()}
                for phase in ("predecessor", "successor"):
                    result = capture([sys.executable, "-B", "-S", "tests/test_beta.py", "--phase", phase],
                                     clean, 120, group=True)
                    result["phase"] = phase
                    primary = clean / "output" / f"{phase}-primary.json"
                    result["records"] = None
                    report["phases"].append(result)
                    if primary.exists():
                        result["records"] = read(primary)
                    stdout, stderr = streams(result)
                    self.assertFalse(result["timed_out"])
                    self.assertEqual(result["returncode"], 0, stderr.decode("utf-8", errors="replace"))
                    self.assertEqual(stderr, b"")
                    self.assertEqual(len(stdout.splitlines()), 1)
                    result["observation"] = json.loads(stdout)
                    self.assertEqual(result["observation"]["phase"], phase)
                    self.assertEqual(len(result["records"]), 26 if phase == "predecessor" else 43)
                    self.assertEqual(sum(r["returncode"] == 2 for r in result["records"]),
                                     1 if phase == "predecessor" else 6)
                    if phase == "predecessor":
                        self.assertEqual(result["observation"]["head"]["generation"], 2)
                        self.assertFalse((clean / "output/catalog-a2.json").exists())
                self.assertTrue(report["phases"][-1]["observation"]["restore_exact"])
                after = {p.relative_to(clean).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for name in ("src", "examples") for p in (clean / name).rglob("*") if p.is_file()}
                self.assertEqual(after, frozen)
                report["status"] = "PASSED"
        finally:
            # Optional private primary capture for an external trusted runner.
            # This path grants no execution authority and is never forwarded to children.
            if receipt_path is not None:
                write_new(receipt_path, report)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--phase" and sys.argv[2] in ("predecessor", "successor"):
        flow = _Flow(ROOT)
        try:
            result = getattr(flow, sys.argv[2])()
            sys.stdout.write(canonical(result).decode("utf-8") + "\n")
        finally:
            if flow.output.is_dir():
                write_new(flow.output / (sys.argv[2] + "-primary.json"), flow.records)
    else:
        unittest.main()
