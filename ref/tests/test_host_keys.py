"""HST-04/14/15/16: переименование CANON-11 ключей сохраняет строки и атомарность привязки."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))

from bagaev_ref.host import driver as D, migrate as M  # noqa: E402
from bagaev_ref.host.store import Store, schema_of  # noqa: E402
from bagaev_ref.kernel import canonical as C  # noqa: E402
from bagaev_ref.machine.runner import prepare  # noqa: E402

CASES = ROOT / "conformance" / "cases" / "migrate"
TABLE = "app.S.items"


def program(src):
    project, ir, pre = prepare([("app.bag", src.encode())])
    assert pre is None, pre
    return D.Program(project, ir)


def fixture(name):
    root = CASES / name
    old = program((root / "app.bag").read_text())
    new = program((root / "v2" / "app.bag").read_text())
    rows = json.loads((root / "case.json").read_text())["run"]["steps"][0]["rows"]
    return old, new, rows


def s(v):
    return {"type": "String", "value": v}


def i(v):
    return {"type": "Int64", "value": str(v)}


class HostKeys(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="bag-host-keys-")
        self.addCleanup(self.tmp.cleanup)

    def store(self, name, old, rows):
        st = Store(str(Path(self.tmp.name) / (name + ".db")))
        self.addCleanup(st.close)
        self.assertEqual(D.seed(st, old, TABLE, rows)["outcome"], "COMMITTED")
        return st

    def query(self, st, p, k):
        r = D.run_query(st, p, "app.get", [s(k)])
        self.assertEqual(r["outcome"], "RETURNED", r)
        return r["value"]

    def command(self, st, p, entry, args, seq):
        r = D.run_command(st, p, "app." + entry, args, {"namespace": "keys", "key": f"key-{seq:012d}"})
        self.assertEqual(r["outcome"], "COMMITTED", r)

    def raw(self, st):
        return st.db.execute('SELECT key, value FROM "t_aa0003" ORDER BY key').fetchall()

    def assert_current_keys(self, st, p):
        # Строгое декодирование проверяет и вложенные nominal-имена в физических байтах.
        for kb, _ in self.raw(st):
            C.unobserve(C.decode(bytes(kb)), p.tables[TABLE].key)

    def test_lookup_overwrite_remove_and_repeat(self):
        for name in ("key-rename-01", "nested-key-rename-01", "key-rename-value-01"):
            with self.subTest(case=name):
                old, new, rows = fixture(name)
                st = self.store(name, old, rows)
                self.assertEqual(D.run_query(st, new, "app.get", [s("a")])["code"], "SCHEMA_BINDING_MISMATCH")
                r = M.apply(st, new)
                self.assertEqual((r["outcome"], r["epoch"], r["state_version"]), ("APPLIED", 1, 2))
                self.assertEqual(len(self.raw(st)), 2)
                self.assert_current_keys(st, new)
                migrated = name == "key-rename-value-01"

                def value(n):
                    return {"type": "app.Tally", "fields": {"total": i(n), "bumps": i(1)}} if migrated else i(n)

                self.assertEqual(self.query(st, new, "a")["payload"], value(7))
                self.command(st, new, "put", [s("a"), i(8)], 1)
                self.assertEqual(len(self.raw(st)), 2)         # overwrite, а не второй логический a
                self.assertEqual(self.query(st, new, "a")["payload"], value(8))
                self.command(st, new, "remove", [s("a")], 2)
                self.assertEqual(len(self.raw(st)), 1)
                self.assertEqual(self.query(st, new, "a")["tag"], "None")
                self.assertEqual(self.query(st, new, "b")["payload"], value(9))
                before = tuple(st.db.iterdump())
                with patch.object(Store, "enc", side_effect=AssertionError("повтор не перекодирует")):
                    self.assertEqual(M.apply(st, new)["outcome"], "UP_TO_DATE")
                self.assertEqual(tuple(st.db.iterdump()), before)

    def test_table_rename_also_reencodes_keys(self):
        old, _, rows = fixture("key-rename-01")
        src = (CASES / "key-rename-01" / "v2" / "app.bag").read_text()
        new = program(src.replace("table items:", "table renamed:").replace("S.items", "S.renamed"))
        st = self.store("table-rename", old, rows)
        self.assertEqual(M.plan(st, new)["tables"][0]["action"], "rename")
        self.assertEqual(M.apply(st, new)["outcome"], "APPLIED")
        self.assertEqual(self.query(st, new, "a")["payload"], i(7))
        self.command(st, new, "put", [s("a"), i(8)], 1)
        self.assertEqual(len(self.raw(st)), 2)
        self.command(st, new, "remove", [s("a")], 2)
        self.assertEqual(len(self.raw(st)), 1)

    def test_recursive_nested_key_name_changes_binding(self):
        src = (CASES / "nested-key-rename-01" / "app.bag").read_text().replace(
            "part: Option<OldKey>", "part: Link").replace(
            "Some(OldKey(k))", "Link.More(LinkPart { token: OldKey(k), next: Link.End })") + '''
@id("ad0001")
pub type Link = enum { @id("ad0002") End, @id("ad0003") More(LinkPart), }
@id("ad0004")
pub type LinkPart = record { @id("ad0005") token: OldKey, @id("ad0006") next: Link, }
'''
        old, new = program(src), program(src.replace("OldKey", "NewKey"))
        a, b = (schema_of(p.project)["tables"]["aa0003"] for p in (old, new))
        self.assertEqual((a["key"], a["key_shape"]), (b["key"], b["key_shape"]))
        self.assertNotEqual(a["key_encoding"], b["key_encoding"])
        st = self.store("recursive", old, [])
        self.command(st, old, "put", [s("a"), i(7)], 1)
        self.assertEqual(M.apply(st, new)["outcome"], "APPLIED")
        self.assert_current_keys(st, new)
        self.assertEqual(self.query(st, new, "a")["payload"], i(7))
        self.command(st, new, "remove", [s("a")], 2)
        self.assertEqual(self.raw(st), [])

    def test_failed_value_migration_rolls_back_key_bytes_and_binding(self):
        old, new, rows = fixture("key-rename-rollback-01")
        st = self.store("rollback", old, rows)
        before = tuple(st.db.iterdump())
        r = M.apply(st, new)
        self.assertEqual((r["code"], r["data"]["error"]),
                         ("MIGRATION_FAILED", {"type": "app.MigErr", "tag": "Negative"}))
        self.assertEqual(tuple(st.db.iterdump()), before)
        self.assertFalse(st.db.in_transaction)
        self.assertEqual(self.query(st, old, "a")["payload"], i(7))
        self.assertEqual(self.query(st, old, "b")["payload"], i(-1))

    def test_collision_never_silently_discards_a_row(self):
        old, new, rows = fixture("key-rename-01")
        st = self.store("collision", old, rows)
        # Старый дефект мог оставить две строки одного логического ключа с разными именами типа.
        kb = C.encode({"type": "app.NewKey", "value": s("a")})
        st.db.execute('INSERT INTO "t_aa0003" VALUES (?, ?)', (kb, C.encode(i(99))))
        before = tuple(st.db.iterdump())
        with self.assertRaises(sqlite3.IntegrityError):
            M.apply(st, new)
        self.assertFalse(st.db.in_transaction)
        self.assertEqual(st.meta("schema"), old.schema)
        self.assertEqual((st.meta("epoch"), st.meta("state_version")), ("0", "1"))
        self.assertEqual(len(self.raw(st)), 3)
        self.assertEqual(M.abort(st)["dropped"], [])
        self.assertEqual(tuple(st.db.iterdump()), before)

    def test_legacy_binding_is_upgraded_without_reinitializing_data(self):
        for renamed in (False, True):
            with self.subTest(renamed=renamed):
                old, new, rows = fixture("nested-key-rename-01")
                target = new if renamed else old
                st = self.store("legacy-" + str(renamed), old, rows)
                legacy = schema_of(old.project)
                for table in legacy["tables"].values():
                    table.pop("key_encoding")
                st.db.execute("BEGIN IMMEDIATE")
                st.set_meta("schema_json", C.encode(legacy).decode())
                st.set_meta("schema", C.digest("data-schema", "1", legacy))
                st.db.execute("COMMIT")
                raw_before = self.raw(st)
                self.assertEqual(D.run_query(st, target, "app.get", [s("a")])["code"], "SCHEMA_BINDING_MISMATCH")
                self.assertEqual(self.raw(st), raw_before)
                r = M.apply(st, target)
                self.assertEqual((r["outcome"], r["rows"], r["epoch"], r["state_version"]), ("APPLIED", 0, 1, 2))
                self.assertEqual(self.query(st, target, "a")["payload"], i(7))
                self.assertEqual(self.query(st, target, "b")["payload"], i(9))
                self.assertEqual(len(self.raw(st)), 2)
                self.assert_current_keys(st, target)
                self.assertEqual(json.loads(st.meta("schema_json")), schema_of(target.project))

    def test_real_process_crashes_keep_one_complete_binding(self):
        for name in ("nested-key-rename-01", "key-rename-value-01"):
            old, new, rows = fixture(name)
            for point in ("migration_prepare", "before_swap_commit", "after_swap"):
                with self.subTest(case=name, crash=point):
                    st = self.store(name + "-" + point, old, rows)
                    before = self.raw(st)
                    st.close()
                    env = dict(os.environ, PYTHONPATH=str(ROOT / "ref"), BAG_CRASH_AT=point)
                    proc = subprocess.run([sys.executable, "-B", "-m", "bagaev_ref", "migrate", "apply",
                                           str(CASES / name / "v2"), "--db", st.path, "--json"],
                                          env=env, capture_output=True, timeout=30)
                    self.assertEqual((proc.returncode, proc.stdout), (137, b""), proc.stderr)
                    st = Store(st.path)
                    self.addCleanup(st.close)
                    committed = point == "after_swap"
                    self.assertEqual(st.meta("schema"), new.schema if committed else old.schema)
                    self.assertEqual((st.meta("epoch"), st.meta("state_version")), ("1", "2") if committed else ("0", "1"))
                    if committed:
                        self.assert_current_keys(st, new)
                    else:
                        self.assertEqual(self.raw(st), before)
                        self.assertNotEqual(st.meta("writer_lock"), "")
                    r = M.apply(st, new)
                    self.assertEqual(r["outcome"], "UP_TO_DATE" if committed else "APPLIED")
                    self.assertEqual((st.meta("epoch"), st.meta("state_version"), st.meta("writer_lock")), ("1", "2", ""))
                    self.assertEqual(len(self.raw(st)), 2)
                    self.assert_current_keys(st, new)
                    value = self.query(st, new, "a")["payload"]
                    self.assertEqual(value["fields"]["total"] if name == "key-rename-value-01" else value, i(7))


if __name__ == "__main__":
    unittest.main()
