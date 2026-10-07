"""Finite entry-example checks; not an LLM selection or productivity study."""
import contextlib
import io
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FirstChangeTests(unittest.TestCase):
    def test_complete_example_and_unchanged_files(self):
        files = list((ROOT / "examples" / "l0").glob("*.json"))
        files += list((ROOT / "examples" / "l0").glob("*.patch"))
        before = {p: p.read_bytes() for p in files}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            runpy.run_path(str(ROOT / "examples/l0/first_change.py"), run_name="__main__")
        self.assertEqual(output.getvalue(), '{"after":["blue","red"],"before":["red","blue","red"],"old_base_retry":"patch.stale"}\n')
        self.assertEqual(before, {p: p.read_bytes() for p in files})

    def test_same_selected_result_as_ordinary_python(self):
        module = runpy.run_path(str(ROOT / "examples/l0/first_change.py"))
        self.assertEqual(module["demonstrate"]()["after"], sorted(set(["red", "blue", "red"])))


if __name__ == "__main__":
    unittest.main()
