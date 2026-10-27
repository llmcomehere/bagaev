"""Задачи пробника пишемости: эталон каждой задачи проходит проверку плеча C, а пустое решение — нет."""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "pilot" / "writability" / "run.py"


def load_run():
    spec = importlib.util.spec_from_file_location("bagaev_writability_run", RUN)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bagaev_writability_run"] = mod
    spec.loader.exec_module(mod)
    return mod


class WritabilityTasks(unittest.TestCase):
    def test_references_pass_and_empty_fails(self):
        run = load_run()
        tasks = run.all_tasks()
        self.assertEqual(len(tasks), 20)
        for t in tasks:
            ref = run.evaluate_c(t, run.tree_files(t["dir"] / "c" / "reference"))
            self.assertTrue(ref["passed"], (t["id"], ref.get("diagnostics", [])[:2], ref.get("ids_lost")))
            self.assertEqual(ref["fabricated_ids"], [], t["id"])
            ctx = run.tree_files(t["dir"] / "c" / "context").get(t["c_target"], b"")
            self.assertFalse(run.evaluate_c(t, {t["c_target"]: ctx})["passed"], t["id"])

    def test_stubs_fail_and_layout_does_not_matter(self):
        """Ревью m2: заглушка без работы с хранилищем не проходит; раскладка сигнатуры роли не играет."""
        run = load_run()
        t = {x["id"]: x for x in run.all_tasks()}
        stubs = {
            "W10": b"module shop.api\n\npub query price(name: String) -> Option<Int64> {\n  None\n}\n",
            "W11": b"module shop.api\n\npub type PriceError = enum {\n  Negative,\n  UnknownItem,\n}\n\n"
                   b"pub command set_price(name: String, value: Int64) -> Result<(), PriceError> {\n  Ok(())\n}\n",
        }
        for tid, src in stubs.items():
            self.assertFalse(run.evaluate_c(t[tid], {t[tid]["c_target"]: src})["passed"], tid)
        w16 = t["W16"]
        unchanged = run.tree_files(w16["dir"] / "c" / "context")["main.bag"]
        self.assertFalse(run.evaluate_c(w16, {"main.bag": unchanged})["passed"])
        ref = run.tree_files(t["W10"]["dir"] / "c" / "reference")["shop/api.bag"]
        column = ref.replace(b"price(name: String)", b"price(\n  name: String,\n)")
        self.assertTrue(run.evaluate_c(t["W10"], {"shop/api.bag": column})["passed"])

    def test_feedback_lines_follow_checked_file(self):
        run = load_run()
        w01 = {x["id"]: x for x in run.all_tasks()}["W01"]
        src = b"module main\n\nuse std.seq\n\npub fn sum(xs: Seq<Int64>) -> Int64 {\n  \"x\"\n}\n"
        rep = run.evaluate_c(w01, {"main.bag": src})
        msg = run.feedback_c(rep)
        self.assertIn('TYPE_MISMATCH', msg)
        self.assertIn('строка: "x"', msg)

    def test_answer_extraction(self):
        run = load_run()
        text = "Вот:\n```bagaev path=main.bag\nmodule main\n```\nи\n```ts path=a/b.ts\nexport {};\n```\n"
        self.assertEqual(run.extract_files(text), {"main.bag": b"module main\n", "a/b.ts": b"export {};\n"})


if __name__ == "__main__":
    unittest.main()
