#!/usr/bin/env python3
"""Offline structural checks for the private documentation workspace."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

REQUIRED = (
    "README.md", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md",
    "docs/foundation.md", ".github/CODEOWNERS",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/research_proposal.yml",
)
P0_IDS = tuple(f"P0-{number:02d}" for number in range(1, 11))
P0_ROW = re.compile(
    r"(?m)^\|\s*(P0-(?:0[1-9]|10))\s*\|([^|\n]+)\|([^|\n]+)\|\s*$"
)
P0_ROW_ERROR = "foundation must define exactly one non-empty table row for each P0-01-P0-10"
LOCAL_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


def check_foundation(foundation: Path) -> list[str]:
    errors: list[str] = []
    if foundation.is_file():
        text = foundation.read_text(encoding="utf-8")
        principles = re.findall(r"(?m)^### B(0[1-9]|1[0-8])\.", text)
        expected = {f"{number:02d}" for number in range(1, 19)}
        if len(principles) != 18 or set(principles) != expected:
            errors.append("foundation must define exactly 18 B01-B18 headings")
        p0_rows = P0_ROW.findall(text)
        p0_identifiers = [identifier for identifier, _, _ in p0_rows]
        empty_p0_columns = any(
            not events.strip() or not outcome.strip()
            for _, events, outcome in p0_rows
        )
        if (
            len(p0_rows) != 10
            or set(p0_identifiers) != set(P0_IDS)
            or empty_p0_columns
        ):
            errors.append(P0_ROW_ERROR)
    return errors


def check_local_links(root: Path) -> list[str]:
    errors: list[str] = []
    resolved_root = root.resolve()

    for document in root.rglob("*.md"):
        if ".git" in document.parts:
            continue
        for target in LOCAL_LINK.findall(document.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#") or target.startswith("mailto:"):
                continue
            path = (document.parent / target.split("#", 1)[0]).resolve()
            if not path.is_relative_to(resolved_root):
                errors.append(
                    f"local link escapes repository: {document.relative_to(root)} -> {target}"
                )
                continue
            if not path.exists():
                errors.append(f"broken local link: {document.relative_to(root)} -> {target}")
    return errors


def check(root: Path) -> list[str]:
    errors = [
        f"missing required file: {relative}"
        for relative in REQUIRED
        if not (root / relative).is_file()
    ]
    errors.extend(check_foundation(root / "docs/foundation.md"))
    errors.extend(check_local_links(root))
    return errors


def self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        errors = check(Path(directory))
        if not any(error.startswith("missing required file:") for error in errors):
            failures.append("missing-file case was not detected")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        root = base / "repository"
        root.mkdir()
        (base / "private.txt").write_text("synthetic\n", encoding="utf-8")
        (root / "README.md").write_text("[outside](../private.txt)\n", encoding="utf-8")
        errors = check_local_links(root)
        if not any(error.startswith("local link escapes repository:") for error in errors):
            failures.append("outside-root link was not rejected")

    with tempfile.TemporaryDirectory() as directory:
        foundation = Path(directory) / "foundation.md"
        headings = [f"### B{number:02d}. Principle" for number in range(1, 19)]
        rows = [f"| {identifier} | Event | Outcome |" for identifier in P0_IDS]
        foundation.write_text("\n".join(headings + [headings[0], *rows]), encoding="utf-8")
        errors = check_foundation(foundation)
        if "foundation must define exactly 18 B01-B18 headings" not in errors:
            failures.append("duplicate foundation heading was not rejected")

    with tempfile.TemporaryDirectory() as directory:
        foundation = Path(directory) / "foundation.md"
        headings = [f"### B{number:02d}. Principle" for number in range(1, 19)]
        rows = [f"| {identifier} | Event | Outcome |" for identifier in P0_IDS[:-1]]
        foundation.write_text("\n".join(headings + rows), encoding="utf-8")
        if P0_ROW_ERROR not in check_foundation(foundation):
            failures.append("missing P0 table row was not rejected")

    with tempfile.TemporaryDirectory() as directory:
        foundation = Path(directory) / "foundation.md"
        headings = [f"### B{number:02d}. Principle" for number in range(1, 19)]
        rows = [f"| {identifier} | Event | Outcome |" for identifier in P0_IDS]
        rows.append("| P0-01 | Duplicate event | Duplicate outcome |")
        foundation.write_text("\n".join(headings + rows), encoding="utf-8")
        if P0_ROW_ERROR not in check_foundation(foundation):
            failures.append("duplicate P0 table row was not rejected")

    with tempfile.TemporaryDirectory() as directory:
        foundation = Path(directory) / "foundation.md"
        headings = [f"### B{number:02d}. Principle" for number in range(1, 19)]
        rows = [f"| {identifier} | Event | Outcome |" for identifier in P0_IDS]
        rows[-1] = "| P0-10 |   | Outcome |"
        foundation.write_text("\n".join(headings + rows), encoding="utf-8")
        if P0_ROW_ERROR not in check_foundation(foundation):
            failures.append("empty P0 table column was not rejected")

    if failures:
        for failure in failures:
            print(f"self-test failed: {failure}", file=sys.stderr)
        return 1
    print("self-test passed: 6 negative cases rejected")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate bagaev documentation offline.")
    parser.add_argument("--self-test", action="store_true", help="exercise negative cases")
    if parser.parse_args().self_test:
        return self_test()
    errors = check(Path(__file__).resolve().parents[1])
    if errors:
        print("documentation validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("documentation validation passed (static structure only; not runtime or protocol proof)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
