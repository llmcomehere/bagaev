"""MCP stdio для протокола агента (spec/protocol/agent-protocol.md §10; D86, D17).

JSON-RPC 2.0 по строкам stdin/stdout, методы `initialize`, `tools/list`, `tools/call`. Каждый инструмент
`bag_<операция>` — та же операция слоя `Ops`, что у CLI `bag op`: один запрос — один и тот же ответ (T14-C05).
Субъект задаётся при запуске сервера (`--principal`), а не аргументами инструмента.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from bagaev_ref.protocol.ops import PROTOCOL, READ, WRITE, Ops

MCP_VERSION = "2024-11-05"

DESCRIPTIONS = {
    "search": "кандидаты по смыслу с основаниями; выбор не делается",
    "inspect": "текст и отношения сущности снимка или кандидата",
    "relations": "рёбра сущности кандидата с provenance",
    "impact": "анализ влияния кандидата относительно базы",
    "context": "ContextPack шага с бюджетом",
    "why": "почему сущность затронута или исключена",
    "check": "диагностики кандидата",
    "run_tests": "прогнать тесты кандидата без записи свидетельств",
    "work_resume": "состояние работы: обязательства, блокеры, готовность (только чтение)",
    "change_begin": "начать работу от текущего head",
    "contract_update": "изменить ChangeContract (новая ревизия)",
    "apply": "применить SourceEdit к кандидату",
    "verify": "прогнать тесты кандидата и записать свидетельства",
    "rebase": "перенести правки работы на текущий head",
    "accept": "принять кандидата: CAS head с записью приёмки",
    "abandon": "закрыть работу без приёмки",
}


def tool_schema(op: str) -> dict:
    props = {"arguments": {"type": "object"}}
    required = []
    if op not in ("change_begin", "search", "inspect"):
        props["change_id"] = {"type": "string"}
        required.append("change_id")
    if op in WRITE:
        props["idempotency_key"] = {"type": "string", "minLength": 16, "maxLength": 128}
        required.append("idempotency_key")
        if op != "change_begin":
            props["expected_work_revision"] = {"type": "integer", "minimum": 1}
            required.append("expected_work_revision")
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


def tools() -> list:
    return [{"name": "bag_" + op, "description": DESCRIPTIONS[op], "inputSchema": tool_schema(op)}
            for op in sorted(READ | WRITE)]


def _error(mid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def handle(ops: Ops, msg):
    """Один объект JSON-RPC 2.0. Уведомление (без `id`) исполняется, но ответа не получает."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str) \
            or ("id" in msg and not (msg["id"] is None or isinstance(msg["id"], (str, int)) and not isinstance(msg["id"], bool))):
        return _error(msg.get("id") if isinstance(msg, dict) and isinstance(msg.get("id"), (str, int)) else None,
                      -32600, "неверный запрос JSON-RPC 2.0")
    notification = "id" not in msg
    mid, method, params = msg.get("id"), msg["method"], msg.get("params", {})
    if not isinstance(params, dict):
        return None if notification else _error(mid, -32602, "params — объект")
    try:
        if method == "initialize":
            result = {"protocolVersion": MCP_VERSION, "capabilities": {"tools": {}},
                      "serverInfo": {"name": "bagaev-ref", "version": "0.0.0"}}
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            result = {"tools": tools()}
        elif method == "tools/call":
            name, args = params.get("name"), params.get("arguments", {})
            if not isinstance(name, str) or not name.startswith("bag_") or name[4:] not in READ | WRITE:
                return None if notification else _error(mid, -32602, f"неизвестный инструмент {name}")
            if not isinstance(args, dict):
                return None if notification else _error(mid, -32602, "arguments — объект")
            req = dict(args, protocol=PROTOCOL, operation=name[4:])
            resp = ops.call(req)
            result = {"content": [{"type": "text", "text": json.dumps(resp, ensure_ascii=False, sort_keys=True)}],
                      "structuredContent": resp, "isError": resp["status"] != "succeeded"}
        else:
            return None if notification else _error(mid, -32601, f"метод {method} не поддержан")
    except Exception as e:                               # дефект реализации не роняет сервер
        return None if notification else _error(mid, -32603, f"внутренняя ошибка: {type(e).__name__}")
    return None if notification else {"jsonrpc": "2.0", "id": mid, "result": result}


def handle_line(ops: Ops, line: str):
    """Строка stdin → ответ (объект, массив для пакета или None)."""
    try:
        msg = json.loads(line)
    except ValueError:
        return _error(None, -32700, "не JSON")
    if isinstance(msg, list):
        if not msg:
            return _error(None, -32600, "пустой пакет")
        replies = [r for r in (handle(ops, m) for m in msg) if r is not None]
        return replies or None
    return handle(ops, msg)


def serve(root: Path, principal: str, inp=sys.stdin, out=sys.stdout) -> int:
    ops = Ops(root, principal)
    try:
        for line in inp:
            line = line.strip()
            if not line:
                continue
            reply = handle_line(ops, line)
            if reply is not None:
                out.write(json.dumps(reply, ensure_ascii=False) + "\n")
                out.flush()
    finally:
        ops.close()
    return 0
