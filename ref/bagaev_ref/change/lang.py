"""Язык проекта CHANGE-1 (spec/protocol/agent-protocol.md §1, CHG-01а): проверка, извлечение графа, прогон тестов,
сущности для операций идентичности и смыслы для поиска.

Протокол, WorkState, свидетельства, приёмка и анализ влияния от языка не зависят: они работают на графе общей
схемы (spec/links/graph.schema.json) и записях тестов. Язык задаёт `bag project init` по файлам корня и хранит
в meta проекта (`language`):
- `bagaev` — эталон: CHECK-1, LINKS-1, тесты машины, `@id`;
- `typescript` — вариант B пилота (pilot/authorship/contract.md §4а): компилятор TypeScript, извлекатель
  pilot/authorship/links-ts/extract.ts, тесты `node --test`. Идентичность кода в TypeScript — имя; операции
  идентичности относятся к объявленным в JSDoc смысловым сущностям, контрактам и правилам.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from bagaev_ref.kernel import canonical as C

ROOT = Path(__file__).resolve().parents[3]


class Bagaev:
    name = "bagaev"
    exts = (".bag",)

    @property
    def extractor_rev(self) -> str:
        from bagaev_ref.links.extract import EXTRACTOR_REV
        return EXTRACTOR_REV

    def check(self, files: dict):
        """(контекст, None) или (None, диагностики) — CHECK-1."""
        from bagaev_ref.machine.runner import prepare
        project, prog, pre = prepare(sorted(files.items()))
        return ((project, prog), None) if pre is None else (None, pre.get("diagnostics", []))

    def extract(self, files: dict, ctx) -> dict:
        from bagaev_ref.links.extract import extract
        return extract(ctx[0], ctx[1], sorted(files.items()))

    def run_tests(self, files: dict) -> dict:
        from bagaev_ref.machine.runner import run_tests
        return run_tests(sorted(files.items()))

    def entities(self, files: dict):
        from bagaev_ref.change.identity import entities
        return entities(files)

    def meanings(self, files: dict) -> dict:
        """Полное имя смысловой сущности → (purpose, terms, not_about)."""
        from bagaev_ref.syntax.parser import parse
        out = {}
        for path, data in files.items():
            tree, _, _ = parse(data, path)
            if tree is None:
                continue
            for it in tree.items:
                d = it.decl
                if type(d).__name__ == "EntityDecl":
                    out[".".join(n.text for n in tree.module.path) + "." + d.name.text] = (d.purpose or "", list(d.terms),
                                                                                         list(d.not_about))
        return out

    assigns_ids = True


class TypeScript:
    """Проект TypeScript варианта B: `src/`, `test/`, `tsconfig.json`, `node-env.d.ts`, `package.json`."""
    name = "typescript"
    exts = (".ts", ".json")
    assigns_ids = False
    runner_suite = "runner:typescript"
    EXTRACTOR = ROOT / "pilot" / "authorship" / "links-ts" / "extract.ts"
    TSC = ROOT / "pilot" / "writability" / "node_modules" / "typescript" / "bin" / "tsc"

    @property
    def extractor_rev(self) -> str:
        return "links-ts@1+" + C.digest("extractor", "1", {"extract.ts": self.EXTRACTOR.read_bytes().hex()})[:16]

    def _tree(self, files: dict):
        tmp = Path(tempfile.mkdtemp(prefix="bag-ts-"))
        for rel, data in files.items():
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp / rel).write_bytes(data)
        return tmp

    def check(self, files: dict):
        if "tsconfig.json" not in files:
            return None, [{"code": "TS_PROJECT_INVALID", "phase": "type", "message": "нет tsconfig.json"}]
        tmp = self._tree(files)
        try:
            p = subprocess.run(["node", str(self.TSC), "-p", str(tmp / "tsconfig.json")], capture_output=True, text=True,
                               timeout=600)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if p.returncode == 0:
            return True, None
        diags = []
        for m in re.finditer(r"^(.+?)\((\d+),(\d+)\): error (TS\d+): (.*)$", p.stdout, re.M):
            f = Path(m.group(1))
            rel = f.relative_to(tmp).as_posix() if f.is_absolute() and f.is_relative_to(tmp) else m.group(1)
            diags.append({"code": m.group(4), "phase": "type", "file": rel, "line": m.group(2), "message": m.group(5)})
        return None, diags or [{"code": "TS_CHECK_FAILED", "phase": "type", "message": p.stdout[-300:]}]

    def extract(self, files: dict, ctx) -> dict:
        from bagaev_ref.links.extract import source_digest
        tmp = self._tree(files)
        try:
            p = subprocess.run(["node", "--no-warnings", str(self.EXTRACTOR), str(tmp)], capture_output=True, text=True,
                               timeout=600, check=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        import json
        data = json.loads(p.stdout)
        C.encode(data)                                   # BAG-CJSON-1: без чисел, только строки, списки, объекты
        rev = self.extractor_rev
        for e in data["edges"]:
            e["provenance"]["extractor"] = rev
        return dict(data, extractor_rev=rev, source=source_digest(sorted(files.items())))

    @staticmethod
    def test_runners(files: dict) -> dict:
        """Полный набор файлов, которые запускает runner, независимо от наличия именованных тестов."""
        return {f: files[f] for f in sorted(files) if f.startswith("test/") and f.endswith(".test.ts")}

    def run_tests(self, files: dict) -> dict:
        tmp = self._tree(files)
        out, runners = [], []
        try:
            for rel in self.test_runners(files):
                mod = rel[len("test/"):-len(".test.ts")].replace("/", ".")
                try:
                    p = subprocess.run(["node", "--no-warnings", "--test", "--test-reporter=tap", str(tmp / rel)],
                                       capture_output=True, text=True, timeout=600, cwd=tmp)
                except (OSError, subprocess.TimeoutExpired) as e:
                    runners.append({"file": rel, "status": "ERROR", "reason": type(e).__name__})
                    continue
                for m in re.finditer(r"^(not ok|ok) \d+ - (.+?)(?:[ \t]+#[ \t]*(SKIP|TODO)\b[^\n]*)?$",
                                     p.stdout, re.M | re.I):
                    status = m.group(3).upper() if m.group(3) else "PASS" if m.group(1).lower() == "ok" else "FAIL"
                    out.append({"test": f"test.{mod}.{m.group(2)}", "status": status})
                if p.returncode != 0:
                    # В TAP могут успеть появиться ok, а затем упасть загрузка/runner. Это отдельное
                    # противоречие прогона, даже если его not ok не соответствует узлу теста графа.
                    runners.append({"file": rel, "status": "ERROR", "reason": "runner-exit", "returncode": str(p.returncode)})
                else:
                    runners.append({"file": rel, "status": "PASS"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return {"phase": "test", "outcome": "ERROR" if any(r["status"] == "ERROR" for r in runners) else "TESTED",
                "tests": out, "runners": runners}

    def entities(self, files: dict):
        """Объявленные смысловые сущности, контракты и правила: ID — полное имя."""
        ctx, diags = self.check(files)
        if diags is not None and not any(d.get("file") for d in diags):
            return None, diags
        g = self.extract(files, ctx)
        out = {}
        for n in g["nodes"]:
            if n["kind"] in ("entity", "contract", "rule"):
                out.setdefault(n["id"], []).append((n["file"], n["kind"], n["name"]))
        return out, []

    def meanings(self, files: dict) -> dict:
        import json
        tmp = self._tree(files)
        try:
            p = subprocess.run(["node", "--no-warnings", str(self.EXTRACTOR), str(tmp), "--meanings"], capture_output=True,
                               text=True, timeout=600, check=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return {k: (v["purpose"], v["terms"], v["not_about"]) for k, v in json.loads(p.stdout).items()}


LANGS = {"bagaev": Bagaev(), "typescript": TypeScript()}


def detect(root: Path) -> str:
    """Язык корня: есть `*.bag` — bagaev; есть tsconfig.json и `*.ts` — typescript."""
    root = Path(root)
    if any(root.rglob("*.bag")):
        return "bagaev"
    if (root / "tsconfig.json").is_file() and any(root.rglob("*.ts")):
        return "typescript"
    return "bagaev"


def of(store):
    return LANGS[store.meta("language") or "bagaev"]
