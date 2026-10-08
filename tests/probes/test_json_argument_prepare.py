"""Only data conversion. No language execution or subprocess launch."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import record_json_prepare as q


class JsonPreparationTests(unittest.TestCase):
    def test_literal_arguments(self):
        cases = json.loads((ROOT / "examples/probes/json-argument-prepare/cases.json").read_bytes())
        for row in cases:
            with self.subTest(case=row["id"]):
                raw = row["arguments_ascii"].encode()
                if row["ok"]:
                    q.arguments(raw, 1)
                else:
                    with self.assertRaises(q.transport.Refusal):
                        q.arguments(raw, 1)

    def test_depth_utf8_and_zero_arguments(self):
        q.arguments(b"[]", 0)
        q.arguments(b"[" * 128 + b"0" + b"]" * 128, 1)
        for raw in [b"[" * 129 + b"0" + b"]" * 129, b'["\xff"]', br'[{"\ud800":1}]']:
            with self.assertRaises(q.transport.Refusal):
                q.arguments(raw, 1)

    def test_lossless_both_profiles_and_exclusive_output(self):
        source = 'bagaev record-form/{form}; program {{ entry main; fn main(x: Json) -> Int64 = 0; }}'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for form in ("4", "5"):
                src = root / ("source" + form)
                src.write_text(source.format(form=form))
                args = root / ("args" + form)
                raw = b' \n[{"a":-1.2300e+400,"b":9223372036854775808,"c":-0}]\t'
                args.write_bytes(raw)
                out = root / ("out" + form)
                result = q.prepare([str(src), "--form", form, "--arguments", str(args), "--output", str(out)])
                wire = out.read_bytes()
                self.assertTrue(wire.endswith(b',"arguments":' + raw + b"}"))
                self.assertFalse(result["execution_admission"])
                self.assertIn(b'invocation/' + (b"10" if form == "4" else b"11"), wire)
                with self.assertRaises(q.transport.Refusal):
                    q.prepare([str(src), "--form", form, "--arguments", str(args), "--output", str(out)])
                self.assertEqual(wire, out.read_bytes())

    def test_old_numeric_route_unchanged(self):
        self.assertEqual(q.transport.parse_json(b"[1,-2]"), [1, -2])
        for raw in (b"[1.5]", b"[9223372036854775808]"):
            with self.assertRaises(q.transport.Refusal):
                q.transport.parse_json(raw)

    def test_typed_entry_and_frame_bounds_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src = root / "source"; args = root / "args"; out = root / "out"
            src.write_text("bagaev record-form/5; program { entry main; fn main(x: Int64) -> Int64 = x; }")
            args.write_text("[1]")
            with self.assertRaises(q.transport.Refusal) as err:
                q.prepare([str(src), "--form", "5", "--arguments", str(args), "--output", str(out)])
            self.assertEqual(err.exception.code, "JSON_ENTRY")
            self.assertFalse(out.exists())
            src.write_text("bagaev record-form/5; program { entry main; fn main(x: Json) -> Int64 = 0; }")
            args.write_bytes(b'["' + b"x" * (q.transport.LIMIT - 4) + b'"]')
            with self.assertRaises(q.transport.Refusal) as err:
                q.prepare([str(src), "--form", "5", "--arguments", str(args), "--output", str(out)])
            self.assertEqual(err.exception.code, "RECORD_BOUNDS")
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
