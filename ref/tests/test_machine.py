"""MACHINE-1: примеры исполняются с вручную проверенными значениями, мост к CORE-0.1 совпадает,
пропускная способность не ниже плана Ф3.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))

from bagaev_ref.machine.runner import run_entry, run_tests  # noqa: E402


def load(root: Path):
    return [(f.relative_to(root).as_posix(), f.read_bytes()) for f in sorted(root.rglob("*.bag"))]


class Examples(unittest.TestCase):
    # Значения посчитаны вручную по исходникам examples/basics.
    EXPECTED = {"arithmetic": 56, "lists": 17, "maps": 402, "results": 42, "shapes": 16, "strings": 12}

    def test_basics_main(self):
        files = load(ROOT / "examples" / "basics")
        for mod, v in self.EXPECTED.items():
            obs = run_entry(files, f"{mod}.main")
            self.assertEqual(obs["outcome"], "RETURNED", (mod, obs))
            self.assertEqual(obs["value"], {"type": "Int64", "value": str(v)}, mod)

    def test_authorship_tests_pass(self):
        obs = run_tests(load(ROOT / "examples" / "authorship"))
        self.assertEqual(obs["counts"]["FAIL"] + obs["counts"]["ERROR"], 0, obs)
        self.assertGreaterEqual(obs["counts"]["PASS"], 1)


class Bridge(unittest.TestCase):
    def test_core01_agrees(self):
        spec = importlib.util.spec_from_file_location("bagaev_core01", ROOT / "conformance" / "bridges" / "core01.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["bagaev_core01"] = mod
        spec.loader.exec_module(mod)
        self.assertEqual(mod.main(["--generated", "40", "--json"]), 0)


class NormativeStdBodies(unittest.TestCase):
    def test_appendix_matches_std(self):
        """MCH-12: тела функций std высшего порядка в machine.md совпадают с интерфейсом эталона."""
        import re
        from bagaev_ref.sema.std import STD_SOURCES
        spec = (ROOT / "spec" / "runtime" / "machine.md").read_text(encoding="utf-8")
        block = spec.split("## Приложение A.")[1]
        for mod, names in (("std.seq", ["map", "map_from", "fold", "fold_from"]), ("std.option", ["map"]),
                           ("std.result", ["map", "map_error"])):
            for n in names:
                body = re.search(r"^(pub )?fn %s\b.*?^}$" % n, STD_SOURCES[mod], re.S | re.M).group(0)
                self.assertIn(body, block, f"{mod}.{n}")


class Throughput(unittest.TestCase):
    def test_at_least_plan(self):
        spec = importlib.util.spec_from_file_location("bagaev_bench", ROOT / "ref" / "bench" / "bench_machine.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        r = mod.measure()
        self.assertEqual(r["value"], 599997)
        self.assertGreater(r["transitions_per_second"], 300_000, r)


if __name__ == "__main__":
    unittest.main()
