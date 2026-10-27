#!/usr/bin/env python3
"""Reveal и подготовка закрытого C10; ожидаемые ответы остаются у контроллера."""
from __future__ import annotations

import argparse
import hmac
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pilot.harness.commit_reveal import commitment
from pilot.harness.common import load, save, sha
from pilot.harness.judge import posthoc
from pilot.harness.mediator import Session


def validate(package):
    if not isinstance(package, dict) or set(package) != {"format", "tasks"} or package["format"] != "bagaev-pilot-closed/1":
        raise ValueError("CLOSED_FORMAT")
    if not isinstance(package["tasks"], list) or not package["tasks"]:
        raise ValueError("CLOSED_TASKS")
    seen = set()
    for task in package["tasks"]:
        if not isinstance(task, dict) or set(task) != {"id", "case", "initial", "public", "expected"}:
            raise ValueError("CLOSED_TASK_SHAPE")
        tid = task["id"]
        if not isinstance(tid, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", tid) or tid in seen:
            raise ValueError("CLOSED_TASK_ID")
        seen.add(tid)
        if task["case"] != "C10" or task["initial"] != "multi-author":
            raise ValueError("CLOSED_CASE_NOT_IMPLEMENTED")
        public = task["public"]
        if not isinstance(public, dict) or set(public) != {"instruction", "separator"} or any(
                not isinstance(public[x], str) or not public[x] for x in public):
            raise ValueError("CLOSED_PUBLIC_SHAPE")
        if len(public["separator"].encode("utf-8")) > 64 or "\n" in public["separator"]:
            raise ValueError("CLOSED_SEPARATOR")
        expected = task["expected"]
        if not isinstance(expected, dict) or set(expected) != {"bylines"} or not isinstance(expected["bylines"], dict) \
                or set(expected["bylines"]) != {"a_101", "a_102"} or any(
                    not isinstance(v, str) or not v for v in expected["bylines"].values()):
            raise ValueError("CLOSED_EXPECTATIONS")
    return package


def reveal(payload: Path, nonce: Path, digest: str):
    raw = payload.read_bytes()
    if not hmac.compare_digest(commitment(raw, nonce.read_bytes()), digest):
        raise ValueError("COMMITMENT_MISMATCH")
    return validate(json.loads(raw))


def task_from(package, task_id):
    return next(task for task in package["tasks"] if task["id"] == task_id)


def materialize(repo: Path, payload: Path, nonce: Path, digest: str, task_id: str, arm: str, output: Path):
    task = task_from(reveal(payload, nonce, digest), task_id)
    arms = load(repo / "pilot/authorship/arms.json")["arms"]
    # C10 начинается с уже работающего multi-author приложения; target separator в него НЕ применяется.
    prompt = task["public"]["instruction"] + "\nНовый разделитель: " + json.dumps(task["public"]["separator"], ensure_ascii=False)
    session = Session(repo, output, arm, initial_source=repo / arms[arm]["reference"], prompt=prompt)
    session.data["closed_task"] = {"commitment": digest, "id": task_id, "case": "C10"}
    session.journal.append("closed_task_prepared", commitment=digest, task_id=task_id, case="C10")
    session.persist()
    session.initialize()
    return session


def evaluate(repo: Path, session_dir: Path, payload: Path, nonce: Path, digest: str):
    session = Session(repo, session_dir, resume=True)
    binding = session.data["closed_task"]
    if binding["commitment"] != digest:
        raise ValueError("CLOSED_SESSION_BINDING")
    if session.data["status"] == "READY":
        raise ValueError("DECISION_NOT_FINAL")
    task = task_from(reveal(payload, nonce, digest), binding["id"])
    return posthoc(repo, session.arm, session.app, session.data.get("acceptance_receipt", {}),
                   session.control / "posthoc.json", expected_bylines=task["expected"]["bylines"],
                   accepted_sources=session.data.get("accepted_files"))


def probe(repo: Path, payload: Path, nonce: Path, digest: str, task_id: str, arm: str, output: Path):
    """Только совместимость одного закрытого C10, без provider и без исследовательской попытки."""
    task = task_from(reveal(payload, nonce, digest), task_id)
    output.mkdir(parents=True, exist_ok=False)
    summary = {"commitment": digest, "task_id": task_id, "arm": arm, "provider": "scripted-controller-only",
               "pilot_status": "NOT_RUN", "llm_measurements": None}
    for label, edit in (("unchanged", False), ("corrected", True)):
        session = materialize(repo, payload, nonce, digest, task_id, arm, output / label)
        if edit:
            rel = "blog/byline.bag" if arm == "C" else "src/byline.ts"
            before = (session.app / rel).read_bytes()
            text = before.decode("utf-8")
            if text.count('" · "') != 1:
                raise ValueError("C10_PROBE_SOURCE_PATTERN_MISMATCH")
            updated = text.replace('" · "', json.dumps(task["public"]["separator"], ensure_ascii=False))
            written = session.call("write", {"path": rel, "expected_sha256": sha(before), "text": updated})
            if written.get("status") not in ("WRITTEN", "succeeded") or session.call("check").get("status") != "PASS":
                raise ValueError("C10_PROBE_EDIT_FAILED")
        session.finish("CONTROLLER_ONLY_C10_COMPATIBILITY")
        result = evaluate(repo, session.directory, payload, nonce, digest)
        summary[label] = {"assessment": result["assessment"], "oracle": result["oracle"]["outcome"],
                          "failed_check_ids": result["oracle"]["failed"]}
    okay = summary["unchanged"]["oracle"] == "FAIL" and summary["corrected"]["oracle"] == "PASS" \
        and all(summary[label]["assessment"] == "ASSESSED" for label in ("unchanged", "corrected"))
    summary["outcome"] = "PASS" if okay else "FAIL"
    save(output / "compatibility.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verify", "prepare", "evaluate", "probe"))
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--nonce-file", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--task")
    parser.add_argument("--arm", choices=("A", "B", "C"))
    parser.add_argument("--session", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    package = reveal(args.payload, args.nonce_file, args.sha256)
    if args.mode in ("prepare", "probe"):
        if args.task is None or args.arm is None or args.session is None:
            parser.error("prepare/probe требуют --task --arm --session")
        if args.mode == "probe":
            result = probe(root, args.payload, args.nonce_file, args.sha256, args.task, args.arm, args.session)
            print(json.dumps({"outcome": result["outcome"], "pilot_status": "NOT_RUN", "sha256": args.sha256}))
            return 0 if result["outcome"] == "PASS" else 1
        else:
            materialize(root, args.payload, args.nonce_file, args.sha256, args.task, args.arm, args.session)
    elif args.mode == "evaluate":
        if args.session is None:
            parser.error("evaluate требует --session")
        result = evaluate(root, args.session, args.payload, args.nonce_file, args.sha256)
        print(json.dumps({"assessment": result["assessment"], "oracle": result["oracle"]["outcome"],
                          "false_accept": result["false_accept"], "sha256": args.sha256}))
        return 0 if result["assessment"] == "ASSESSED" and result["oracle"]["outcome"] == "PASS" else 1
    print(json.dumps({"status": "VERIFIED", "sha256": args.sha256, "tasks": len(package["tasks"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
