#!/usr/bin/env python3
"""Оракул опыта авторства: чёрный ящик по общему CLI-контракту (pilot/authorship/contract.md).

  python3 pilot/authorship/oracle/run.py --arm C [--candidate DIR] [--baseline DIR] [--json]

Ожидания — из registry/data/core/authorship-fixtures.json и дополнений пилота (contract.md §5: почта, RSS,
уведомления). Данные засеваются базовой версией приложения (S0), затем кандидат выполняет миграцию и сценарии.
Оракул не читает исходников и не зависит от языка варианта. Каждая проверка привязана к обязательствам O01–O10
и случаям C01–C13 (05-authorship-experiment.md). Ничего не пишет в рабочее дерево: состояние — во временном каталоге.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PILOT = ROOT / "pilot" / "authorship"
FIX = json.loads((ROOT / "registry/data/core/authorship-fixtures.json").read_text(encoding="utf-8"))
SEED = PILOT / "data" / "seed.json"
EMAIL = {p["person_id"]: p["email"] for p in json.loads(SEED.read_text(encoding="utf-8"))["people"]}


def decode_cli_response(returncode: int, stdout: str, stderr: str = "") -> dict:
    """Общий контракт прямого CLI и изолированного posthoc; правильные поля не скрывают ошибку ответа."""
    if returncode != 0:
        return {"status": "crash", "code": "CLI_EXIT", "rc": returncode, "stderr": stderr[-400:]}
    try:
        lines = stdout.strip().splitlines()
        result = json.loads(lines[0]) if len(lines) == 1 else None
    except ValueError:
        result = None
    if isinstance(result, dict) and result.get("status") in ("ok", "rejected"):
        return result
    return {"status": "crash", "code": "CLI_RESPONSE", "stdout": stdout[-400:]}


class Arm:
    def __init__(self, spec: dict, app: Path, state: Path, tmp: Path):
        self.spec, self.app, self.state, self.tmp, self.n = spec, app, state, tmp, 0
        self.failures = []

    def run(self, command: str, app: Path | None = None, **opts) -> dict:
        argv = [x.replace("{app}", str(app or self.app)).replace("{state}", str(self.state)) for x in self.spec["cli"]]
        argv.append(command)
        for k, v in opts.items():
            if isinstance(v, (dict, list)):
                self.n += 1
                f = self.tmp / f"in-{self.n}.json"
                f.write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
                v = str(f)
            argv += ["--" + k.replace("_", "-"), str(v)]
        try:
            p = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT, timeout=600)
            failure = decode_cli_response(p.returncode, p.stdout, p.stderr)
            if failure["status"] != "crash":
                return failure
        except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
            failure = {"status": "crash", "code": "CLI_FAILURE", "reason": type(exc).__name__}
        self.failures.append(dict(failure, command=command))
        return failure


def norm_state(st: dict) -> dict:
    """Сравниваемая часть состояния: статьи как есть, индекс — множества (порядок поиска задаёт search)."""
    return {"articles": st.get("articles"),
            "author_index": {k: sorted(v) for k, v in (st.get("author_index") or {}).items()},
            "outbox_pending_event_ids": st.get("outbox_pending_event_ids"),
            "inbox_completed_event_ids": st.get("inbox_completed_event_ids")}


def expected_state(label: str) -> dict:
    src = {"D1": FIX["expected_state_after_migration"], "D2": FIX["expected_state_after_write_before_delivery"],
           "D3": FIX["expected_state_after_event_delivery"]}[label]
    arts = [{"article_id": a["article_id"], "article_revision": a["article_revision"], "title": a["title"],
             "author_ids": a["author_ids"], "editor_ids": a["editor_ids"]} for a in src["articles"]]
    return {"articles": arts, "author_index": {k: sorted(v) for k, v in src["author_index"].items()},
            "outbox_pending_event_ids": src.get("outbox_pending_event_ids", []),
            "inbox_completed_event_ids": src["inbox_completed_event_ids"]}


class Report:
    def __init__(self):
        self.checks = []

    def check(self, cid: str, obligations: list, cases: list, ok: bool, detail=None):
        self.checks.append({"id": cid, "obligations": obligations, "cases": cases, "outcome": "PASS" if ok else "FAIL",
                            **({"detail": detail} if not ok and detail is not None else {})})
        return ok


def fresh(arm: Arm, baseline: Path, rep: Report, tag: str) -> bool:
    """Засев D0 базовой версией и миграция кандидатом → D1 (O02)."""
    if arm.state.exists():
        shutil.rmtree(arm.state)
    seed = arm.run("seed", app=baseline, data=json.loads(SEED.read_text(encoding="utf-8")))
    if seed.get("status") != "ok":
        return rep.check(f"{tag}-seed", [], [], False, seed)
    mig = arm.run("migrate")
    st = arm.run("state")
    return rep.check(f"{tag}-migration-d1", ["O02"], ["C01"], mig.get("status") == "ok" and norm_state(st) == expected_state("D1"),
                     {"migrate": mig, "state": norm_state(st), "expected": expected_state("D1")})


def flow_c01(arm: Arm, baseline: Path, rep: Report):
    if not fresh(arm, baseline, rep, "c01"):
        return
    cmd = FIX["command_set_authors"]
    r = arm.run("set-authors", command_file=cmd)
    rep.check("set-authors-accepted", ["O01"], ["C01"], r.get("status") == "ok" and r.get("article_revision") == 2, r)
    st = arm.run("state")
    rep.check("state-d2-before-delivery", ["O04", "O07"], ["C01", "C09"], norm_state(st) == expected_state("D2"),
              {"state": norm_state(st), "expected": expected_state("D2")})
    again = arm.run("set-authors", command_file=cmd)
    st2 = arm.run("state")
    rep.check("command-retry-idempotent", ["O07"], ["C01"],
              again.get("status") == "ok" and again.get("replayed") is True and norm_state(st2) == expected_state("D2"),
              {"retry": again, "state": norm_state(st2)})
    d = arm.run("deliver-events")
    st = arm.run("state")
    rep.check("state-d3-after-delivery", ["O04", "O07"], ["C01"],
              d.get("status") == "ok" and norm_state(st) == expected_state("D3"),
              {"deliver": d, "state": norm_state(st), "expected": expected_state("D3")})
    obs = FIX["expected_observations"]
    for a, want in obs["bylines"].items():
        got = arm.run("byline", article=a)
        rep.check(f"byline-{a}", ["O03"], ["C01"], got.get("byline") == want, {"got": got, "want": want})
    for p, want in obs["search_by_person_id"].items():
        got = arm.run("search", person=p)
        rep.check(f"search-{p}", ["O04"], ["C01", "C09"], got.get("article_ids") == want, {"got": got, "want": want})
    for p, want in obs["profile_article_ids_by_person_id"].items():
        got = arm.run("profile", person=p)
        rep.check(f"profile-{p}", ["O03"], ["C01"], got.get("article_ids") == want, {"got": got, "want": want})
    for a, want in obs["decoded_export_json"].items():
        got = arm.run("export", article=a)
        try:
            dec = json.loads(got.get("export", ""))
        except ValueError:
            dec = None
        rep.check(f"export-{a}", ["O05"], ["C01", "C04", "C05"], dec == want, {"got": dec, "want": want})
    # скрытые потребители (contract.md §5): задание о них не упоминает
    feed = arm.run("rss").get("feed", "")
    want_items = {"a_101": "Борис Соколов · Алина Петрова", "a_102": "Борис Соколов"}
    rep.check("hidden-rss-authors", ["O03"], ["C01"],
              all(f"<guid>{a}</guid>" in feed and f"<author>{n}</author>" in feed.split(f"<guid>{a}</guid>", 1)[1].split("</item>", 1)[0]
                  for a, n in want_items.items()), {"feed": feed, "want": want_items})
    notes = arm.run("notifications").get("notifications")
    ev = FIX["expected_emitted_event"]
    want_to = sorted(EMAIL[p] for p in ev["author_ids"])
    got_to = sorted(n["to"] for n in (notes or []) if n.get("key", "").startswith(ev["event_id"] + ":"))
    rep.check("hidden-notify-all-authors", ["O03"], ["C01"], got_to == want_to, {"got": notes, "want_to": want_to})
    # C13: повторная доставка того же события — одна запись inbox и один набор записей индекса
    rd = arm.run("redeliver", event=ev["event_id"])
    st = arm.run("state")
    rep.check("redelivery-deduplicated", ["O07"], ["C13"],
              rd.get("status") == "ok" and rd.get("reexecuted") is False and norm_state(st) == expected_state("D3")
              and arm.run("search", person="p_boris").get("article_ids") == ["a_101", "a_102"],
              {"redeliver": rd, "state": norm_state(st)})
    # C03: авторство не даёт права правки
    deny = {"command_id": "cmd_boris_a101", "idempotency_key": "cmd_boris_a101_try1", "actor_id": "u_boris",
            "article_id": "a_101", "expected_article_revision": 2, "author_ids": ["p_boris"]}
    r = arm.run("set-authors", command_file=deny)
    st = arm.run("state")
    rep.check("coauthor-not-editor", ["O06"], ["C03"],
              r.get("status") == "rejected" and r.get("code") == "PERMISSION_DENIED" and norm_state(st) == expected_state("D3"),
              {"result": r, "state": norm_state(st)})


def flow_c02(arm: Arm, baseline: Path, rep: Report):
    if not fresh(arm, baseline, rep, "c02"):
        return
    for n, req in enumerate(FIX["invalid_author_requests"]):
        cmd = dict(FIX["command_set_authors"], author_ids=req["author_ids"], command_id=f"cmd_invalid_{n}",
                   idempotency_key=f"cmd_invalid_request_{n}")
        r = arm.run("set-authors", command_file=cmd)
        st = arm.run("state")
        code = {"EMPTY_AUTHORS": "EMPTY_AUTHORS", "DUPLICATE_AUTHOR": "DUPLICATE_AUTHOR", "UNKNOWN_PERSON": "UNKNOWN_PERSON"}[
            req["diagnostic_example"]]
        rep.check(f"invalid-{code.lower()}", ["O01"], ["C02"],
                  r.get("status") == "rejected" and r.get("code") == code and norm_state(st) == expected_state("D1"),
                  {"result": r, "state": norm_state(st)})


def flow_remove_author(arm: Arm, baseline: Path, rep: Report):
    """O04: A → [B] должен удалить статью из индекса A, а не только добавить B.

    Ожидание выведено из O03/O04 и D1 до исполнения: один редактор, прежняя статья,
    ревизия 2, один новый автор; проекция и профиль прежнего автора пусты.
    """
    if not fresh(arm, baseline, rep, "remove-author"):
        return
    cmd = dict(FIX["command_set_authors"], author_ids=["p_boris"])
    result = arm.run("set-authors", command_file=cmd)
    rep.check("replacement-accepted", ["O01"], ["C09"],
              result.get("status") == "ok" and result.get("article_revision") == 2, result)
    delivered = arm.run("deliver-events")
    expected = copy.deepcopy(expected_state("D3"))
    next(a for a in expected["articles"] if a["article_id"] == "a_101")["author_ids"] = ["p_boris"]
    expected["author_index"]["p_alina"] = []
    state = arm.run("state")
    rep.check("replacement-state", ["O04", "O07"], ["C09"],
              delivered.get("status") == "ok" and norm_state(state) == expected,
              {"state": norm_state(state), "expected": expected})
    found = arm.run("search", person="p_alina")
    rep.check("author-removed-from-index", ["O04"], ["C09"], found.get("article_ids") == [], found)
    profile = arm.run("profile", person="p_alina")
    rep.check("author-removed-from-profile", ["O03"], ["C09"], profile.get("article_ids") == [], profile)


def check_image(arm: Arm, rep: Report):
    fx = FIX["pure_image_fixture"]
    r = arm.run("resize", input={"input": fx["input"], "requested_output_size": fx["requested_output_size"]})
    rep.check("image-resize-pure", ["O08"], ["C08"], r.get("output") == fx["expected_output"], r)


def run(arm_name: str, candidate: Path | None = None, baseline: Path | None = None) -> dict:
    spec = json.loads((PILOT / "arms.json").read_text(encoding="utf-8"))["arms"][arm_name]
    candidate = Path(candidate or ROOT / spec["reference"]).resolve()
    baseline = Path(baseline or ROOT / spec["baseline"]).resolve()
    rep = Report()
    with tempfile.TemporaryDirectory(prefix="bag-oracle-") as tmp:
        arm = Arm(spec, candidate, Path(tmp) / "state", Path(tmp))
        flow_c01(arm, baseline, rep)
        flow_c02(arm, baseline, rep)
        flow_remove_author(arm, baseline, rep)
        check_image(arm, rep)
        rep.check("cli-contract", [], [], not arm.failures, arm.failures)
    failed = [c for c in rep.checks if c["outcome"] == "FAIL"]
    return {"arm": arm_name, "candidate": str(candidate.relative_to(ROOT)) if candidate.is_relative_to(ROOT) else str(candidate),
            "outcome": "PASS" if not failed else "FAIL", "passed": len(rep.checks) - len(failed), "total": len(rep.checks),
            "failed": [c["id"] for c in failed], "checks": rep.checks}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--arm", required=True)
    ap.add_argument("--candidate")
    ap.add_argument("--baseline")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    out = run(a.arm, a.candidate and Path(a.candidate), a.baseline and Path(a.baseline))
    if a.json:
        print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    else:
        for c in out["checks"]:
            print(f"[{c['outcome']}] {c['id']} ({', '.join(c['obligations'] + c['cases'])})")
        print(f"{out['arm']} {out['candidate']}: {out['passed']}/{out['total']} — {out['outcome']}")
    return 0 if out["outcome"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
