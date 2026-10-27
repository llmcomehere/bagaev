"""Проверки каркаса CLI эталона (Ф0). Запуск: `cd ref && python3 -m unittest discover -s tests -q`."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

REF = Path(__file__).resolve().parent.parent


def bag(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", "-m", "bagaev_ref", *args], cwd=REF,
                          capture_output=True, text=True, check=False)


class CliSkeleton(unittest.TestCase):
    def test_version_is_json(self):
        p = bag("version")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["impl"], "bagaev-ref")

    def test_conformance_exec_refuses_unimplemented_phase_honestly(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "case.json").write_text(json.dumps({"id": "eval/x", "expect": {"phase": "future", "outcome": "RETURNED"},
                                                           "files": []}), encoding="utf-8")
            p = bag("conformance-exec", "--case", d, "--json")
        self.assertEqual(p.returncode, 0, p.stderr)
        obs = json.loads(p.stdout)
        self.assertEqual((obs["outcome"], obs["code"], obs["phase"]), ("IMPLEMENTATION_STOP", "NOT_IMPLEMENTED", "future"))

    def test_conformance_exec_parse_phase(self):
        case = REF.parent / "conformance" / "cases" / "lex" / "bom"
        obs = json.loads(bag("conformance-exec", "--case", str(case), "--json").stdout)
        self.assertEqual(obs["outcome"], "PRELAUNCH")
        self.assertEqual(obs["diagnostics"][0]["code"], "SOURCE_BOM")

    def test_unknown_command_fails(self):
        self.assertNotEqual(bag("frobnicate").returncode, 0)


if __name__ == "__main__":
    unittest.main()
