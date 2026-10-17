"""Pure helper conformance for existing profile11 presence predicates."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT
DATA = ROOT / 'examples/probes/cpython-presence/cases.json'
sys.path.insert(0, str(ROOT / 'src'))
import bagaev_record_json_view as view
import bagaev_record_cpython_runtime as runtime
import bagaev_record_cpython_backend as backend

class Presence(unittest.TestCase):
    def setUp(self):
        raw = DATA.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), '6ab5616ad9a9691068b7e11376aab0741c5c5eab60397133a49e3c1793e020a7')
        self.oracle = json.loads(raw)
        self.layout = runtime.Layout({'schema':'bagaev-typed-record/11','records':{},'lists':{},'variants':{}})

    def frame(self):
        budget = runtime.Budget()
        return runtime.Frame(budget, '/program/functions/main/body', self.layout), budget

    def test_bounded_text_and_missing_without_surcharge(self):
        for case in self.oracle['json_cases']:
            with self.subTest(case=case['id']):
                data = case['repeat']['text'] * case['repeat']['count'] if 'repeat' in case else case['input']
                frame, budget = self.frame()
                operand = view.parse(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode())
                self.assertIs(frame.json_is_text(operand), case['expected'])
                self.assertEqual(budget.work, 1)
        frame, budget = self.frame()
        self.assertIs(frame.json_is_text(view.parse(b'[]').at(0)), False)
        self.assertEqual(budget.work, 1)

    def test_option_zero_extrema_and_projection(self):
        for value, expected in ((None,False),(0,True),(-(2**63),True),(2**63-1,True)):
            frame, budget = self.frame()
            self.assertIs(frame.option_is_some(runtime.Option(value)), expected)
            self.assertEqual(budget.work, 1)
        for case in self.oracle['projected_option_cases']:
            frame, budget = self.frame()
            child = runtime.Frame(budget, '/program/functions/main/body/1', self.layout)
            runtime.Frame(budget, '/program/functions/main/body/1/1', self.layout)
            operand = view.parse(case['arguments_raw'].encode()).at(0)
            self.assertIs(frame.option_is_some(child.json_int(operand)), case['expected'])
            self.assertEqual(budget.work, case['work'])

    def test_wrong_types_refuse_without_extra_work(self):
        for method, key in (('option_is_some','wrong_option_values'),('json_is_text','wrong_json_values')):
            for value in self.oracle['runtime_only'][key]:
                frame, budget = self.frame()
                with self.assertRaises(runtime.RuntimeAPIError) as caught:
                    getattr(frame,method)(value)
                self.assertEqual(caught.exception.code, self.oracle['runtime_only']['expected_code'])
                self.assertEqual(budget.work, self.oracle['runtime_only']['work_after_refusal'])

    def test_lowering_map_and_compiler_runtime_pin(self):
        self.assertEqual(backend.HELPERS['option.is_some'], ('option_is_some',1))
        self.assertEqual(backend.HELPERS['json.is_text'], ('json_is_text',1))
        module = ast.parse((SOURCE_ROOT / 'tools/record_source_cpython.py').read_text())
        assignments = [node for node in module.body if isinstance(node,ast.Assign)
                       and any(isinstance(target,ast.Name) and target.id == 'RUNTIMES' for target in node.targets)]
        self.assertEqual(len(assignments),1)
        pins = ast.literal_eval(assignments[0].value)
        for name,pin in pins.items():
            self.assertEqual(hashlib.sha256((SOURCE_ROOT/name).read_bytes()).hexdigest(),pin)

if __name__ == '__main__':
    unittest.main()
