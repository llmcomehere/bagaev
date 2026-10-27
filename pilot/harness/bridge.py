#!/usr/bin/env python3
"""Доверенный процесс внутри bwrap. Принимает только JSON, не shell-команды."""
from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.setrecursionlimit(100000)
from bagaev_ref.change import lang as L
from bagaev_ref.change import workstate as W
from bagaev_ref.protocol.ops import Ops, init_project

APP = Path("/workspace")

# Произвольный код TS-теста не видит и не меняет ProjectStore родительского инструмента.
# Тест исполняет отдельный bwrap контроллера: вложенные user namespaces доступны не везде.
_run = subprocess.run


def test_sandbox(argv, *args, **kwargs):
    if isinstance(argv, list) and argv and argv[0] == "node" and "--test" in argv:
        root = Path(kwargs["cwd"])
        token = uuid.uuid4().hex
        request = Path("/rpc") / (token + ".request.json")
        response = Path("/rpc") / (token + ".response.json")
        job = {"test": Path(argv[-1]).relative_to(root).as_posix(),
               "files": {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
                         for p in root.rglob("*") if p.is_file()}}
        temporary = request.with_suffix(".tmp")
        temporary.write_text(json.dumps(job), encoding="utf-8")
        temporary.replace(request)
        while not response.exists():
            time.sleep(0.005)
        result = json.loads(response.read_bytes())
        return subprocess.CompletedProcess(argv, result["returncode"], result["stdout"], result["stderr"])
    return _run(argv, *args, **kwargs)


subprocess.run = test_sandbox


def main(request):
    action, arm = request["action"], request["arm"]
    language = L.LANGS["bagaev" if arm == "C" else "typescript"]
    if action in ("check", "test"):
        files = {p.relative_to(APP).as_posix(): p.read_bytes() for p in APP.rglob("*")
                 if p.is_file() and p.suffix in language.exts
                 and not any(x.startswith(".") or x == "node_modules" for x in p.relative_to(APP).parts)}
        if action == "check":
            _, diagnostics = language.check(files)
            return {"status": "PASS" if diagnostics is None else "FAIL", "diagnostics": diagnostics or []}
        return language.run_tests(files)
    if arm == "A":
        return {"status": "ERROR", "code": "TOOL_NOT_ALLOWED"}
    if action == "init":
        return init_project(APP, "pilot-agent")
    ops = Ops(APP, "pilot-agent")
    try:
        if action == "op":
            response = ops.call(request["request"])
            if response["status"] == "succeeded" and request["request"]["operation"] in ("apply", "rebase"):
                work = W.work_row(ops.store, response["change_id"])
                sources = ops.store.files(work["candidate"])
                # Материализация только нормализованных путей исходников из ProjectStore.
                from bagaev_ref.change.sourceedit import valid_path
                if not all(valid_path(p, language.exts) for p in sources):
                    raise ValueError("UNSAFE_SNAPSHOT_PATH")
                for p in APP.rglob("*"):
                    rel = p.relative_to(APP).as_posix()
                    if p.is_file() and valid_path(rel, language.exts) and rel not in sources:
                        p.unlink()
                for rel, data in sources.items():
                    dst = APP / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(data)
            return response
        if action == "advance_head":
            # Управляемая инъекция внешнего writer: не доказательство приёмки его программы.
            before = ops.store.meta("head")
            files = ops.store.files(before)
            path = "blog/byline.bag" if arm == "C" else "src/byline.ts"
            files[path] += b"\n// C07 external writer\n"
            db = ops.store.db
            db.execute("BEGIN IMMEDIATE")
            sid = ops.store.snapshot(files, [before])
            db.execute("UPDATE snapshots SET accepted = 1 WHERE id = ?", (sid,))
            ops.store.set_meta("head", sid)
            ops.store.set_meta("head_revision", int(ops.store.meta("head_revision")) + 1)
            ops.store.journal("harness_external_head", sid, {"before": before})
            db.execute("COMMIT")
            return {"status": "INJECTED", "before": before, "head": sid}
        if action == "head":
            return {"head": ops.store.meta("head")}
        raise ValueError("UNKNOWN_BRIDGE_ACTION")
    finally:
        ops.close()


if __name__ == "__main__":
    try:
        result = main(json.load(sys.stdin))
    except Exception as exc:
        result = {"status": "ERROR", "code": "BRIDGE_ERROR", "detail": type(exc).__name__}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
