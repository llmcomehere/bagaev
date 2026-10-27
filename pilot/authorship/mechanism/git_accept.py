"""Обычная приёмка A: снимок файлов и атомарный Git compare-and-swap.

Компилятор/тесты вызываются отдельно; скрытый оракул не участвует в решении приёмки.
Git-хранилище живёт в state, вне доступного агенту приложения. Никаких remote/hooks.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

REF = "refs/heads/accepted"
IDENTITY = {"GIT_AUTHOR_NAME": "bagaev pilot", "GIT_AUTHOR_EMAIL": "pilot@bagaev.invalid",
            "GIT_COMMITTER_NAME": "bagaev pilot", "GIT_COMMITTER_EMAIL": "pilot@bagaev.invalid",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000", "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000"}


def git(state: Path, *args, data=None, index=None, check=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(IDENTITY, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    return subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, "--git-dir", str(Path(state) / "repo.git"), *args],
                          input=data, capture_output=True, env=env, check=check, timeout=60)


def sources(app: Path):
    for f in sorted(Path(app).rglob("*")):
        rel = f.relative_to(app)
        if any(p in (".git", ".bagaev", "node_modules", "__pycache__") for p in rel.parts):
            continue
        if f.is_symlink():
            raise ValueError(f"symlink вне снимка: {rel}")
        if f.is_file():
            yield rel.as_posix(), f.read_bytes()


def snapshot(app: Path, state: Path, parent: str | None) -> str:
    if parent is not None:
        if not isinstance(parent, str) or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", parent) is None:
            raise ValueError("expected_head — полный Git object ID")
        git(state, "cat-file", "-e", parent + "^{commit}")
    with tempfile.TemporaryDirectory(prefix="git-index-", dir=state) as tmp:
        index = Path(tmp) / "index"
        git(state, "read-tree", "--empty", index=index)
        for rel, raw in sources(Path(app)):
            blob = git(state, "hash-object", "-w", "--stdin", data=raw).stdout.strip().decode()
            git(state, "update-index", "--add", "--cacheinfo", "100644", blob, rel, index=index)
        tree = git(state, "write-tree", index=index).stdout.strip().decode()
    parents = ["-p", parent] if parent else []
    return git(state, "commit-tree", tree, *parents, data=b"pilot snapshot\n").stdout.strip().decode()


def init(app: Path, state: Path) -> str:
    state = Path(state).resolve()
    if (state / "repo.git").exists():
        raise FileExistsError(state / "repo.git")
    state.mkdir(parents=True, exist_ok=True)
    git(state, "init", "--bare")
    candidate = snapshot(Path(app), state, None)
    git(state, "update-ref", REF, candidate, "0" * len(candidate))
    return candidate


def head(state: Path) -> str:
    return git(Path(state), "rev-parse", "--verify", REF).stdout.strip().decode()


def accept(app: Path, state: Path, expected_head: str) -> dict:
    state = Path(state).resolve()
    candidate = snapshot(Path(app), state, expected_head)
    result = git(state, "update-ref", REF, candidate, expected_head, check=False)
    current = head(state)
    if result.returncode:
        if current != expected_head:
            return {"status": "blocked", "code": "STALE_BASE", "head": current, "candidate": candidate}
        raise RuntimeError(result.stderr.decode(errors="replace"))
    # Квитанция относится к нашему CAS; последующий конкурент может уже сменить head.
    return {"status": "accepted", "head": candidate, "candidate": candidate}


def advance_head(app: Path, state: Path) -> dict:
    return accept(app, state, head(state))
