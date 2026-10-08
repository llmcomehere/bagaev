"""Data-only discovery revision and old-output identity tests."""
import hashlib,json,sys,unittest
from pathlib import Path
T=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(T/'src'))
import bagaev_record_capabilities as caps


class Discovery(unittest.TestCase):
    def test_prior_bytes(self):
        expected={('4','1'):'8a121083b2414276e63bcd41027c2cfe58d4c697f66e2abd8c405f2687f5dff7',
                  ('4','2'):'c5d19dc8970245f54f6a573519c9fc4717c63c3197ca7e9c34950a43a7b5d04b',
                  ('5','1'):'0dacb0410fba589b37f51b5b21d78966b4fc667881631a121298da00d8147fce',
                  ('5','2'):'9eea24256dc88d9c80b20f727b62774583e0aad342744742bd0002cbc4b018c5'}
        for (form,revision),pin in expected.items():
            value=(caps.describe if revision=='1' else caps.describe_v2)(form)
            raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),pin)

    def test_wide_debugging(self):
        value=caps.describe_v3('5');m=value['source_debugging']
        self.assertTrue(m['supported'])
        self.assertEqual(value['schema'],'bagaev-record-capabilities/3')
        self.assertEqual(m['required_flags'],['--form','--program-pin','--output'])
        self.assertEqual(m['optional_flags'],['--source-sha256','--pointer'])
        self.assertEqual(m['map_schema'],'bagaev-record-source-map/1')
        self.assertEqual(m['checked_report_schema'],'bagaev-native-source-locations/1')
        for path in [m['map_tool'],m['checked_inspector_source'],m['guide']]:self.assertTrue((T/path).is_file())
        for key in ['map_semantic_check','native_output_authenticated','execution_admission']:self.assertFalse(m[key])
        self.assertEqual(m['map_bounds'],{'nodes':2048,'output_bytes':1048576})
        self.assertEqual(m['precision'],['exact-expression','enclosing-expression'])

    def test_narrow_has_no_upgrade(self):
        value=caps.describe_v3('4')
        self.assertFalse(value['source_debugging']['supported'])
        self.assertNotIn('record_source_map.py',value['data_tools'])
        self.assertEqual(value['program_schema'],'bagaev-typed-record/10')
        with self.assertRaises(caps.narrow.FormError):caps.describe_v3('3')


if __name__=='__main__':unittest.main()
