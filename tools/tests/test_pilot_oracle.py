"""Нарушения CLI-контракта не превращаются в успех по последней строке stdout."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sp = importlib.util.spec_from_file_location('pilot_oracle_test', ROOT / 'pilot/authorship/oracle/run.py')
oracle = importlib.util.module_from_spec(sp)
sp.loader.exec_module(oracle)


class CliContract(unittest.TestCase):
    def result(self, script):
        with tempfile.TemporaryDirectory() as tmp:
            arm = oracle.Arm({'cli': [sys.executable, '-c', script]}, ROOT, Path(tmp), Path(tmp))
            result = arm.run('state')
            return result, arm.failures

    def test_nonzero_with_valid_json_is_failure(self):
        result, failures = self.result('print(\'{"status":"ok"}\'); raise SystemExit(1)')
        self.assertEqual(result['code'], 'CLI_EXIT')
        self.assertEqual(len(failures), 1)

    def test_only_one_response_object_is_accepted(self):
        for script in ('print(\'diagnostic\\n{"status":"ok"}\')', 'print(\'[]\')',
                       'print(\'{"status":"error","code":"BROKEN"}\')'):
            with self.subTest(script=script):
                result, failures = self.result(script)
                self.assertEqual(result['code'], 'CLI_RESPONSE')
                self.assertTrue(failures)

    def test_domain_refusal_is_processed_response(self):
        result, failures = self.result('print(\'{"status":"rejected","code":"PERMISSION_DENIED"}\')')
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(failures, [])


if __name__ == '__main__':
    unittest.main()
