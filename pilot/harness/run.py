#!/usr/bin/env python3
"""Воспроизводимый локальный dry-run без LLM. Live execution намеренно отсутствует."""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import subprocess
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pilot.harness.common import Journal, encoded, load, manifest, save, sha
from pilot.harness.judge import posthoc
from pilot.harness.mediator import Session, ScriptedProvider, git_adapter, live_provider
from pilot.harness.sandbox import Sandbox

ROOT = Path(__file__).resolve().parents[2]
CASES = ["C01", "C04", "C05", "C06", "C08", "C10", "C11", "C12"]


def schedule(seed=20261027, repetitions=5):
    if repetitions < 3:
        raise ValueError("Минимум три повторения каждого случая и варианта")
    rng = random.Random(seed)
    blocks = [(rep, case) for rep in range(1, repetitions + 1) for case in CASES]
    rng.shuffle(blocks)
    rows = []
    for block, (rep, case) in enumerate(blocks, 1):
        arms = list("ABC")
        rng.shuffle(arms)
        for arm in arms:
            rows.append({"order": len(rows) + 1, "block": block, "repeat": rep, "case": case, "arm": arm,
                         "id": f"r{rep:02d}-{case}-{arm}", "provider_seed": rng.randrange(2**31)})
    return {"format": "bagaev-pilot-schedule/1", "seed": seed, "repetitions": repetitions,
            "cases": CASES, "rows": rows, "status": "PLANNED", "provider_seed_supported": None}


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def versions(repo):
    commands = {"python": ["/usr/bin/python3", "--version"], "node": ["/usr/bin/node", "--version"],
                "git": ["git", "--version"], "bwrap": ["bwrap", "--version"],
                "typescript": ["node", str(repo / "pilot/writability/node_modules/typescript/bin/tsc"), "--version"],
                "commit": ["git", "rev-parse", "HEAD"], "working_tree": ["git", "status", "--porcelain"]}
    out = {}
    for name, argv in commands.items():
        p = subprocess.run(argv, cwd=repo, capture_output=True, text=True, timeout=10)
        out[name] = {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    return out


def inputs(repo):
    paths = ["ref", "pilot/harness", "pilot/authorship/app-ts", "pilot/authorship/app-bagaev",
             "pilot/authorship/reference", "pilot/authorship/oracle", "pilot/authorship/mechanism",
             "pilot/authorship/links-ts"]
    out = {p: manifest(repo / p) for p in paths}
    for rel in ["pilot/authorship/arms.json", "pilot/authorship/preregistration.json", "pilot/authorship/protocol.md",
                "pilot/authorship/closed-commitments.json",
                "spec/language/guide-llm.md", "registry/data/core/authorship-fixtures.json", "pilot/authorship/data/seed.json"]:
        out[rel] = {"sha256": sha((repo / rel).read_bytes()), "bytes": (repo / rel).stat().st_size}
    out["typescript"] = manifest(repo / "pilot/writability/node_modules/typescript")
    return out


def provider_call(provider, session, tool, arguments=None):
    # Ограничитель срабатывает до отправки контекста даже scripted-процессу.
    if session.budget_reason() or session.data["status"] != "READY":
        return session.call(tool, arguments)
    action = provider.action(session, {"tool": tool, "arguments": arguments or {}})
    return session.call(action["tool"], action["arguments"])


def smoke(repo, directory, arm):
    session = Session(repo, directory, arm)
    session.initialize()
    provider = ScriptedProvider(repo)
    try:
        listing = provider_call(provider, session, "list")
        require("files" in listing and not any("reference" in p or ".bagaev" in p for p in listing["files"]), "LIST_BOUNDARY")
        path = "blog/byline.bag" if arm == "C" else "src/byline.ts"
        before = provider_call(provider, session, "read", {"path": path})
        require("text" in before, "READ_FAILED")
        found = provider_call(provider, session, "search", {"query": "byline"})
        require(bool(found.get("matches")), "SEARCH_FAILED")
        written = provider_call(provider, session, "write", {"path": path, "expected_sha256": before["sha256"],
                                                             "text": before["text"] + "\n// scripted dry-run\n"})
        require(written.get("status") in ("WRITTEN", "succeeded"), f"WRITE_FAILED: {written}")
        checked = provider_call(provider, session, "check")
        require(checked.get("status") == "PASS", f"CHECK_FAILED: {checked}")
        tested = provider_call(provider, session, "test")
        require(tested.get("tests") and all(t.get("status") == "PASS" for t in tested["tests"]), f"TEST_FAILED: {tested}")
        require(session.data["files"][path]["sha256"] != before["sha256"], "NO_REAL_WRITE")
        session.finish()
        return {"arm": arm, "outcome": "PASS", "directory": str(directory), "scripted_session": provider.session,
                "checks": len(tested["tests"]), "pilot_status": "NOT_RUN"}
    finally:
        provider.kill()


def resume_hook(repo, directory, arm):
    s = Session(repo, directory, arm)
    s.initialize()
    if arm != "A":
        added = s.call("bag", {"operation": "contract_update", "arguments": {"ops": [
            {"op": "add_clause", "id": oid.lower(), "claim": oid + " остаётся открытым",
             "method": {"test": "probe.pending_" + oid.lower()}} for oid in ("O04", "O05")]}})
        require(added.get("status") == "succeeded", f"CLAUSES_FAILED: {added}")
    old_provider = ScriptedProvider(repo)
    before = provider_call(old_provider, s, "resume")
    old_id = old_provider.session
    old_provider.kill()  # реальный SIGKILL provider, состояние инструмента живёт отдельно
    s = Session(repo, directory, resume=True)
    new_provider = ScriptedProvider(repo)
    try:
        s.reset_context(old_id, new_provider.session)
        after = provider_call(new_provider, s, "resume")
        require(before == after and old_id != new_provider.session, "RESUME_CHANGED")
        text = encoded(after).decode().lower()
        require("o04" in text and "o05" in text, "OPEN_OBLIGATIONS_LOST")
        if arm != "A":
            refused = s.call("accept")
            require(refused.get("error", {}).get("code") == "OPEN_OBLIGATIONS", "RESUME_ACCEPTED_OPEN")
        s.finish()
        return {"case": "C06", "arm": arm, "outcome": "PASS", "provider_killed": True,
                "state_equal": True, "graph_obligations": arm != "A"}
    finally:
        new_provider.kill()


def head_hook(repo, directory, arm):
    s = Session(repo, directory, arm)
    s.initialize()
    if arm == "A":
        advanced = git_adapter(repo).advance_head(s.app, s.control / "git")
        s.journal.append("hook", case="C07", response=advanced)
        s.persist()
    else:
        advanced = s.controller("advance_head")
    result = s.call("accept")
    code = result.get("code", result.get("error", {}).get("code"))
    require(code == "STALE_BASE", f"STALE_ACCEPT: {result}")
    current = git_adapter(repo).head(s.control / "git") if arm == "A" else s.controller("head")["head"]
    require(current == advanced["head"] and current != s.data["base"], "HEAD_OVERWRITTEN")
    s.finish()
    return {"case": "C07", "arm": arm, "outcome": "PASS", "code": code, "head": current}


def unavailable_hook(repo, directory, arm):
    s = Session(repo, directory, arm)
    s.initialize()
    hidden = s.hide_export()
    require(not (s.app / hidden["path"]).exists(), "SOURCE_STILL_VISIBLE")
    require(s.call("read", {"path": hidden["path"]}).get("code") == "REQUIRED_SOURCE_UNAVAILABLE", "HIDDEN_READ")
    require(not any(m["path"] == hidden["path"] for m in s.call("search", {"query": "export"})["matches"]), "HIDDEN_SEARCH")
    for tool in ("check", "test", "accept"):
        require(s.call(tool).get("status") == "INCOMPLETE", "HIDDEN_TRANSITIVE_TOOL")
    if arm != "A":
        for operation in ("inspect", "context", "search", "work_resume"):
            require(s.call("bag", {"operation": operation}).get("status") == "INCOMPLETE", "HIDDEN_SNAPSHOT_BYPASS")
    s.finish("REQUIRED_SOURCE_UNAVAILABLE")
    return dict(hidden, arm=arm, outcome="PASS", boundary="mediator; engine missing-source semantics not claimed")


def defect_hooks(repo, directory):
    module_spec = importlib.util.spec_from_file_location("pilot_mutations", repo / "pilot/authorship/oracle/mutants.py")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    arms = load(repo / "pilot/authorship/arms.json")["arms"]
    directory.mkdir()
    reports = []
    for arm in "ABC":
        for name in ("export_first_author_only", "export_old_constant", "index_not_updated"):
            target = directory / f"{arm}-{name}"
            metadata = module.inject(arm, name, repo / arms[arm]["reference"], target)
            checked, elapsed = Sandbox(repo, target).call(arm, "check")
            require(metadata["before"] != metadata["after"] and checked.get("status") == "PASS", f"INVALID_HOOK: {metadata} {checked}")
            reports.append(dict(metadata, arm=arm, outcome="PASS", check=checked, elapsed_seconds=elapsed,
                                evidence="injection and compilation only; semantic detection belongs to mechanism/oracle"))
    save(directory / "hooks.json", reports)
    return reports


def dry_run(repo, output, smoke_repetitions=3):
    if smoke_repetitions < 3:
        raise ValueError("Dry-run проверяет минимум три независимые копии каждого варианта")
    output.mkdir(parents=True, exist_ok=False)
    report = {"format": "bagaev-pilot-dry-run/1", "provider": "scripted", "pilot_status": "NOT_RUN",
              "research_attempts": [], "llm_measurements": None, "outcome": "ERROR", "smoke": [], "hooks": [],
              "started_at": time.time()}
    try:
        save(output / "versions.json", versions(repo))
        source_inputs = inputs(repo)
        save(output / "inputs.json", source_inputs)
        report["inputs_sha256"] = sha(encoded(source_inputs))
        prereg = load(repo / "pilot/authorship/preregistration.json")
        save(output / "schedule.json", schedule(prereg["seed"], prereg["repetitions"]))
        for repeat in range(1, smoke_repetitions + 1):
            for arm in "ABC":
                report["smoke"].append(smoke(repo, output / f"smoke-{repeat}-{arm}", arm))
        for arm in "ABC":
            for label, hook in (("C06", resume_hook), ("C07", head_hook), ("C12", unavailable_hook)):
                report["hooks"].append(hook(repo, output / f"hook-{label}-{arm}", arm))
        report["hooks"].extend(defect_hooks(repo, output / "controller-only-defects"))
        # S0 компилируется и проходит свои тесты, обычный A может принять его.
        # Независимый posthoc должен увидеть провал нового задания: oracle не gate.
        negative = Session(repo, output / "posthoc-separation-A", "A")
        negative.initialize()
        receipt = negative.call("accept")
        assessed = posthoc(repo, "A", negative.app, receipt, negative.control / "posthoc.json",
                           accepted_sources=negative.data["accepted_files"])
        require(assessed["false_accept"] is True, "ORACLE_NOT_INDEPENDENT_OR_TOOL_ERROR")
        negative.finish()
        report["posthoc_separation"] = {"outcome": "PASS", "scripted_false_accept_visible": True,
                                         "research_false_accepts": None}
        report["outcome"] = "PASS"
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "detail": str(exc)}
    report["finished_at"] = time.time()
    save(output / "result.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("schedule", "dry-run", "live"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261027)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--smoke-repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.mode == "live":
        try:
            live_provider()
        except RuntimeError as exc:
            print(json.dumps({"status": "ERROR", "code": "LIVE_DISABLED", "detail": str(exc)}, ensure_ascii=False))
            return 2
    if args.mode == "schedule":
        require(not args.output.exists(), "OUTPUT_EXISTS")
        save(args.output, schedule(args.seed, args.repetitions))
        print(json.dumps({"status": "PLANNED", "output": str(args.output)}))
        return 0
    result = dry_run(ROOT, args.output.resolve(), args.smoke_repetitions)
    print(json.dumps({"outcome": result["outcome"], "pilot_status": "NOT_RUN", "output": str(args.output),
                      "error": result.get("error")}, ensure_ascii=False))
    return 0 if result["outcome"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
