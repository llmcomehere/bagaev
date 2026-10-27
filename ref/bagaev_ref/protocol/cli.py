"""Подкоманды проекта и протокола (spec/protocol/agent-protocol.md §10): `bag project init`, `bag op`,
`bag work resume`, `bag mcp [--selftest]`. Субъект — `--principal` или переменная BAG_PRINCIPAL."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def principal_of(a) -> str:
    return a.principal or os.environ.get("BAG_PRINCIPAL") or "local"


def emit(obj, a):
    print(json.dumps(obj, ensure_ascii=False, indent=None if getattr(a, "json", False) else 2, sort_keys=True))


def cmd_init(a) -> int:
    from bagaev_ref.protocol.ops import init_project
    r = init_project(Path(a.root), principal_of(a))
    emit(r, a)
    return 0 if r["outcome"] == "INITIALIZED" else 1


def cmd_op(a) -> int:
    from bagaev_ref.protocol.ops import Ops
    text = Path(a.request[1:]).read_text(encoding="utf-8") if a.request.startswith("@") else a.request
    try:
        req = json.loads(text)
    except json.JSONDecodeError as e:
        emit({"status": "failed", "error": {"code": "REQUEST_INVALID", "data": {"detail": str(e)}}}, a)
        return 2
    ops = Ops(Path(a.root), principal_of(a))
    try:
        r = ops.call(req)
    finally:
        ops.close()
    emit(r, a)
    return 0 if r["status"] == "succeeded" else 1


def cmd_resume(a) -> int:
    from bagaev_ref.protocol.ops import PROTOCOL, Ops
    ops = Ops(Path(a.root), principal_of(a))
    try:
        args = {"budget": a.budget} if a.budget is not None else {}
        r = ops.call({"protocol": PROTOCOL, "operation": "work_resume", "change_id": a.change, "arguments": args})
    finally:
        ops.close()
    emit(r, a)
    return 0 if r["status"] == "succeeded" else 1


def cmd_mcp(a) -> int:
    if a.selftest:
        return selftest(a)
    from bagaev_ref.protocol.mcp_server import serve
    return serve(Path(a.root), principal_of(a))


def selftest(a) -> int:
    """Паритет транспортов (T14-C05): один сценарий через MCP stdio и через CLI `bag op` на двух копиях
    проекта даёт одинаковые ответы, кроме дайджестов в обоих одинаково детерминированных полях."""
    import shutil
    from bagaev_ref.protocol.ops import PROTOCOL
    src = Path(a.root)
    tmp = Path(tempfile.mkdtemp(prefix="bag-mcp-"))
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2]))
    try:
        roots = []
        for name in ("cli", "mcp"):
            dst = tmp / name
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".bagaev"))
            subprocess.run([sys.executable, "-m", "bagaev_ref", "project", "init", str(dst), "--principal", "p", "--json"],
                           env=env, capture_output=True, check=True)
            roots.append(dst)
        script = [{"operation": "change_begin", "idempotency_key": "selftest-begin-0001", "arguments": {"intent": "проверка"}},
                  {"operation": "work_resume", "arguments": {}},
                  {"operation": "verify", "idempotency_key": "selftest-verify-001", "expected_work_revision": 1, "arguments": {}},
                  {"operation": "accept", "idempotency_key": "selftest-accept-001", "expected_work_revision": 2, "arguments": {}},
                  {"operation": "accept", "idempotency_key": "selftest-accept-001", "expected_work_revision": 2, "arguments": {}},
                  {"operation": "accept", "idempotency_key": "selftest-accept-001", "expected_work_revision": 9, "arguments": {}}]
        # CLI
        cli_out, change = [], None
        for step in script:
            req = dict(step, protocol=PROTOCOL)
            if step["operation"] != "change_begin":
                req["change_id"] = change
            p = subprocess.run([sys.executable, "-m", "bagaev_ref", "op", str(roots[0]), json.dumps(req), "--principal", "p",
                                "--json"], env=env, capture_output=True, text=True)
            r = json.loads(p.stdout)
            change = change or r.get("change_id")
            cli_out.append(r)
        # MCP
        proc = subprocess.Popen([sys.executable, "-m", "bagaev_ref", "mcp", str(roots[1]), "--principal", "p"], env=env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        msgs = [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}]
        lines = [json.dumps(m) for m in msgs]
        mcp_out, change2 = [], None
        proc.stdin.write("\n".join(lines) + "\n")
        proc.stdin.flush()
        init = json.loads(proc.stdout.readline())
        listing = json.loads(proc.stdout.readline())
        for i, step in enumerate(script):
            args = {k: v for k, v in step.items() if k != "operation"}
            if step["operation"] != "change_begin":
                args["change_id"] = change2
            msg = {"jsonrpc": "2.0", "id": 10 + i, "method": "tools/call",
                   "params": {"name": "bag_" + step["operation"], "arguments": args}}
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()
            r = json.loads(proc.stdout.readline())["result"]["structuredContent"]
            change2 = change2 or r.get("change_id")
            mcp_out.append(r)
        proc.stdin.close()
        proc.wait(timeout=60)
        same = cli_out == mcp_out
        report = {"outcome": "PARITY" if same else "MISMATCH", "steps": len(script),
                  "mcp_protocol": init["result"]["protocolVersion"], "tools": len(listing["result"]["tools"]),
                  "statuses": [r["status"] for r in cli_out],
                  "codes": [r.get("error", {}).get("code") for r in cli_out]}
        if not same:
            report["diff"] = [i for i, (x, y) in enumerate(zip(cli_out, mcp_out)) if x != y]
        emit(report, a)
        return 0 if same else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def register(sub) -> None:
    pp = sub.add_parser("project", help="проектное хранилище .bagaev (D85)")
    ps = pp.add_subparsers(dest="project_command", required=True)
    ip = ps.add_parser("init", help="начальный снимок рабочего дерева: первый принятый head")
    ip.add_argument("root")
    ip.add_argument("--principal")
    ip.add_argument("--json", action="store_true")
    ip.set_defaults(fn=cmd_init)

    op = sub.add_parser("op", help="операция протокола агента: JSON-запрос (или @файл) → JSON-ответ")
    op.add_argument("root")
    op.add_argument("request")
    op.add_argument("--principal")
    op.add_argument("--json", action="store_true")
    op.set_defaults(fn=cmd_op)

    wp = sub.add_parser("work", help="состояние работы")
    ws = wp.add_subparsers(dest="work_command", required=True)
    rp = ws.add_parser("resume", help="пересчитать состояние работы (только чтение)")
    rp.add_argument("root")
    rp.add_argument("change")
    rp.add_argument("--budget", type=int, help="бюджет ContextPack")
    rp.add_argument("--principal")
    rp.add_argument("--json", action="store_true")
    rp.set_defaults(fn=cmd_resume)

    mp = sub.add_parser("mcp", help="MCP stdio для агента (JSON-RPC 2.0)")
    mp.add_argument("root")
    mp.add_argument("--principal")
    mp.add_argument("--selftest", action="store_true", help="паритет MCP и CLI на копиях проекта")
    mp.add_argument("--json", action="store_true")
    mp.set_defaults(fn=cmd_mcp)
