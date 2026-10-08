"""Data-only form5 literal boundary regression; no runtime dispatch."""
from pathlib import Path
import sys,json,unittest
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/wide-record-literals'
sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_form as wide
import bagaev_record_json_form as narrow
import bagaev_record_wide_format as formatting


class LiteralTests(unittest.TestCase):
    def test_frozen_boundaries_and_graphs(self):
        for c in json.loads((D/'cases.json').read_bytes()):
            with self.subTest(case=c['id']):
                if not c['ok']:
                    with self.assertRaises(wide.FormError) as err:
                        wide.decode(c['source'])
                    self.assertEqual(err.exception.code,c['reason'])
                    continue
                value=wide.decode(c['source'])
                self.assertEqual(value['functions']['main']['body'],
                                 ['records.list','Items']+[['record','Item',['int',i]] for i in range(c['count'])])
                self.assertEqual(value['lists']['Items']['capacity'],c['capacity'])
                self.assertEqual(wide.decode(wide.encode(value)),value)
                pretty=formatting.format_source(c['source'])
                self.assertEqual(wide.decode(pretty),value)
                self.assertEqual(formatting.format_source(pretty),pretty)

    def test_accepted_sixteen_item_sum_graph(self):
        expected=json.loads((T/'examples/probes/native-wide-qualification/sum.invocation.json').read_bytes())['program']
        self.assertEqual(wide.decode((D/'sum-before-fix.bagaev').read_bytes()),expected)
        self.assertEqual(wide.decode(wide.encode(expected)),expected)

    def test_narrow_profile_unchanged(self):
        cases={c['id']:c for c in json.loads((D/'cases.json').read_bytes())}
        for name in ('four','five'):
            source=cases[name]['source'].replace('record-form/5','record-form/4').replace('capacity 16','capacity 4')
            if name=='four':
                graph=narrow.decode(source)
                self.assertEqual(narrow.decode(narrow.encode(graph)),graph)
            else:
                with self.assertRaises(narrow.FormError) as err:narrow.decode(source)
                self.assertEqual(err.exception.code,'FORM_BOUNDS')


if __name__=='__main__':unittest.main()
