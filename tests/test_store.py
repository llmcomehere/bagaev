"""Authored M4 boundary checks; execution needs a separately reviewed profile."""
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from src import bagaev as CLI, bagaev_l2 as L2, bagaev_store as S

ROOT = Path(__file__).resolve().parents[1]


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def identity(value):
    return "sha256:" + hashlib.sha256(raw(value)).hexdigest()


def program(body):
    definition = {"params": ["x"], "body": body}
    return {"schema": "bagaev-l2/1", "entry": "main", "definitions": {"main": definition},
            "pins": {"main": identity({"schema": "bagaev-l2-definition/1",
                                        "definition": definition, "dependencies": {}})}}


def policy():
    return {"schema": "bagaev-store-policy/1", "contract": {
        "schema": "bagaev-store-contract/1", "assumptions": ["Synthetic selected input only"],
        "cases": [{"id": "true-zero", "input": True, "expected": {"value": 0}}]}}


def change(before, after):
    return {"schema": "bagaev-l2-patch/1", "base": identity(before), "target": identity(after),
            "add": {}, "replace": after["definitions"]}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bagaev-store-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "store"
        self.policy = policy()
        S.create(self.path, self.policy)
        self.store = S.Store(self.path)
        self.addCleanup(self.store.close)
        self.a0, self.a1, self.bad = program(0), program(["if", ["var", "x"], 0, 1]), program(2)
        self.s0 = self.store.put("source", self.a0)
        self.s1 = self.store.put("source", self.a1)
        self.sb = self.store.put("source", self.bad)
        self.c01 = self.store.put("change", change(self.a0, self.a1))
        self.c10 = self.store.put("change", change(self.a1, self.a0))

    def continuation(self, source, *, base=None, changes=None, evidence=None, **updates):
        value = {"schema": "bagaev-store-continuation/1", "task": "synthetic-change",
                 "intent": "Preserve the pinned case", "base": self.store.inspect()["head"] if base is None else base,
                 "target": source, "changes": [] if changes is None else changes,
                 "contract": identity(self.policy["contract"]), "required": ["true-zero"],
                 "evidence": self.store.check(source) if evidence is None else evidence,
                 "unresolved": [], "effects": [], "hypotheses": []}
        value.update(updates)
        return self.store.put("continuation", value)

    def refuses(self, code, function, *args):
        before = self.store.export()
        with self.assertRaises(S.StoreError) as raised:
            function(*args)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(self.store.export(), before)

    def test_candidates_pins_detachment_and_actual_checks(self):
        self.assertEqual(self.s0, identity(self.a0))
        self.assertEqual(self.store.inspect()["head"], {"generation": 0, "source": None})
        detached = self.store.get(self.s0)
        detached["value"]["definitions"]["main"]["body"] = 900
        self.assertEqual(self.store.get(self.s0)["value"], self.a0)
        evidence = self.store.check(self.s0)
        observed = self.store.get(evidence[0])["value"]
        self.assertEqual(observed["source"], self.s0)
        self.assertEqual(observed["input"], identity(True))
        self.assertEqual(observed["result"], {"status": "passed", "actual": {"value": 0}})
        failed = self.store.get(self.store.check(self.sb)[0])["value"]
        self.assertEqual(failed["result"], {"status": "failed", "actual": {"value": 2}})
        self.assertEqual(self.store.inspect()["head"]["generation"], 0)
        continuation = self.continuation(self.s0, evidence=evidence)
        receipt = self.store.admit("first", continuation)
        self.assertEqual(receipt["head"], {"generation": 1, "source": self.s0})
        self.assertEqual(self.store.get(self.s0)["value"], self.a0)

    def test_atomic_stale_and_monotonic_aba(self):
        initial = self.continuation(self.s0)
        self.store.admit("zero", initial)
        base = self.store.inspect()["head"]
        first = self.continuation(self.s1, changes=[self.c01])
        stale = self.continuation(self.s1, base=base, changes=[self.c01], intent="Stale proposal")
        self.store.admit("one", first)
        self.refuses("STORE_STALE", self.store.admit, "stale", stale)
        back = self.continuation(self.s0, changes=[self.c10])
        self.store.admit("back", back)
        self.assertEqual(self.store.inspect()["head"], {"generation": 3, "source": self.s0})
        self.refuses("STORE_STALE", self.store.admit, "aba", stale)
        self.assertEqual(self.store.inspect("stale")["status"], "absent")

    def test_operation_replay_and_conflicting_reuse(self):
        original = self.continuation(self.s0)
        receipt = self.store.admit("stable-id", original)
        next_id = self.continuation(self.s1, changes=[self.c01])
        self.store.admit("next", next_id)
        before = self.store.export()
        self.assertEqual(self.store.admit("stable-id", original), receipt)
        self.assertEqual(self.store.export(), before)
        self.refuses("STORE_OPERATION", self.store.admit, "stable-id", next_id)
        with S.Store(self.path) as fresh:
            result = fresh.inspect("stable-id")
            self.assertEqual(result["receipt"], receipt)
            self.assertEqual(result["head"], {"generation": 2, "source": self.s1})

    def test_forged_stale_failed_unknown_and_missing_evidence(self):
        genuine = self.store.check(self.s0)
        wrong_source = self.continuation(self.s1, evidence=genuine)
        self.refuses("STORE_CHECK", self.store.admit, "wrong-source", wrong_source)
        missing = self.continuation(self.s0, evidence=[])
        self.refuses("STORE_CHECK", self.store.admit, "missing", missing)
        failed = self.continuation(self.sb)
        self.refuses("STORE_CHECK", self.store.admit, "failed", failed)
        forged = self.store.get(genuine[0])["value"]
        forged["source"] = self.sb  # Correct claimed expected value, wrong actual program.
        assertion = self.store.put("evidence", forged)
        candidate = self.continuation(self.sb, evidence=[assertion])
        self.refuses("STORE_CHECK", self.store.admit, "forged", candidate)
        forged["source"] = self.s0
        forged["checker"]["implementation"] = "sha256:" + "0" * 64
        foreign = self.store.put("evidence", forged)
        candidate = self.continuation(self.s0, evidence=[foreign])
        self.refuses("STORE_CHECK", self.store.admit, "foreign-checker", candidate)
        forged["result"]["status"] = "unknown"
        unknown = self.store.put("evidence", forged)
        candidate = self.continuation(self.s0, evidence=[unknown])
        self.refuses("STORE_CHECK", self.store.admit, "unknown", candidate)

    def test_context_obligations_effects_and_change_references(self):
        for key, value in (("unresolved", ["Acceptance unresolved"]),
                           ("effects", [{"id": "remote", "status": "unknown", "detail": "No receiver receipt"}]),
                           ("effects", [{"id": "remote", "status": "failed", "detail": "Declared failed"}])):
            candidate = self.continuation(self.s0, **{key: value})
            self.refuses("STORE_CHECK", self.store.admit, "blocked", candidate)
        continuation = self.continuation(self.s0, hypotheses=[{"text": "Unverified claim", "sources": [self.s0]}])
        self.store.admit("initial", continuation)
        value = self.store.get(continuation)["value"]
        value["base"] = self.store.inspect()["head"]
        value["target"] = self.s1
        self.refuses("STORE_FORMAT", self.store.put, "continuation", value)
        value["changes"] = [self.c01]
        value["required"] = []
        self.refuses("STORE_FORMAT", self.store.put, "continuation", value)
        value["required"] = ["true-zero"]
        value["hypotheses"][0]["sources"] = ["sha256:" + "1" * 64]
        self.refuses("STORE_FORMAT", self.store.put, "continuation", value)

    def test_deterministic_import_and_explicit_restore_authority(self):
        first = self.continuation(self.s0)
        self.store.admit("zero", first)
        second = self.continuation(self.s1, changes=[self.c01])
        receipt = self.store.admit("one", second)
        exported = self.store.export()
        self.assertEqual(exported, self.store.export())
        self.assertEqual(raw(json.loads(exported)), exported)
        snapshot = self.store.inspect()["snapshot"]
        self.assertEqual(identity(json.loads(exported)["state"]), snapshot)
        imported_path = self.root / "imported"
        S.import_package(imported_path, exported, self.policy)
        with S.Store(imported_path) as imported:
            self.assertEqual(imported.inspect()["head"], {"generation": 0, "source": None})
            self.assertEqual(imported.inspect("one")["status"], "absent")
            self.assertEqual(imported.inspect()["historical"], 1)
            self.assertEqual(imported.get(self.s1), self.store.get(self.s1))
            self.assertNotEqual(imported.inspect()["snapshot"], snapshot)
        restored_path = self.root / "restored"
        S.restore(restored_path, exported, self.policy, snapshot)
        with S.Store(restored_path) as restored:
            self.assertEqual(restored.export(), exported)
            self.assertEqual(restored.inspect("one")["receipt"], receipt)
            self.assertEqual(restored.admit("one", second), receipt)
        destination = self.root / "must-not-exist"
        with self.assertRaises(S.StoreError):
            S.restore(destination, exported, self.policy, self.s1)
        self.assertFalse(destination.exists())
        changed = copy.deepcopy(self.policy)
        changed["contract"]["assumptions"].append("Changed receiver scope")
        with self.assertRaises(S.StoreError) as error:
            S.restore(destination, exported, changed, snapshot)
        self.assertEqual(error.exception.code, "STORE_POLICY")
        self.assertFalse(destination.exists())

    def test_canonical_integrity_and_no_partial_import(self):
        exported = self.store.export()
        corruptions = [exported + b"\n", exported[:-1], b"{}", b'{"x":0,"x":1}',
                       b'NaN', b'"\\ud800"', b'[' * 1024 + b']' * 1024,
                       b" " * (S.LIMIT + 1)]
        changed = json.loads(exported)
        changed["state"]["objects"][self.s0]["value"]["entry"] = "absent"
        changed["snapshot"] = identity(changed["state"])
        corruptions.append(raw(changed))
        for index, data in enumerate(corruptions):
            destination = self.root / f"invalid-{index}"
            with self.subTest(index=index), self.assertRaises(S.StoreError):
                S.import_package(destination, data, self.policy)
            self.assertFalse(destination.exists())
        backup = self.root / "backup.json"
        S.backup(backup, exported)
        self.assertEqual(backup.read_bytes(), exported)
        with self.assertRaises(S.StoreError):
            S.backup(backup, exported)
        self.assertEqual(backup.read_bytes(), exported)
        with self.assertRaises(S.StoreError):
            S.import_package(self.path, exported, self.policy)
        self.assertEqual(self.store.export(), exported)

    def test_local_corruption_symlinks_and_bound_refusal(self):
        link = self.root / "link"
        link.symlink_to(self.path, target_is_directory=True)
        with self.assertRaises(S.StoreError) as error:
            S.Store(link)
        self.assertEqual(error.exception.code, "STORE_PATH")
        with mock.patch.object(S, "OBJECT_LIMIT", len(self.store.inspect()["objects"])):
            self.refuses("STORE_BOUND", self.store.put, "source", program(3))
        malformed = self.root / "corrupt"
        S.create(malformed, self.policy)
        connection = sqlite3.connect(malformed / "state.sqlite")
        try:
            connection.execute("UPDATE state SET payload=?", (b"{}",))
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(S.StoreError):
            S.Store(malformed)

    def test_malformed_referenced_records_refuse_before_import_creation(self):
        package = json.loads(self.store.export())
        contract_id = identity(self.policy["contract"])
        evidence = {"schema": "bagaev-store-evidence/1", "source": self.s0,
                    "contract": contract_id, "case": "true-zero", "input": identity(True),
                    "checker": {"version": "shape-2", "implementation": "sha256:" + "0" * 64},
                    "assumptions": self.policy["contract"]["assumptions"],
                    "result": {"status": "passed", "actual": {"value": 0}}}
        evidence_id = identity(evidence)
        # The referencing object must be visited before the malformed record.
        self.assertLess(evidence_id, contract_id)
        package["state"]["objects"][evidence_id] = {"kind": "evidence", "value": evidence}
        for index, record in enumerate(({}, {"value": self.policy["contract"]},
                                         {"kind": "contract"}, [])):
            malformed = copy.deepcopy(package)
            malformed["state"]["objects"][contract_id] = record
            malformed["snapshot"] = identity(malformed["state"])
            destination = self.root / f"malformed-reference-{index}"
            with self.subTest(record=record), self.assertRaises(S.StoreError) as raised:
                S.import_package(destination, raw(malformed), self.policy)
            self.assertEqual(raised.exception.code, "STORE_FORMAT")
            self.assertFalse(destination.exists())

    def test_malformed_contract_values_refuse_before_forward_reference_use(self):
        package = json.loads(self.store.export())
        policy_file = self.root / "contract-value-policy.json"
        policy_file.write_bytes(raw(self.policy))
        variants = (
            (None, "payload-1"),
            ({}, "payload-0"),
            ({"schema": "bagaev-store-contract/1", "assumptions": [],
              "cases": [{"input": True, "expected": {"value": 0}}]}, "payload-0"),
        )
        for index, (value, version) in enumerate(variants):
            contract_id = identity(value)
            evidence = {"schema": "bagaev-store-evidence/1", "source": self.s0,
                        "contract": contract_id, "case": "true-zero", "input": identity(True),
                        "checker": {"version": version, "implementation": "sha256:" + "0" * 64},
                        "assumptions": self.policy["contract"]["assumptions"],
                        "result": {"status": "passed", "actual": {"value": 0}}}
            evidence_id = identity(evidence)
            self.assertLess(evidence_id, contract_id)
            malformed = copy.deepcopy(package)
            objects = malformed["state"]["objects"]
            objects[contract_id] = {"kind": "contract", "value": value}
            objects[evidence_id] = {"kind": "evidence", "value": evidence}
            self.assertTrue(all(key == identity(record["value"]) for key, record in objects.items()))
            malformed["snapshot"] = identity(malformed["state"])
            data = raw(malformed)
            destination = self.root / f"contract-value-{index}"
            with self.subTest(index=index), self.assertRaises(S.StoreError) as raised:
                S.import_package(destination, data, self.policy)
            self.assertEqual(raised.exception.code, "STORE_FORMAT")
            self.assertFalse(destination.exists())
            document = self.root / f"contract-value-{index}.json"
            document.write_bytes(data)
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = CLI.main(["store", "import", str(destination), "--package", str(document),
                                   "--policy", str(policy_file)])
            self.assertEqual(status, 2)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(stdout.getvalue().count("\n"), 1)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["command"], "store")
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], "STORE_FORMAT")
            self.assertFalse(destination.exists())
            self.assertEqual(self.store.export(), raw(package))

    def test_cli_oversized_inputs_and_stream_growth_are_bounded_refusals(self):
        oversized = self.root / "oversized.json"
        with oversized.open("wb") as stream:
            stream.truncate(S.LIMIT + 1)
        policy_file = self.root / "receiver-policy.json"
        policy_file.write_bytes(raw(self.policy))
        destination = self.root / "oversized-destination"
        commands = (
            ["store", "init", destination, "--policy", oversized],
            ["store", "put", self.path, "source", oversized],
            ["store", "import", destination, "--package", oversized, "--policy", policy_file],
            ["store", "restore", destination, "--package", oversized, "--policy", policy_file,
             "--snapshot", self.store.inspect()["snapshot"]],
        )
        before = self.store.export()
        actual_fstat, actual_read = os.fstat, os.read

        def before_growth(fd):
            info = actual_fstat(fd)
            # Model the file growing after fstat: keep its real regular-file tag,
            # but report the earlier zero size so the streaming guard must act.
            return os.stat_result((*info[:6], 0, *info[7:]))

        for growth in (False, True):
            for command in commands:
                stdout, stderr = io.StringIO(), io.StringIO()
                observation = (mock.patch.object(CLI.os, "fstat", side_effect=before_growth)
                               if growth else contextlib.nullcontext())
                with self.subTest(action=command[1], growth=growth), observation, \
                        mock.patch.object(CLI.os, "read", wraps=actual_read) as reads, \
                        contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    status = CLI.main(list(map(str, command)))
                    self.assertEqual(status, 2)
                    self.assertEqual(stderr.getvalue(), "")
                    self.assertEqual(stdout.getvalue().count("\n"), 1)
                    result = json.loads(stdout.getvalue())
                    self.assertEqual(result["schema"], "bagaev-toolchain/1")
                    self.assertEqual(result["command"], "store")
                    self.assertFalse(result["ok"])
                    self.assertEqual(result["error"]["code"], "STORE_BOUND")
                    self.assertEqual(reads.called, growth)
                self.assertFalse(destination.exists())
                self.assertEqual(self.store.export(), before)

    def test_competing_connections_and_declared_policy(self):
        candidate = self.continuation(self.s0)
        with S.Store(self.path) as other:
            other.connection.execute("BEGIN IMMEDIATE")
            try:
                with self.assertRaises(S.StoreError) as error:
                    self.store.admit("contended", candidate)
                self.assertEqual(error.exception.code, "STORE_BUSY")
            finally:
                other.connection.rollback()
        self.assertEqual(self.store.inspect("contended")["status"], "absent")
        receipt = self.store.admit("contended", candidate)
        self.assertEqual(receipt["head"]["generation"], 1)
        different = copy.deepcopy(self.policy["contract"])
        different["assumptions"] = ["Unselected policy"]
        foreign_contract = self.store.put("contract", different)
        value = self.store.get(candidate)["value"]
        value["base"] = receipt["head"]
        value["contract"] = foreign_contract
        foreign = self.store.put("continuation", value)
        self.refuses("STORE_POLICY", self.store.admit, "different-policy", foreign)

    def test_transaction_failure_and_committed_unobserved_receipt(self):
        candidate = self.continuation(self.s0)
        real = self.store.connection

        class Connection:
            def __init__(self, committed):
                self.committed = committed
            def __getattr__(self, name):
                return getattr(real, name)
            def commit(self):
                if self.committed:
                    real.commit()
                raise OSError("synthetic lost response")

        before = self.store.export()
        for committed in (False, True):
            with mock.patch.object(self.store, "connection", Connection(committed)):
                with self.assertRaises(OSError):
                    self.store.admit("recover", candidate)
            with S.Store(self.path) as fresh:
                observation = fresh.inspect("recover")
                self.assertEqual(observation["status"], "committed" if committed else "absent")
                if not committed:
                    self.assertEqual(fresh.export(), before)
                else:
                    self.assertEqual(fresh.admit("recover", candidate), observation["receipt"])

    def test_fresh_process_precommit_and_postcommit_recovery(self):
        candidate = self.continuation(self.s0)
        # Guest-only interruption at SQLite commit, never a product control.
        script = '''
import os, sys
from src import bagaev_store as S
with S.Store(sys.argv[1]) as store:
    actual = store.connection
    actual.execute("PRAGMA cache_size=1")
    class Connection:
        def __getattr__(self, name): return getattr(actual, name)
        def commit(self):
            if sys.argv[3] == "after": actual.commit()
            os._exit(72 if sys.argv[3] == "after" else 71)
    store.connection = Connection()
    store.admit("crash-operation", sys.argv[2])
'''
        before = self.store.export()
        for phase, status in (("before", 71), ("after", 72)):
            process = subprocess.run([sys.executable, "-B", "-c", script, str(self.path), candidate, phase],
                                     cwd=ROOT, env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
                                     capture_output=True, timeout=30)
            self.assertEqual(process.returncode, status, process.stderr)
            self.assertEqual(process.stdout, b"")
            with S.Store(self.path) as fresh:
                result = fresh.inspect("crash-operation")
                self.assertEqual(result["status"], "absent" if phase == "before" else "committed")
                if phase == "before":
                    self.assertEqual(fresh.export(), before)
                else:
                    self.assertEqual(fresh.admit("crash-operation", candidate), result["receipt"])

    def test_cli_json_envelope_and_explicit_store_commands(self):
        def cli(arguments, status=0):
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                actual = CLI.main(list(map(str, arguments)))
            self.assertEqual(actual, status, stderr.getvalue())
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(stdout.getvalue().count("\n"), 1)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["schema"], "bagaev-toolchain/1")
            self.assertEqual(result["command"], "store")
            self.assertEqual(result["ok"], status == 0)
            return result.get("result", result.get("error"))
        initial = self.continuation(self.s0)
        receipt = cli(["store", "admit", self.path, "cli-id", initial])
        result = cli(["store", "inspect", self.path, "--operation", "cli-id"])
        self.assertEqual(result["receipt"], receipt)
        backup = self.root / "cli-backup.json"
        exported = cli(["store", "export", self.path, "--output", backup])
        self.assertEqual(exported["snapshot"], self.store.inspect()["snapshot"])
        self.assertEqual(cli(["store", "export", self.path, "--output", backup], 2)["code"], "STORE_PATH")
        document = self.root / "policy.json"
        document.write_bytes(raw(self.policy))
        restored = self.root / "cli-restored"
        cli(["store", "restore", restored, "--package", backup, "--policy", document,
             "--snapshot", exported["snapshot"]])
        self.assertEqual(cli(["store", "inspect", restored])["head"], receipt["head"])


if __name__ == "__main__":
    unittest.main()
