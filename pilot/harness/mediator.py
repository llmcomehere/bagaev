"""Ограниченные инструменты одной попытки; oracle не участвует в приёмке."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path, PurePosixPath

from .common import Journal, encoded, load, manifest, save, sha
from .sandbox import Sandbox, base_command

PROMPT = ("Измени приложение: вместо ровно одного автора статьи разреши непустой упорядоченный список "
          "существующих людей без повторов. Сохрани старую атрибуцию миграцией. Подпись, профиль, "
          "сохранённый поиск и JSON-экспорт должны передавать всех авторов. Повтор события не дублирует "
          "результат. Авторство не даёт редакторских прав. Сохрани остальные обязательства. "
          "Пользуйся только объявленными инструментами. Не считай отказ от всех задач успехом.")

LIMITS = {"turns": 80, "context_token_upper_bound": 24000, "total_token_upper_bound": 160000,
          "wall_seconds": 900, "tool_seconds": 30, "tool_output_bytes": 96000, "write_bytes": 96000}
TERMINAL = {"ERROR", "INCOMPLETE", "BUDGET_STOP"}


def git_adapter(repo: Path):
    path = repo / "pilot/authorship/mechanism/git_accept.py"
    if not path.is_file():
        raise RuntimeError("A_GIT_ADAPTER_UNAVAILABLE")
    spec = importlib.util.spec_from_file_location("pilot_git_accept", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AccessDenied(ValueError):
    pass


class Session:
    def __init__(self, repo: Path, directory: Path, arm: str | None = None, *, limits=None, resume=False,
                 initial_source: Path | None = None, prompt: str = PROMPT):
        self.repo, self.directory = repo.resolve(), directory.resolve()
        self.app = self.directory / "workspace"
        self.control = self.directory / "control"
        self.checkpoint = self.control / "checkpoint.json"
        if resume:
            self.data = load(self.checkpoint)
            self.journal = Journal(self.control / "actions.jsonl")
            if self.data["journal_tail"] != self.journal.tail:
                raise ValueError("CHECKPOINT_JOURNAL_MISMATCH: не повторять операцию без сверки")
            if self.data["files"] != manifest(self.app):
                raise ValueError("CHECKPOINT_WORKSPACE_MISMATCH")
            if self.data["runtime_binding"] != self.runtime_binding():
                raise ValueError("RUNTIME_CHANGED")
        else:
            if arm not in ("A", "B", "C"):
                raise ValueError("INVALID_ARM")
            self.directory.mkdir(parents=True, exist_ok=False)
            self.control.mkdir()
            arms = load(self.repo / "pilot/authorship/arms.json")["arms"]
            source = initial_source or self.repo / arms[arm]["baseline"]
            manifest(source)  # отбрасывать symlink до copytree
            shutil.copytree(source, self.app)
            guide = (self.repo / "spec/language/guide-llm.md").read_text(encoding="utf-8") if arm == "C" else ""
            if guide:
                (self.app / "guide-llm.md").write_text(guide, encoding="utf-8")
            self.journal = Journal(self.control / "actions.jsonl")
            self.data = {"format": "bagaev-pilot-session/1", "arm": arm, "provider": "scripted",
                         "pilot_status": "NOT_RUN", "status": "READY", "created_at": time.time(),
                         "limits": dict(LIMITS, **(limits or {})), "turns": 0, "context_bytes_total": 0,
                         "tool_seconds": 0.0, "accepted": False, "hidden": [], "cursor": 0,
                         "conversation": [{"role": "system", "text": prompt}, {"role": "guide", "text": guide}],
                         "llm_measurements": {"input_tokens": None, "output_tokens": None, "cost_usd": None},
                         "runtime_binding": self.runtime_binding(), "baseline": manifest(self.app),
                         "open_obligations": ["O04", "O05"], "research_attempt": False}
            self.journal.append("prepared", arm=arm, baseline=self.data["baseline"],
                                guide_sha256=sha(guide.encode()) if guide else None)
            self.persist()
        self.sandbox = Sandbox(self.repo, self.app, self.data["limits"]["tool_seconds"])

    def runtime_binding(self):
        out = {"ref": manifest(self.repo / "ref/bagaev_ref"),
               "extractor": manifest(self.repo / "pilot/authorship/links-ts"),
               "harness": manifest(self.repo / "pilot/harness")}
        for key, rel in (("arms", "pilot/authorship/arms.json"),
                         ("preregistration", "pilot/authorship/preregistration.json"),
                         ("git_adapter", "pilot/authorship/mechanism/git_accept.py")):
            path = self.repo / rel
            out[key] = sha(path.read_bytes()) if path.exists() else None
        tsc = self.repo / "pilot/writability/node_modules/typescript"
        out["typescript"] = manifest(tsc) if tsc.exists() else None
        return sha(encoded(out))

    @property
    def arm(self):
        return self.data["arm"]

    def persist(self):
        self.data["files"] = manifest(self.app)
        self.data["journal_tail"] = self.journal.tail
        save(self.checkpoint, self.data)

    def path(self, name, *, write=False):
        if not isinstance(name, str) or not name:
            raise AccessDenied("PATH_DENIED")
        path = PurePosixPath(name)
        if path.is_absolute() or path.as_posix() != name or any(
                x in (".", "..", "node_modules") or x.startswith(".") for x in path.parts):
            raise AccessDenied("PATH_DENIED")
        current = self.app
        for segment in path.parts:
            current /= segment
            if current.is_symlink():
                raise AccessDenied("SYMLINK_DENIED")
        if name in self.data["hidden"]:
            raise AccessDenied("REQUIRED_SOURCE_UNAVAILABLE")
        if write and (name == "guide-llm.md" or path.suffix not in ((".bag",) if self.arm == "C" else (".ts", ".json"))):
            raise AccessDenied("WRITE_DENIED")
        return current

    def controller(self, action, **arguments):
        response, elapsed = self.sandbox.call(self.arm, action, **arguments)
        self.data["tool_seconds"] += elapsed
        self.journal.append("controller_tool", action=action, arguments=arguments,
                            response=response, elapsed_seconds=elapsed)
        self.persist()
        return response

    def initialize(self):
        if self.arm == "A":
            self.data["base"] = git_adapter(self.repo).init(self.app, self.control / "git")
            self.journal.append("controller_git_init", head=self.data["base"])
        else:
            initialized = self.controller("init")
            if initialized.get("outcome") != "INITIALIZED":
                self.data["status"] = "ERROR"
                self.persist()
                raise RuntimeError(f"PROJECT_INIT_FAILED: {initialized}")
            self.data["base"] = initialized["head"]
            result = self.bag({"operation": "change_begin", "arguments": {"intent": self.data["conversation"][0]["text"]}})
            if result.get("status") != "succeeded":
                raise RuntimeError(f"CHANGE_BEGIN_FAILED: {result}")
        self.persist()

    def bag(self, arguments):
        if self.arm == "A":
            raise AccessDenied("TOOL_NOT_ALLOWED")
        if self.data["hidden"]:
            return {"status": "INCOMPLETE", "code": "REQUIRED_SOURCE_UNAVAILABLE", "acceptance_allowed": False}
        request = dict(arguments)
        if request.get("operation") == "change_begin" and self.data.get("change_id"):
            raise AccessDenied("CHANGE_ALREADY_OPEN")
        request["protocol"] = "bagaev-protocol/1"
        if request.get("change_id", self.data.get("change_id")) != self.data.get("change_id"):
            raise AccessDenied("FOREIGN_CHANGE")
        if request["operation"] != "change_begin" and self.data.get("change_id"):
            request.setdefault("change_id", self.data["change_id"])
        if request["operation"] in {"change_begin", "contract_update", "apply", "verify", "rebase", "accept", "abandon"}:
            request.setdefault("idempotency_key", f"harness-action-{len(self.journal.rows):08d}")
            if request["operation"] != "change_begin":
                request.setdefault("expected_work_revision", self.data["work_revision"])
        response, elapsed = self.sandbox.call(self.arm, "op", request=request)
        self.data["tool_seconds"] += elapsed
        # Полный исходный запрос и ответ остаются в журнале, включая внутренний SourceEdit от write.
        self.journal.append("protocol", request=request, response=response, elapsed_seconds=elapsed)
        if response.get("status") == "succeeded":
            for key in ("change_id", "work_revision"):
                if key in response:
                    self.data[key] = response[key]
            if request["operation"] == "accept":
                self.data["accepted"] = True
                self.data["acceptance_receipt"] = response
                self.data["accepted_files"] = manifest(self.app)
        return response

    def context(self):
        return self.data["conversation"]

    def budget_reason(self):
        limits = self.data["limits"]
        context_bytes = len(encoded(self.context()))
        return ("TURN_LIMIT" if self.data["turns"] >= limits["turns"] else
                "WALL_TIME_LIMIT" if time.time() - self.data["created_at"] >= limits["wall_seconds"] else
                "CONTEXT_LIMIT" if context_bytes > limits["context_token_upper_bound"] else
                "TOTAL_TOKEN_UPPER_BOUND" if self.data["context_bytes_total"] + context_bytes > limits["total_token_upper_bound"] else None)

    def call(self, tool: str, arguments=None):
        arguments = arguments or {}
        if self.data["status"] in TERMINAL:
            return {"status": self.data["status"], "code": "SESSION_TERMINAL"}
        limits = self.data["limits"]
        context_bytes = len(encoded(self.context()))
        context_path = self.control / "contexts" / f"{len(self.journal.rows) + 1:06d}.json"
        save(context_path, self.context())
        reason = self.budget_reason()
        if reason:
            response = {"status": "BUDGET_STOP", "code": reason}
        else:
            self.data["turns"] += 1
            self.data["context_bytes_total"] += context_bytes
            self.sandbox.tool_seconds = min(limits["tool_seconds"],
                                            max(0.001, limits["wall_seconds"] - (time.time() - self.data["created_at"])))
            try:
                response = self.dispatch(tool, arguments)
            except AccessDenied as exc:
                response = {"status": "DENIED", "code": str(exc)}
            except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
                response = {"status": "ERROR", "code": "TOOL_ERROR", "detail": str(exc)[:300]}
        raw = encoded(response)
        if len(raw) > limits["tool_output_bytes"]:
            save(self.control / f"oversize-{len(self.journal.rows):06d}.json", response)
            response = {"status": "INCOMPLETE", "code": "TOOL_OUTPUT_LIMIT", "bytes": len(raw), "sha256": sha(raw)}
        if response.get("status") in ("ERROR", "BUDGET_STOP"):
            self.data["status"] = response["status"]
        self.journal.append("tool", tool=tool, arguments=arguments, response=response, context_sha256=sha(encoded(self.context())),
                            context_bytes=context_bytes, context_file=str(context_path.relative_to(self.control)), turns=self.data["turns"])
        self.data["conversation"].extend([{"role": "tool_call", "tool": tool, "arguments": arguments},
                                          {"role": "tool_result", "response": response}])
        self.persist()
        return response

    def dispatch(self, tool, args):
        if self.data["accepted"] and (tool in ("write", "accept") or tool == "bag" and args.get("operation") in
                                      {"change_begin", "contract_update", "apply", "verify", "rebase", "accept", "abandon"}):
            raise AccessDenied("DECISION_FINAL")
        if tool == "list":
            return {"files": [p for p in manifest(self.app) if p not in self.data["hidden"]]}
        if tool == "read":
            path = self.path(args["path"])
            data = path.read_bytes()
            if len(data) > self.data["limits"]["tool_output_bytes"]:
                return {"status": "INCOMPLETE", "code": "TOOL_OUTPUT_LIMIT", "bytes": len(data), "sha256": sha(data)}
            return {"path": args["path"], "text": data.decode("utf-8"), "sha256": sha(data)}
        if tool == "search":
            query = args["query"]
            if not isinstance(query, str) or len(query) > 256:
                raise AccessDenied("QUERY_INVALID")
            matches = []
            for rel in manifest(self.app):
                if rel in self.data["hidden"]:
                    continue
                for number, line in enumerate(self.path(rel).read_text(encoding="utf-8").splitlines(), 1):
                    if query in line:
                        matches.append({"path": rel, "line": number, "text": line})
            return {"matches": matches}
        if tool == "write":
            path = self.path(args["path"], write=True)
            text = args["text"]
            if not isinstance(text, str) or len(text.encode()) > self.data["limits"]["write_bytes"]:
                raise AccessDenied("WRITE_SIZE_LIMIT")
            previous = path.read_bytes() if path.exists() else None
            if args.get("expected_sha256") != (sha(previous) if previous is not None else None):
                return {"status": "DENIED", "code": "STALE_SOURCE"}
            if self.arm != "A":
                item = {"path": args["path"], "create": text} if previous is None else {
                    "path": args["path"], "base_sha256": sha(previous), "whole_file": text}
                return self.bag({"operation": "apply", "arguments": {"source_edit": {"files": [item]}}})
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            return {"status": "WRITTEN", "sha256": sha(path.read_bytes())}
        if tool in ("check", "test"):
            if self.data["hidden"]:
                return {"status": "INCOMPLETE", "code": "REQUIRED_SOURCE_UNAVAILABLE", "acceptance_allowed": False}
            result, elapsed = self.sandbox.call(self.arm, tool)
            self.data["tool_seconds"] += elapsed
            return result
        if tool == "bag":
            return self.bag(args)
        if tool == "accept":
            if self.data["hidden"]:
                return {"status": "INCOMPLETE", "code": "REQUIRED_SOURCE_UNAVAILABLE", "acceptance_allowed": False}
            if self.arm != "A":
                return self.bag({**args, "operation": "accept"})
            response = git_adapter(self.repo).accept(self.app, self.control / "git", args.get("expected_head", self.data["base"]))
            self.data["accepted"] = response.get("status") == "accepted"
            self.data["acceptance_receipt"] = response
            if self.data["accepted"]:
                self.data["accepted_files"] = manifest(self.app)
            return response
        if tool == "resume":
            if self.arm != "A":
                return self.bag({"operation": "work_resume", "arguments": args})
            return {"base": self.data["base"], "files": manifest(self.app), "open_obligations": self.data["open_obligations"],
                    "note": "чеклист исполнителя; не результат анализа графа"}
        raise AccessDenied("TOOL_NOT_ALLOWED")

    def hide_export(self):
        rel = "blog/export.bag" if self.arm == "C" else "src/export.ts"
        source = self.path(rel)
        data = source.read_bytes()
        (self.control / "withheld").mkdir(exist_ok=True)
        source.replace(self.control / "withheld" / source.name)
        self.data["hidden"].append(rel)
        self.journal.append("hook", case="C12", path=rel, sha256=sha(data), policy="block_transitive_tools")
        self.persist()
        return {"case": "C12", "path": rel, "sha256": sha(data)}

    def reset_context(self, old_session, new_session):
        durable = {key: self.data.get(key) for key in ("arm", "base", "change_id", "work_revision", "open_obligations")}
        self.data["conversation"] = self.data["conversation"][:2] + [{"role": "checkpoint", "data": durable}]
        self.journal.append("session_reset", case="C06", old_session=old_session, new_session=new_session, durable=durable)
        self.persist()

    def finish(self, reason="SCRIPTED_VALIDATION_ONLY"):
        if self.data["status"] == "READY":
            self.data["status"] = "INCOMPLETE"
        self.journal.append("finished", status=self.data["status"], reason=reason, accepted=self.data["accepted"])
        self.persist()
        save(self.control / "result.json", {key: self.data[key] for key in
             ("arm", "provider", "pilot_status", "status", "research_attempt", "llm_measurements", "turns",
              "tool_seconds", "context_bytes_total", "accepted", "files", "journal_tail")})


class ScriptedProvider:
    def __init__(self, repo: Path):
        argv = base_command() + ["--ro-bind", str(repo / "pilot/harness/provider.py"), "/provider.py",
                                  "--", "/usr/bin/python3", "-I", "/provider.py"]
        self.process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, env={"PATH": "/usr/bin:/bin"})
        ready = self.process.stdout.readline()
        if not ready:
            raise RuntimeError("SCRIPTED_PROVIDER_START_FAILED")
        self.session = json.loads(ready)["session"]

    def action(self, session: Session, action: dict):
        self.process.stdin.write(json.dumps({"context": session.context(), "next_action": action}, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        response = json.loads(self.process.stdout.readline())
        if response["session"] != self.session:
            raise RuntimeError("PROVIDER_SESSION_MISMATCH")
        return response["action"]

    def kill(self):
        self.process.kill()
        self.process.wait(timeout=5)
        for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
            pipe.close()


def live_provider(*args, **kwargs):
    raise RuntimeError("LIVE_DISABLED: exact Claude model, budget, freeze и writability-v2 ещё не закреплены")
