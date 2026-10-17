"""Literal tree roundtrips for the supported form4 data codec; no evaluation."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
import bagaev_record_json_form as form

LOOP = ['loop', 2, 'i', 'total', ['int', 0], ['add', ['use', 'total'], ['int', 1]]]
LET = ['let', 'n', ['int', 3], ['add', ['use', 'n'], ['int', 1]]]
IF = ['if', ['bool', True], ['int', 2], ['int', 3]]
MATCH = ['match', ['variant', 'Choice', 'Value', ['int', 4]], [['Value', 'n', ['use', 'n']]]]

def program(body, result='Int64'):
    return {'schema': 'bagaev-typed-record/10', 'records': {}, 'lists': {},
            'variants': {'Choice': {'Value': 'Int64'}}, 'entry': 'main',
            'functions': {'main': {'params': [], 'result': result, 'body': copy.deepcopy(body)}}}

class ControlOperands(unittest.TestCase):
    def test_literal_source_tree(self):
        source = b'bagaev record-form/4; program { variant Choice { Value: Int64 }; entry main; fn main() -> Int64 = (fold (2, 0) with (i, total) in total + 1) + 10; }'
        expected = program(['add', LOOP, ['int', 10]])
        self.assertEqual(form.decode(source), expected)
        self.assertEqual(form.decode(form.encode(expected)), expected)
        relocated = program(['loop', 2, 'i', 'total', ['int', 0], ['add', ['add', ['use', 'total'], ['int', 1]], ['int', 10]]])
        self.assertNotEqual(expected, relocated)

    def test_control_operand_positions(self):
        for control in (LOOP, LET, IF, MATCH):
            for op in ('add', 'sub', 'mul', 'lt'):
                for left, right in ((control, ['int', 10]), (['int', 10], control), (control, control)):
                    with self.subTest(control=control[0], op=op, left=left[0], right=right[0]):
                        expected = program([op, left, right], 'Bool' if op == 'lt' else 'Int64')
                        unchanged = copy.deepcopy(expected)
                        encoded = form.encode(expected)
                        self.assertEqual(expected, unchanged)
                        self.assertEqual(form.decode(encoded), expected)
                        self.assertEqual(form.encode(form.decode(encoded)), encoded)

    def test_nested_controls(self):
        expected = program(['mul', ['let', 'z', ['int', 1], ['add', LOOP, ['use', 'z']]], ['if', ['bool', False], LET, MATCH]])
        self.assertEqual(form.decode(form.encode(expected)), expected)

    def test_plain_arithmetic_bytes(self):
        expected = program(['add', ['int', 2], ['mul', ['int', 3], ['int', 4]]])
        literal = b'bagaev record-form/4;\nprogram {\n  variant Choice { Value: Int64 };\n\n  entry main;\n\n  fn main() -> Int64 = (2 + (3 * 4));\n}\n'
        self.assertEqual(form.encode(expected), literal)
        self.assertEqual(form.decode(literal), expected)

if __name__ == '__main__':
    unittest.main()
