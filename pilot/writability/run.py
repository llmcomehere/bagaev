#!/usr/bin/env python3
"""Харнесс пробника пишемости (protocol.md).

  python3 pilot/writability/run.py --validate     эталонные решения проходят проверку своего плеча
  python3 pilot/writability/run.py --dry-run DIR  собрать все промпты в DIR и оценить объём токенов

  python3 pilot/writability/run.py --run ID [--limit N]   прогон выбранной модели через CLI
  python3 pilot/writability/run.py --score ID             метрики protocol.md §4
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TASKS = HERE / "tasks"
sys.path.insert(0, str(ROOT / "ref"))

from bagaev_ref.syntax import ast as A  # noqa: E402
from bagaev_ref.syntax.parser import parse  # noqa: E402
from bagaev_ref.syntax.printer import ID_ATTR, FormatError, assign_ids, id_sites  # noqa: E402

FILE_BLOCK = re.compile(r"```[a-zA-Z]*[ \t]+path=([^\s`]+)[ \t]*\n(.*?)```", re.S)
MAX_ROUNDS = 2                     # раунды диагностик после первой попытки (protocol.md §3)
SHOWN_DIAGNOSTICS = 5


def load_task(tid: str) -> dict:
    d = TASKS / tid
    meta = json.loads((d / "task.json").read_text(encoding="utf-8"))
    meta["dir"] = d
    meta["statement_md"] = (d / "task.md").read_text(encoding="utf-8")
    return meta


def tree_files(base: Path) -> dict[str, bytes]:
    if not base.exists():
        return {}
    return {f.relative_to(base).as_posix(): f.read_bytes() for f in sorted(base.rglob("*")) if f.is_file()}


# ------------------------------------------------------------ плечо C: bagaev
def id_map(data: bytes, renamed: dict | None = None) -> dict:
    """Место SURF-07 → значение @id. Ключ — (декларация, член); renamed переименовывает члены (старое → новое)."""
    tree, _, diags = parse(data)
    if tree is None or diags:
        return {}
    renamed = renamed or {}
    out = {}
    for node, _ in id_sites(tree):
        ids = [a.args[0][1] for a in node.attrs if a.name.text == "id" and a.args and a.args[0][0] == "STRING"]
        if not ids:
            continue
        out[site_key(tree, node, renamed)] = ids[0]
    return out


def site_key(tree, node, renamed: dict) -> tuple:
    if isinstance(node, A.ModuleHeader):
        return ("module",)
    if isinstance(node, A.Item):
        return (node.decl.name.text,)
    owner = next(it.decl.name.text for it in tree.items if it.start <= node.start < it.end)
    return (owner, renamed.get(node.name.text, node.name.text))


def evaluate_c(task: dict, solution: dict[str, bytes]) -> dict:
    """Собрать проект: контекст + ответ + скрытая проверка; --assign-ids для файлов ответа; bag check."""
    d = task["dir"] / "c"
    context, probe = tree_files(d / "context"), tree_files(d / "probe")
    files = dict(context)
    taken = set()
    for data in list(context.values()) + list(probe.values()):
        taken |= set(ID_ATTR.findall(data.decode("utf-8", errors="replace")))
    written_ids = set()
    report = {"arm": "C", "task": task["id"]}
    for name, data in solution.items():
        written_ids |= set(ID_ATTR.findall(data.decode("utf-8", errors="replace")))
        try:
            files[name] = assign_ids(data, name, taken)
        except FormatError:
            files[name] = data                       # синтаксическая ошибка — её покажет bag check
    files.update(probe)
    report["checked_files"] = {n: files[n] for n in solution}   # строки диагностик — по этим байтам
    from bagaev_ref.cli import check_observation
    obs = check_observation(sorted(files.items()))
    report["passed_check"] = obs["outcome"] == "ACCEPTED"
    report["diagnostics"] = obs.get("diagnostics", [])
    expect = task.get("c_expect", {})
    report["interface_ok"] = report["passed_check"] and interface_ok(task, expect, files)
    ctx_ids = set().union(*[set(ID_ATTR.findall(v.decode())) for v in context.values()]) if context else set()
    report["fabricated_ids"] = sorted(written_ids - ctx_ids)
    keep = expect.get("keep_ids_from_context")
    if keep:
        renamed = expect.get("renamed", {})
        before = id_map(context[keep], renamed)
        after = id_map(files.get(keep, b""))
        lost = sorted(".".join(k) for k, v in before.items() if after.get(k) != v)
        report["ids_preserved"] = not lost
        report["ids_lost"] = lost
    report["passed"] = report["interface_ok"] and report.get("ids_preserved", True)
    return report


def interface_ok(task: dict, expect: dict, files: dict[str, bytes]) -> bool:
    """Скрытая проверка того, что не выражает probe-модуль: точки входа по разрешённым типам и фактическим
    эффектам тела (а не по тексту сигнатуры), связи implements/checks."""
    from bagaev_ref.sema.check import check_project_full
    from bagaev_ref.sema.project import FnInfo
    from bagaev_ref.sema.types import show, show_atom
    project, _ = check_project_full(sorted(files.items()))
    module = project.modules.get(task["c_target"][:-4].replace("/", "."))
    if module is None:
        return False
    for name, want in expect.get("decls", {}).items():
        info = module.values.get(name)
        if not isinstance(info, FnInfo) or info.kind != want["kind"]:
            return False
        if [show(t) for t in info.params] != want["params"] or show(info.ret) != want["ret"]:
            return False
        if not set(want.get("actual", [])) <= {show_atom(a) for a in info.actual}:
            return False
    tree, _, _ = parse(files.get(task["c_target"], b""))
    decls = {it.decl.name.text: it.decl for it in tree.items} if tree else {}
    for name, links in expect.get("links", {}).items():
        d = decls.get(name)
        if d is None:
            return False
        have: dict = {}
        for lk in getattr(d, "links", []):                     # повторные предложения одного вида складываются
            have.setdefault(lk.kind, set()).update(".".join(n.text for n in t) for t in lk.targets)
        if any(not set(v) <= have.get(k, set()) for k, v in links.items()):
            return False
    return True


def feedback_c(report: dict) -> str:
    """Сообщение для раунда исправлений: место — по проверенному файлу, с текстом строки."""
    lines = []
    for dg in report["diagnostics"][:SHOWN_DIAGNOSTICS]:
        src = report["checked_files"].get(dg["file"])
        if src is None:
            lines.append(f"{dg['file']}: {dg['code']} {json.dumps(dg.get('data', {}), ensure_ascii=False)}")
            continue
        start = dg["span"][0]
        line_no = src[:start].count(b"\n") + 1
        text = src.split(b"\n")[line_no - 1].decode("utf-8", errors="replace").strip()
        lines.append(f"{dg['file']}:{line_no}: {dg['code']} {json.dumps(dg.get('data', {}), ensure_ascii=False)}"
                     f" — строка: {text}")
    if report["passed_check"] and not report["interface_ok"]:
        lines.append("Проверка прошла, но интерфейс или поведение эффектов не совпадают с требуемыми в условии.")
    if report.get("ids_lost"):
        lines.append("Потеряны или изменены @id: " + ", ".join(report["ids_lost"]))
    return "\n".join(lines)


# ------------------------------------------------------------ плечо T: TypeScript
def tsc() -> str | None:
    """Закреплённый компилятор пробника (package.json рядом), иначе tsc из PATH."""
    local = HERE / "node_modules" / ".bin" / "tsc"
    return str(local) if local.exists() else shutil.which("tsc")


def evaluate_t(task: dict, solution: dict[str, bytes]) -> dict:
    d = task["dir"] / "t"
    report = {"arm": "T", "task": task["id"]}
    if tsc() is None:
        report.update(passed=None, status="NOT_RUN", detail="tsc не установлен; выполните npm ci в pilot/writability")
        return report
    with tempfile.TemporaryDirectory(prefix="bagaev-w-") as tmp:
        root = Path(tmp)
        files = dict(tree_files(d / "context"))
        files.update(solution)
        files.update(tree_files(d / "probe"))
        for name, data in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_bytes(data)
        names = [n for n in files if n.endswith(".ts")]
        cmd = [tsc(), "--strict", "--noEmit", "--target", "es2022", "--module", "es2022", "--moduleResolution", "bundler",
               "--noUncheckedIndexedAccess", *names]
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=120)
        report["passed_check"] = r.returncode == 0
        report["diagnostics"] = [ln for ln in r.stdout.splitlines() if ": error TS" in ln]
        report["passed"] = report["passed_check"]
    return report


# ------------------------------------------------------------ промпты
def system_prompt(arm: str) -> str:
    if arm == "C":
        guide = (ROOT / "spec" / "language" / "guide-llm.md").read_text(encoding="utf-8")
        return ("Ты пишешь код на языке bagaev. Ниже — его полное описание; других источников нет.\n"
                "Верни полный текст каждого файла, который создаёшь или меняешь, блоком ```bagaev path=<путь>.\n"
                "Не придумывай значения @id: у новых деклараций опусти @id, их вставит инструмент; "
                "существующие @id сохрани без изменений.\n\n" + guide)
    return ("Ты пишешь код на TypeScript 5 в режиме strict (noUncheckedIndexedAccess). "
            "Верни полный текст каждого файла, который создаёшь или меняешь, блоком ```ts path=<путь>.")


def task_prompt(task: dict, arm: str) -> str:
    sub = "c" if arm == "C" else "t"
    md = task["statement_md"]
    head, _, rest = md.partition("\n## bagaev")
    section = ("## bagaev" + rest.split("\n## TypeScript")[0]) if arm == "C" else ("## TypeScript" + rest.split("\n## TypeScript")[1])
    parts = [head.strip(), section.strip()]
    ctx = tree_files(task["dir"] / sub / "context")
    if ctx:
        lang = "bagaev" if arm == "C" else "ts"
        parts.append("Файлы проекта:")
        parts += [f"```{lang} path={n}\n{v.decode('utf-8')}```" for n, v in ctx.items()]
    return "\n\n".join(parts)


def extract_files(text: str) -> dict[str, bytes]:
    return {m.group(1): m.group(2).encode("utf-8") for m in FILE_BLOCK.finditer(text)}


def estimate_tokens(s: str) -> int:
    """Измеритель плана: utf-8-bytes/4@1."""
    return (len(s.encode("utf-8")) + 3) // 4


# ------------------------------------------------------------ команды
def all_tasks() -> list[dict]:
    index = json.loads((TASKS / "index.json").read_text(encoding="utf-8"))
    return [load_task(t["id"]) for t in index]


def cmd_validate() -> int:
    bad = 0
    for t in all_tasks():
        rc = evaluate_c(t, tree_files(t["dir"] / "c" / "reference"))
        rt = evaluate_t(t, tree_files(t["dir"] / "t" / "reference"))
        empty = evaluate_c(t, {t["c_target"]: tree_files(t["dir"] / "c" / "context").get(t["c_target"], b"")})
        status_t = "NOT_RUN" if rt["passed"] is None else ("PASS" if rt["passed"] else "FAIL")
        ctx_t = tree_files(t["dir"] / "t" / "context")
        empty_t = evaluate_t(t, {t["t_target"]: ctx_t.get(t["t_target"], b"")})
        weak_t = empty_t["passed"] is True
        ok = rc["passed"] and not empty["passed"] and status_t != "FAIL" and not weak_t
        bad += not ok
        print(f"{t['id']}: C эталон {'PASS' if rc['passed'] else 'FAIL'}, C без решения "
              f"{'FAIL (верно)' if not empty['passed'] else 'PASS (проверка слишком слабая)'}, T эталон {status_t}, "
              f"T без решения {'PASS (проверка слишком слабая)' if weak_t else 'FAIL (верно)' if empty_t['passed'] is False else 'NOT_RUN'}")
        if not rc["passed"]:
            print("   ", rc["diagnostics"][:2], rc.get("ids_lost"))
    print("итог:", "OK" if bad == 0 else f"{bad} задач с замечаниями")
    return 1 if bad else 0


def cmd_dry_run(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    total = {"C": 0, "T": 0}
    for t in all_tasks():
        for arm in ("C", "T"):
            s, u = system_prompt(arm), task_prompt(t, arm)
            (out / f"{t['id']}-{arm}.txt").write_text(f"=== system\n{s}\n\n=== user\n{u}\n", encoding="utf-8")
            total[arm] += estimate_tokens(s) + estimate_tokens(u)
    print(json.dumps({"prompts": str(out), "first_attempt_input_tokens": total}, ensure_ascii=False))
    return 0


# ------------------------------------------------------------ прогон модели (protocol.md §3, §6)
MODEL = "claude-sonnet-5-5"
EFFORT = "medium"
BUDGET_USD = 25.0                  # условная стоимость по total_cost_usd; прогон идёт по подписке
SEED = 20261023
REPS = 3
WORKERS = 4
RESULTS = HERE / "results"


def claude_cli() -> str:
    """Claude Code CLI: из PATH или встроенный в настольное приложение."""
    found = shutil.which("claude")
    if found:
        return found
    cands = sorted(Path.home().glob(".config/Claude/claude-code/*/*/claude"))
    if not cands:
        raise SystemExit("Claude Code CLI не найден")
    return str(cands[-1])


def call_model(system: str, prompt: str, session: str | None, workdir: Path) -> dict:
    """Один ход диалога через `claude -p` под подпиской: без инструментов, со своим системным промптом.
    Рабочий каталог пуст — модель не видит ни репозиторий, ни CLAUDE.md, ни память."""
    cmd = [claude_cli(), "-p", "--model", MODEL, "--effort", EFFORT, "--tools", "", "--setting-sources", "",
           "--strict-mcp-config", "--exclude-dynamic-system-prompt-sections", "--system-prompt", system,
           "--output-format", "json"]
    if session:
        cmd += ["--resume", session]
    r = subprocess.run(cmd + [prompt], cwd=workdir, capture_output=True, text=True, timeout=900)
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"error": (r.stderr or r.stdout)[-500:], "cost": 0.0}
    if out.get("is_error"):
        return {"error": str(out.get("result"))[:500], "cost": float(out.get("total_cost_usd") or 0)}
    return {"text": out.get("result", ""), "session": out.get("session_id"), "usage": out.get("usage", {}),
            "cost": float(out.get("total_cost_usd") or 0), "model": list((out.get("modelUsage") or {}).keys())}


def feedback_t(report: dict) -> str:
    return "\n".join(report.get("diagnostics", [])[:SHOWN_DIAGNOSTICS]) or "Проверка не прошла."


def allowed_files(task: dict, arm: str) -> set:
    sub = "c" if arm == "C" else "t"
    return {task[f"{sub}_target"]} | set(tree_files(task["dir"] / sub / "context"))


def run_pair(task: dict, arm: str, rep: int, out_dir: Path, ledger) -> dict:
    """Одна пара «задача × плечо × повтор»: попытка и до MAX_ROUNDS раундов исправлений в одном диалоге."""
    workdir = Path(tempfile.mkdtemp(prefix="bagaev-w-run-"))
    system, prompt = system_prompt(arm), task_prompt(task, arm)
    session, attempts = None, []
    for k in range(1 + MAX_ROUNDS):
        if not ledger.reserve():
            return {"task": task["id"], "arm": arm, "rep": rep, "status": "BUDGET_STOP", "attempts": attempts}
        reply = call_model(system, prompt, session, workdir)
        ledger.spend(reply.get("cost", 0.0))
        rec = {"attempt": k + 1, "cost": reply.get("cost", 0.0), "usage": reply.get("usage", {}),
               "model": reply.get("model")}
        if "error" in reply:
            rec["error"] = reply["error"]
            attempts.append(rec)
            return {"task": task["id"], "arm": arm, "rep": rep, "status": "ERROR", "attempts": attempts}
        session = reply["session"]
        name = f"{task['id']}-{arm}-r{rep}-a{k + 1}"
        (out_dir / "answers").mkdir(exist_ok=True)
        (out_dir / "answers" / f"{name}.md").write_text(reply["text"], encoding="utf-8")
        files = {n: v for n, v in extract_files(reply["text"]).items() if n in allowed_files(task, arm)}
        if not files:
            rep_ = {"passed": False, "passed_check": False, "diagnostics": [], "no_files": True}
            fb = "В ответе нет блоков файлов вида ```<язык> path=<путь>. Верни полный текст файлов."
        elif arm == "C":
            rep_ = evaluate_c(task, files)
            fb = feedback_c(rep_)
        else:
            rep_ = evaluate_t(task, files)
            fb = feedback_t(rep_)
        rec.update({k2: rep_.get(k2) for k2 in ("passed", "passed_check", "interface_ok", "ids_preserved",
                                                 "ids_lost", "fabricated_ids", "no_files")})
        rec["diagnostics"] = rep_.get("diagnostics", [])[:SHOWN_DIAGNOSTICS]
        attempts.append(rec)
        if rep_.get("passed"):
            break
        prompt = "Проверка не прошла:\n" + fb + "\n\nИсправь и верни полный текст изменённых файлов."
    shutil.rmtree(workdir, ignore_errors=True)
    return {"task": task["id"], "arm": arm, "rep": rep, "status": "DONE", "attempts": attempts}


class Ledger:
    """Учёт условной стоимости: новый вызов не начинается, если потрачено ≥ лимита за вычетом запаса."""
    RESERVE = 0.30                 # верхняя оценка одного вызова Sonnet, $

    def __init__(self, spent: float):
        import threading
        self.spent, self.lock = spent, threading.Lock()

    def reserve(self) -> bool:
        with self.lock:
            return self.spent + self.RESERVE <= BUDGET_USD

    def spend(self, x: float):
        with self.lock:
            self.spent += x


def cmd_run(run_id: str, limit: int | None) -> int:
    import random
    from concurrent.futures import ThreadPoolExecutor
    out_dir = RESULTS / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    log = out_dir / "pairs.jsonl"
    done = {}
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["status"] == "DONE":
                done[(r["task"], r["arm"], r["rep"])] = r
    meta = out_dir / "meta.json"
    if not meta.exists():
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "pilot/writability",
                                "spec/language/guide-llm.md", "ref", ":!pilot/writability/results"],
                               capture_output=True, text=True).stdout.strip()
        if dirty:
            raise SystemExit("протокол, задачи или эталон не закоммичены — прогон не начинается:\n" + dirty)
        meta.write_text(json.dumps({"commit": head, "model": MODEL, "effort": EFFORT, "reps": REPS, "seed": SEED,
                                    "rounds": MAX_ROUNDS, "budget_usd": BUDGET_USD, "cli": claude_cli(),
                                    "cli_version": subprocess.run([claude_cli(), "--version"], capture_output=True,
                                                                  text=True).stdout.strip(),
                                    "tsc": tsc()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pairs = [(t, arm, rep) for t in all_tasks() for arm in ("C", "T") for rep in range(1, REPS + 1)]
    random.Random(SEED).shuffle(pairs)
    todo = [p for p in pairs if (p[0]["id"], p[1], p[2]) not in done][:limit]
    spent = sum(a["cost"] for r in done.values() for a in r["attempts"])
    ledger = Ledger(spent)
    import threading
    wlock = threading.Lock()

    def work(p):
        res = run_pair(p[0], p[1], p[2], out_dir, ledger)
        with wlock:
            with log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
            ok = res["attempts"] and res["attempts"][-1].get("passed")
            print(f"{res['task']} {res['arm']} r{res['rep']}: {res['status']} "
                  f"{'PASS' if ok else 'FAIL'} за {len(res['attempts'])} попыт.; потрачено ${ledger.spent:.2f}", flush=True)
        return res
    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, todo))
    return cmd_score(run_id)


def cmd_score(run_id: str) -> int:
    """Метрики protocol.md §4 по последней записи каждой пары."""
    out_dir = RESULTS / run_id
    pairs = {}
    for line in (out_dir / "pairs.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        pairs[(r["task"], r["arm"], r["rep"])] = r
    edits_c = {"W13", "W14", "W15", "W16"}
    summary = {"pairs": {}, "complete": True}
    for arm in ("C", "T"):
        rs = [r for k, r in pairs.items() if k[1] == arm]
        done = [r for r in rs if r["status"] == "DONE"]
        p1 = sum(1 for r in done if r["attempts"][0].get("passed")) / max(1, len(done))
        p3 = sum(1 for r in done if r["attempts"][-1].get("passed")) / max(1, len(done))
        cost = sum(a["cost"] for r in rs for a in r["attempts"])
        tin = sum((a.get("usage") or {}).get("input_tokens", 0) + (a.get("usage") or {}).get("cache_read_input_tokens", 0)
                  + (a.get("usage") or {}).get("cache_creation_input_tokens", 0) for r in rs for a in r["attempts"])
        tout = sum((a.get("usage") or {}).get("output_tokens", 0) for r in rs for a in r["attempts"])
        per_task = {}
        for r in done:
            per_task.setdefault(r["task"], []).append(bool(r["attempts"][-1].get("passed")))
        summary["pairs"][arm] = {"done": len(done), "expected": 20 * REPS, "P1": round(p1, 3), "P3": round(p3, 3),
                                 "cost_usd": round(cost, 2), "input_tokens": tin, "output_tokens": tout,
                                 "per_task_P3": {t: sum(v) / len(v) for t, v in sorted(per_task.items())}}
        if len(done) < 20 * REPS:
            summary["complete"] = False
    c_edits = [r for k, r in pairs.items() if k[1] == "C" and k[0] in edits_c and r["status"] == "DONE"]
    broken = [r for r in c_edits if any(a.get("ids_preserved") is False for a in r["attempts"])]
    summary["id_breakage_C"] = round(len(broken) / max(1, len(c_edits)), 3)
    summary["fabricated_ids_C"] = sum(len(a.get("fabricated_ids") or []) for k, r in pairs.items() if k[1] == "C"
                                      for a in r["attempts"])
    pc, pt = summary["pairs"]["C"]["P3"], summary["pairs"]["T"]["P3"]
    summary["K1"] = {"P3_ratio": round(pc / pt, 3) if pt else None,
                     "triggered": bool(pt and pc < 0.70 * pt) or summary["id_breakage_C"] > 0.05}
    rng = __import__("random").Random(SEED)
    tasks = sorted({k[0] for k in pairs})

    def boot(arm):
        vals = []
        for _ in range(2000):
            sample = [rng.choice(tasks) for _ in tasks]
            xs = [summary["pairs"][arm]["per_task_P3"].get(t, 0) for t in sample]
            vals.append(sum(xs) / len(xs))
        vals.sort()
        return [round(vals[50], 3), round(vals[1949], 3)]
    summary["bootstrap95_P3"] = {"C": boot("C"), "T": boot("T")}
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "pairs"} |
                     {"C": {k: v for k, v in summary["pairs"]["C"].items() if k != "per_task_P3"},
                      "T": {k: v for k, v in summary["pairs"]["T"].items() if k != "per_task_P3"}}, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate", action="store_true")
    g.add_argument("--dry-run", metavar="DIR")
    g.add_argument("--run", metavar="RUN_ID", help="прогон модели; повторный запуск продолжает незавершённые пары")
    g.add_argument("--score", metavar="RUN_ID", help="пересчитать метрики прогона")
    ap.add_argument("--limit", type=int, help="не больше N пар (пробный запуск)")
    a = ap.parse_args(argv)
    if a.validate:
        return cmd_validate()
    if a.dry_run:
        return cmd_dry_run(Path(a.dry_run))
    if a.score:
        return cmd_score(a.score)
    return cmd_run(a.run, a.limit)


if __name__ == "__main__":
    sys.exit(main())
