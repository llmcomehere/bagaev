"""HOST-1: команды с квитанциями, идемпотентность, полномочия, доставка событий, replay, миграция,
точки сбоя с kill -9 и восстановление по квитанции (spec/runtime/host.md).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))

from bagaev_ref.host import driver as D, migrate as M  # noqa: E402
from bagaev_ref.host.store import Store  # noqa: E402
from bagaev_ref.machine.runner import prepare  # noqa: E402

APP = ROOT / "examples" / "authorship"
ENTRY = "blog.editor.set_authors"
ARTICLES, PEOPLE, ACL, INDEX = (f"blog.db.Blog.{t}" for t in ("articles", "people", "acl", "author_index"))


def load(root: Path):
    return [(f.relative_to(root).as_posix(), f.read_bytes()) for f in sorted(root.rglob("*.bag"))]


def program(root: Path) -> D.Program:
    project, prog, pre = prepare(load(root))
    assert pre is None, pre
    return D.Program(project, prog)


def s(v):
    return {"type": "String", "value": v}


def pid(v):
    return {"type": "blog.people.PersonId", "value": s(v)}


def aid(v):
    return {"type": "blog.articles.ArticleId", "value": s(v)}


def actor(v):
    return {"type": "blog.acl.ActorId", "value": s(v)}


def ids(*xs):
    return {"type": "Seq<blog.people.PersonId>", "items": [pid(x) for x in xs]}


def article(a, *authors, rev="1"):
    return {"type": "blog.articles.Article", "fields": {
        "id": aid(a), "title": s("T" + a), "revision": {"type": "Int64", "value": rev},
        "authors": {"type": "blog.authorship.Authors", "value": ids(*authors)}}}


def article_v1(a, author, rev="1"):
    return {"type": "blog.articles.ArticleV1", "fields": {
        "id": aid(a), "title": s("T" + a), "author": pid(author), "revision": {"type": "Int64", "value": rev}}}


def key(n: int) -> dict:
    return {"namespace": "editor", "key": f"k-{n:016d}"}


PROGRAM = program(APP)


def seeded(db: str) -> Store:
    st = Store(db)
    people = [[pid(p), {"type": "blog.people.Person", "fields": {"id": pid(p), "display_name": s(p.title())}}]
              for p in ("ann", "bob", "cid")]
    assert D.seed(st, PROGRAM, PEOPLE, people)["outcome"] == "COMMITTED"
    acl = [[actor("ed"), {"type": "blog.acl.Roles", "fields": {"editor": {"type": "Bool", "value": True}}}],
           [actor("ro"), {"type": "blog.acl.Roles", "fields": {"editor": {"type": "Bool", "value": False}}}]]
    assert D.seed(st, PROGRAM, ACL, acl)["outcome"] == "COMMITTED"
    assert D.seed(st, PROGRAM, ARTICLES, [[aid("a1"), article("a1", "ann")]])["outcome"] == "COMMITTED"
    return st


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bag-host-")
        self.db = os.path.join(self.tmp, "app.db")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class Commands(Base):
    def test_commit_then_receipt_replay(self):
        st = seeded(self.db)
        sv0 = int(st.meta("state_version"))
        r1 = D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("ann", "bob")], key(1))
        self.assertEqual((r1["outcome"], r1["replayed"], r1["state_version"]), ("COMMITTED", False, sv0 + 1))
        state = D.dump(st, PROGRAM)
        self.assertEqual(state["tables"][ARTICLES][0][1], article("a1", "ann", "bob", rev="2"))
        self.assertEqual(len(state["outbox"]), 1)
        r2 = D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("ann", "bob")], key(1))
        self.assertEqual((r2["outcome"], r2["replayed"], r2["value"]), ("COMMITTED", True, r1["value"]))
        self.assertEqual(D.dump(st, PROGRAM), state)          # повтор ничего не меняет (HST-06)

    def test_idempotency_conflict(self):
        st = seeded(self.db)
        D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(1))
        r = D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("cid")], key(1))
        self.assertEqual((r["outcome"], r["code"]), ("REFUSED", "IDEMPOTENCY_CONFLICT"))

    def test_err_is_final_and_changes_no_data(self):
        st = seeded(self.db)
        before = D.dump(st, PROGRAM)
        r = D.run_command(st, PROGRAM, ENTRY, [actor("ro"), aid("a1"), ids("bob")], key(2))
        self.assertEqual((r["outcome"], r["final"]), ("ABORTED", True))
        self.assertEqual(r["value"]["tag"], "Err")
        after = D.dump(st, PROGRAM)
        self.assertEqual(after["tables"], before["tables"])
        self.assertEqual(after["outbox"], [])
        self.assertEqual(after["state_version"], before["state_version"] + 1)   # квитанция — запись (D43)
        self.assertEqual(D.status(st, key(2))["receipt_outcome"], "ABORTED")

    def test_receipt_checked_before_stale_guard(self):
        st = seeded(self.db)
        sv = int(st.meta("state_version"))
        r1 = D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(3), expected_state=sv)
        self.assertEqual(r1["outcome"], "COMMITTED")
        r2 = D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(3), expected_state=sv)
        self.assertEqual((r2["outcome"], r2["replayed"]), ("COMMITTED", True))   # не STALE_STATE (D44)
        r3 = D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("cid")], key(4), expected_state=sv)
        self.assertEqual(r3["code"], "STALE_STATE")
        self.assertEqual(D.status(st, key(4))["outcome"], "ABSENT_AT_READ")      # отказ до допуска не резервирует

    def test_prelaunch_refusals_reserve_nothing(self):
        st = seeded(self.db)
        bad = [("blog.editor.nope", [actor("ed")], key(5), "UNKNOWN_ENTRYPOINT"),
               (ENTRY, [actor("ed")], key(5), "REQUEST_INVALID"),
               (ENTRY, [actor("ed"), aid("a1"), ids("bob")], {"namespace": "editor", "key": "short"}, "REQUEST_INVALID")]
        for entry, args, kr, code in bad:
            self.assertEqual(D.run_command(st, PROGRAM, entry, args, kr)["code"], code)
        self.assertEqual(D.status(st, key(5))["outcome"], "ABSENT_AT_READ")

    def test_fault_rolls_back_without_receipt(self):
        st = seeded(self.db)
        big = {"type": "Int64", "value": str(2**63 - 1)}
        a = article("a9", "ann")
        a["fields"]["revision"] = big
        D.seed(st, PROGRAM, ARTICLES, [[aid("a9"), a]])
        before = D.dump(st, PROGRAM)
        r = D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a9"), ids("bob")], key(6))
        self.assertEqual((r["outcome"], r["final"], r["termination"], r["code"]), ("ABORTED", False, "FAULT", "ARITHMETIC_OVERFLOW"))
        self.assertEqual(D.dump(st, PROGRAM), before)
        self.assertEqual(D.status(st, key(6))["outcome"], "ABSENT_AT_READ")


class Authority(Base):
    def test_policy_denies_entrypoint(self):
        st = seeded(self.db)
        policy = {"callers": {"ui": [ENTRY]}}
        r = D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(7), caller="bot", policy=policy)
        self.assertEqual(r["code"], "ACCESS_DENIED")
        self.assertEqual(D.status(st, key(7))["outcome"], "ABSENT_AT_READ")
        r = D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(7), caller="ui", policy=policy)
        self.assertEqual(r["outcome"], "COMMITTED")

    def test_perform_checked_against_granted_atoms(self):
        st = seeded(self.db)
        before = D.dump(st, PROGRAM)
        policy = {"revoke": ["emits blog.events.AuthorshipChanged"]}
        r = D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(8), policy=policy)
        self.assertEqual((r["termination"], r["code"]), ("IMPLEMENTATION_STOP", "ACCESS_DENIED"))
        self.assertEqual(D.dump(st, PROGRAM), before)            # put до emit тоже откатан


class Events(Base):
    def test_deliver_once_and_project(self):
        st = seeded(self.db)
        D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("ann", "bob")], key(1))
        D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("cid")], key(2))
        out = D.deliver(st, PROGRAM)
        self.assertEqual([(r["seq"], r["outcome"]) for r in out], [(1, "COMMITTED"), (2, "COMMITTED")])
        self.assertEqual(D.deliver(st, PROGRAM), [])
        again = D.deliver(st, PROGRAM, seq=1)
        self.assertEqual((again[0]["outcome"], again[0]["replayed"]), ("COMMITTED", True))   # дедуп (handler, seq)
        index = {k["value"]["value"]: [x["value"]["value"] for x in v["items"]]
                 for k, v in D.dump(st, PROGRAM)["tables"][INDEX]}
        self.assertEqual(index, {"ann": [], "bob": [], "cid": ["a1"]})

    def test_replay_matches_and_detects_divergence(self):
        st = seeded(self.db)
        D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(1))
        D.deliver(st, PROGRAM)
        self.assertEqual(D.replay(st, PROGRAM, "editor:" + key(1)["key"])["outcome"], "REPLAY_MATCH")
        self.assertEqual(D.replay(st, PROGRAM, "blog.indexer.index_authorship:1")["outcome"], "REPLAY_MATCH")
        # replay ничего не пишет: ни таблиц, ни outbox, ни квитанций (T06-C04)
        before = D.dump(st, PROGRAM), st.db.execute("SELECT count(*) FROM journal").fetchone()
        D.replay(st, PROGRAM, "editor:" + key(1)["key"])
        D.replay(st, PROGRAM, "blog.indexer.index_authorship:1")
        self.assertEqual((D.dump(st, PROGRAM), st.db.execute("SELECT count(*) FROM journal").fetchone()), before)
        # replay не читает таблицы: после изменения данных результат тот же
        st.db.execute(f'DELETE FROM "t_8kzanb"')
        self.assertEqual(D.replay(st, PROGRAM, "editor:" + key(1)["key"])["outcome"], "REPLAY_MATCH")
        # подменённый журнал — расхождение
        row = st.db.execute("SELECT seq, body FROM journal WHERE ref = ?", ("editor:" + key(1)["key"],)).fetchone()
        body = json.loads(bytes(row[1]))
        body["ops"] = body["ops"][:2]
        from bagaev_ref.kernel import canonical as C
        st.db.execute("UPDATE journal SET body = ? WHERE seq = ?", (C.encode(body), row[0]))
        self.assertEqual(D.replay(st, PROGRAM, "editor:" + key(1)["key"])["outcome"], "REPLAY_DIVERGENCE")


def make_v1(dst: Path) -> Path:
    """Прежняя версия приложения: статья с одним автором; модули, которым нужна новая схема, убраны."""
    shutil.copytree(APP, dst)
    db = dst / "blog" / "db.bag"
    db.write_text(db.read_text(encoding="utf-8").replace("Map<ArticleId, Article>", "Map<ArticleId, ArticleV1>")
                  .replace("{ArticleId, Article}", "{ArticleId, ArticleV1}"), encoding="utf-8")
    for f in ("editor", "migration", "tests"):
        (dst / "blog" / f"{f}.bag").unlink()
    return dst


class Migration(Base):
    def setUp(self):
        super().setUp()
        self.v1 = make_v1(Path(self.tmp) / "v1")
        self.p1 = program(self.v1)

    def seed_v1(self):
        st = Store(self.db)
        D.seed(st, self.p1, ARTICLES, [[aid("a1"), article_v1("a1", "ann", "4")], [aid("a2"), article_v1("a2", "bob")]])
        return st

    def test_apply_migrates_rows_and_bumps_epoch(self):
        st = self.seed_v1()
        self.assertEqual(D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(1))["code"],
                         "SCHEMA_BINDING_MISMATCH")
        p = M.plan(st, PROGRAM)
        self.assertEqual([t["action"] for t in p["tables"] if t["table"] == ARTICLES], ["migrate"])
        r = M.apply(st, PROGRAM)
        self.assertEqual((r["outcome"], r["epoch"], r["rows"]), ("APPLIED", 1, 2))
        rows = D.dump(st, PROGRAM)["tables"][ARTICLES]
        self.assertEqual(rows[0][1], article("a1", "ann", rev="4"))
        self.assertEqual(M.apply(st, PROGRAM)["outcome"], "UP_TO_DATE")
        self.assertEqual(M.plan(st, self.p1)["code"], "MIGRATION_PLAN_INVALID")   # обратной миграции нет

    def test_receipt_survives_migration(self):
        """Ключи не истекают (CANON-10): квитанция, записанная до миграции, возвращается и после неё."""
        st = self.seed_v1()
        M.apply(st, PROGRAM)
        D.seed(st, PROGRAM, PEOPLE, [[pid("bob"), {"type": "blog.people.Person", "fields": {"id": pid("bob"), "display_name": s("B")}}]])
        D.seed(st, PROGRAM, ACL, [[actor("ed"), {"type": "blog.acl.Roles", "fields": {"editor": {"type": "Bool", "value": True}}}]])
        r1 = D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(1))
        D.deliver(st, PROGRAM)
        v3 = Path(self.tmp) / "v3"
        shutil.copytree(APP, v3)
        db = v3 / "blog" / "db.bag"
        db.write_text(db.read_text(encoding="utf-8").replace(
            "  @id(\"e2mrc6\")", "  @id(\"q3zz8m\") table notes: Map<ArticleId, String>\n  @id(\"e2mrc6\")"), encoding="utf-8")
        p3 = program(v3)
        self.assertEqual(M.apply(st, p3)["epoch"], 2)
        r2 = D.run_command(st, p3, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(1))
        self.assertEqual((r2["replayed"], r2["value"], r2["state_version"]), (True, r1["value"], r1["state_version"]))

    def test_lock_and_backlog(self):
        st = self.seed_v1()
        M.apply(st, PROGRAM)
        D.seed(st, PROGRAM, PEOPLE, [[pid("bob"), {"type": "blog.people.Person", "fields": {"id": pid("bob"), "display_name": s("B")}}]])
        D.seed(st, PROGRAM, ACL, [[actor("ed"), {"type": "blog.acl.Roles", "fields": {"editor": {"type": "Bool", "value": True}}}]])
        self.assertEqual(D.run_command(st, PROGRAM, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(1))["outcome"], "COMMITTED")
        v3 = Path(self.tmp) / "v3"
        shutil.copytree(APP, v3)
        db = v3 / "blog" / "db.bag"
        db.write_text(db.read_text(encoding="utf-8").replace(
            "  @id(\"e2mrc6\")", "  @id(\"q3zz8m\") table notes: Map<ArticleId, String>\n  @id(\"e2mrc6\")"), encoding="utf-8")
        p3 = program(v3)
        r = M.apply(st, p3)
        self.assertEqual(r["code"], "MIGRATION_BACKLOG")
        self.assertEqual(st.meta("writer_lock"), "")
        D.deliver(st, PROGRAM)
        r = M.apply(st, p3)
        self.assertEqual((r["outcome"], [t["action"] for t in r["tables"] if t["table"].endswith("notes")]), ("APPLIED", ["create"]))
        st.set_meta("writer_lock", "someone")
        self.assertEqual(D.run_command(st, p3, ENTRY, [actor("ed"), aid("a1"), ids("bob")], key(2))["code"],
                         "MIGRATION_IN_PROGRESS")

    def test_failed_row_leaves_data(self):
        st = self.seed_v1()
        mig = self.v1.parent / "v2bad"
        shutil.copytree(APP, mig)
        f = mig / "blog" / "migration.bag"
        f.write_text(f.read_text(encoding="utf-8").replace(
            "{\n  Ok(Article", "{\n  if old.revision == 4 {\n    return Err(MigrationError.Unreachable)\n  }\n  Ok(Article"),
            encoding="utf-8")
        p = program(mig)
        before = D.dump(st, self.p1)
        r = M.apply(st, p)
        self.assertEqual((r["code"], r["data"]["table"]), ("MIGRATION_FAILED", ARTICLES))
        self.assertEqual(D.dump(st, self.p1), before)
        self.assertEqual(st.meta("writer_lock"), "")


COUNTER = ROOT / "conformance" / "cases" / "migrate" / "apply-epoch-01"


def counter(version: str = "") -> D.Program:
    """Программа-счётчик сценариев хоста: v1 (Int64) в корне случая, v2 (Tally и миграция) в v2/."""
    root = COUNTER / version if version else COUNTER
    files = [(f.relative_to(root).as_posix(), f.read_bytes()) for f in sorted(root.glob("*.bag"))]
    project, prog, pre = prepare(files)
    assert pre is None, pre
    return D.Program(project, prog)


class ReviewM4(Base):
    """Регрессии ревью m4 (registry/reviews/m4.md)."""

    def setUp(self):
        super().setUp()
        self.v1, self.v2 = counter(), counter("v2")

    def bump(self, st, n, program=None):
        return D.run_command(st, program or self.v1, "app.bump", [s("a"), {"type": "Int64", "value": "1"}],
                             {"namespace": "app", "key": f"key-{n:012d}"})

    def test_h1_binding_rechecked_inside_transaction(self):
        st = Store(self.db)
        D.seed(st, self.v1, "app.S.counts", [[s("a"), {"type": "Int64", "value": "5"}]])
        orig = D.crash_point

        def migrate_meanwhile(name):                     # миграция успевает между проверкой и BEGIN
            if name == "before_begin":
                other = Store(self.db)
                self.assertEqual(M.apply(other, self.v2)["outcome"], "APPLIED")
                other.close()
        D.crash_point = migrate_meanwhile
        try:
            r = self.bump(st, 1)
        finally:
            D.crash_point = orig
        self.assertEqual(r["code"], "SCHEMA_BINDING_MISMATCH")
        self.assertEqual(len(D.dump(st, self.v2)["tables"]["app.S.counts"]), 1)

    def test_h2_concurrent_apply_of_same_plan(self):
        st = Store(self.db)
        D.seed(st, self.v1, "app.S.counts", [[s("a"), {"type": "Int64", "value": "5"}], [s("b"), {"type": "Int64", "value": "7"}]])
        orig, inner = M.crash_point, {}

        def second_apply(name):                          # второй процесс того же плана проходит целиком
            if name == "migration_prepare" and not inner:
                inner["started"] = True
                other = Store(self.db)
                inner["r"] = M.apply(other, self.v2)
                other.close()
        M.crash_point = second_apply
        try:
            r = M.apply(st, self.v2)
        finally:
            M.crash_point = orig
        self.assertEqual((inner["r"]["outcome"], r["code"]), ("APPLIED", "STALE_STATE"))
        self.assertEqual(len(D.dump(st, self.v2)["tables"]["app.S.counts"]), 2)
        self.assertEqual(st.meta("writer_lock"), "")

    def test_h3_replay_checks_write_arguments(self):
        st = Store(self.db)
        self.bump(st, 1)
        five = COUNTER.parent.parent / "store" / "replay-divergence-01" / "v5"
        files = [(f.relative_to(five).as_posix(), f.read_bytes()) for f in five.glob("*.bag")]
        project, prog, _ = prepare(files)
        self.assertEqual(D.replay(st, D.Program(project, prog), "app:key-000000000001")["outcome"], "REPLAY_DIVERGENCE")

    def test_m4_m5_strict_request(self):
        st = Store(self.db)
        bad_key = D.run_command(st, self.v1, "app.bump", [s("a"), {"type": "Int64", "value": "1"}],
                                {"namespace": "app", "key": "key-000000000001\n"})
        surrogate = D.run_command(st, self.v1, "app.bump", [s("a\ud800"), {"type": "Int64", "value": "1"}],
                                  {"namespace": "app", "key": "key-000000000001"})
        extra = D.run_command(st, self.v1, "app.bump", [dict(s("a"), x="1"), {"type": "Int64", "value": "1"}],
                              {"namespace": "app", "key": "key-000000000001"})
        self.assertEqual([r["code"] for r in (bad_key, surrogate, extra)], ["REQUEST_INVALID"] * 3)
        self.assertEqual(D.status(st, {"namespace": "app", "key": "key-000000000001"})["outcome"], "ABSENT_AT_READ")

    def test_m6_seed_respects_lock_and_l2_replay_of_seed(self):
        st = Store(self.db)
        D.seed(st, self.v1, "app.S.counts", [[s("a"), {"type": "Int64", "value": "5"}]])
        self.assertEqual(D.replay(st, self.v1, "seed:app.S.counts")["code"], "REQUEST_INVALID")
        st.set_meta("writer_lock", "other")
        self.assertEqual(D.seed(st, self.v1, "app.S.counts", [])["code"], "MIGRATION_IN_PROGRESS")

    def test_state_version_exhausted(self):
        st = Store(self.db)
        self.bump(st, 1)
        st.set_meta("state_version", D.MAX_VERSION)
        self.assertEqual(self.bump(st, 2)["code"], "STATE_VERSION_EXHAUSTED")
        self.assertEqual(D.status(st, {"namespace": "app", "key": "key-000000000002"})["outcome"], "ABSENT_AT_READ")


def bag(*args, env=None):
    e = dict(os.environ, PYTHONPATH=str(ROOT / "ref"))
    e.pop("BAG_CRASH_AT", None)
    e.update(env or {})
    p = subprocess.run([sys.executable, "-m", "bagaev_ref", *args, "--json"], capture_output=True, text=True, env=e)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip() else None)


class Crash(Base):
    """kill -9 в точках сбоя (HST-12): процесс завершается без отката и без ответа; восстановление — по квитанции."""

    def cmd(self, n, crash=None):
        args = json.dumps([actor("ed"), aid("a1"), ids("bob", "cid")])
        return bag("run", str(APP), ENTRY, "--db", self.db, "--args", args, "--namespace", "editor",
                   "--key", key(n)["key"], env={"BAG_CRASH_AT": crash} if crash else None)

    def test_command_crash_points(self):
        for point, committed in (("before_begin", False), ("before_commit", False), ("after_commit", True)):
            with self.subTest(point=point):
                if os.path.exists(self.db):
                    for suffix in ("", "-wal", "-shm"):
                        if os.path.exists(self.db + suffix):
                            os.remove(self.db + suffix)
                seeded(self.db).close()
                rc, out = self.cmd(1, point)
                self.assertEqual((rc, out), (137, None))
                st = Store(self.db)
                self.assertEqual(D.status(st, key(1))["outcome"], "RESULT" if committed else "ABSENT_AT_READ")
                self.assertEqual(len(D.dump(st, PROGRAM)["outbox"]), 1 if committed else 0)
                st.close()
                rc, out = self.cmd(1)
                self.assertEqual((rc, out["outcome"], out["replayed"]), (0, "COMMITTED", committed))
                st = Store(self.db)
                self.assertEqual(len(D.dump(st, PROGRAM)["outbox"]), 1)      # ровно один эффект
                st.close()

    def test_concurrent_same_key_executes_once(self):
        """Одновременные процессы с одним ключом: BEGIN IMMEDIATE сериализует, исполнение ровно одно (HST-01, HST-05)."""
        seeded(self.db).close()
        args = json.dumps([actor("ed"), aid("a1"), ids("bob", "cid")])
        e = dict(os.environ, PYTHONPATH=str(ROOT / "ref"))
        e.pop("BAG_CRASH_AT", None)
        procs = [subprocess.Popen([sys.executable, "-m", "bagaev_ref", "run", str(APP), ENTRY, "--db", self.db, "--args", args,
                                   "--namespace", "editor", "--key", key(1)["key"], "--json"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=e) for _ in range(8)]
        outs = [json.loads(p.communicate(timeout=120)[0]) for p in procs]
        self.assertEqual(sorted(o["replayed"] for o in outs), [False] + [True] * 7)
        self.assertEqual({o["state_version"] for o in outs}, {outs[0]["state_version"]})
        st = Store(self.db)
        self.assertEqual(len(D.dump(st, PROGRAM)["outbox"]), 1)
        st.close()
        procs = [subprocess.Popen([sys.executable, "-m", "bagaev_ref", "run", str(APP), ENTRY, "--db", self.db, "--args", args,
                                   "--namespace", "editor", "--key", key(10 + n)["key"], "--json"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=e) for n in range(6)]
        outs = [json.loads(p.communicate(timeout=120)[0]) for p in procs]
        self.assertEqual(sorted(o["state_version"] for o in outs), list(range(5, 11)))   # разные ключи: шесть фиксаций подряд

    def test_handler_crash_points(self):
        for point, committed in (("before_begin", False), ("before_commit", False), ("after_commit", True)):
            with self.subTest(point=point):
                for suffix in ("", "-wal", "-shm"):
                    if os.path.exists(self.db + suffix):
                        os.remove(self.db + suffix)
                seeded(self.db).close()
                self.cmd(1)
                rc, _ = bag("events", "deliver", str(APP), "--db", self.db, env={"BAG_CRASH_AT": point})
                self.assertEqual(rc, 137)
                st = Store(self.db)
                self.assertEqual(D.event_status(st, "blog.indexer.index_authorship", 1)["outcome"],
                                 "RESULT" if committed else "ABSENT_AT_READ")
                self.assertEqual(D.dump(st, PROGRAM)["pending"], [] if committed else
                                 [{"handler": "blog.indexer.index_authorship", "seq": 1}])
                st.close()
                rc, out = bag("events", "deliver", str(APP), "--db", self.db)
                self.assertEqual([(d["seq"], d["outcome"]) for d in out["deliveries"]], [] if committed else [(1, "COMMITTED")])
                rc, out = bag("events", "deliver", str(APP), "--db", self.db)
                self.assertEqual(out["deliveries"], [])
                st = Store(self.db)
                self.assertEqual(len(D.dump(st, PROGRAM)["inbox"]), 1)          # обработка ровно одна
                st.close()

    def test_migration_crash_points(self):
        p1 = program(make_v1(Path(self.tmp) / "v1"))
        for point, epoch in (("migration_prepare", "0"), ("before_swap_commit", "0"), ("after_swap", "1")):
            with self.subTest(point=point):
                for suffix in ("", "-wal", "-shm"):
                    if os.path.exists(self.db + suffix):
                        os.remove(self.db + suffix)
                st = Store(self.db)
                D.seed(st, p1, ARTICLES, [[aid("a1"), article_v1("a1", "ann")]])
                st.close()
                rc, _ = bag("migrate", "apply", str(APP), "--db", self.db, env={"BAG_CRASH_AT": point})
                self.assertEqual(rc, 137)
                st = Store(self.db)
                self.assertEqual(st.meta("epoch"), epoch)
                if epoch == "0":
                    self.assertNotEqual(st.meta("writer_lock"), "")        # писатели остановлены до завершения
                    self.assertEqual(self.cmd(9)[1]["code"], "MIGRATION_IN_PROGRESS")
                st.close()
                rc, out = bag("migrate", "apply", str(APP), "--db", self.db)
                self.assertEqual(out["outcome"], "UP_TO_DATE" if epoch == "1" else "APPLIED")
                st = Store(self.db)
                self.assertEqual((st.meta("epoch"), st.meta("writer_lock")), ("1", ""))
                self.assertEqual(D.dump(st, PROGRAM)["tables"][ARTICLES][0][1], article("a1", "ann"))
                st.close()


if __name__ == "__main__":
    unittest.main()
