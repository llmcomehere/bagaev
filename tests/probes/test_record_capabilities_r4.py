"""Explicit current discovery with frozen previous revisions."""
from pathlib import Path
import hashlib,json,sys,unittest,re
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_capabilities as c
class CurrentDiscovery(unittest.TestCase):
    def test_revision3_bytes_and_legacy_exclusion(self):
        for form,digest in [('4','1440e3a1812eae88276665853070588e94713bbad03187768826fa841bbe48d4'),('5','6757d1be102a60b39d60f20c945db55e8fa1a63e76f1eccb2c13585ff8ec1fc3')]:
            value=c.describe_v3(form);raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode();self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
            for describe in [c.describe,c.describe_v2,c.describe_v3]:self.assertFalse({'bool.and','bool.or'} & {x['name'] for x in describe(form)['intrinsic_spellings']})
    def test_explicit_profile11_routes(self):
        v=c.describe_v4('5');self.assertEqual(v['schema'],'bagaev-record-capabilities/4');e=v['profile11_extensions'];self.assertTrue(e['supported'])
        self.assertTrue({'bool.and','bool.or'} <= {x['name'] for x in v['intrinsic_spellings']})
        self.assertTrue(e['lazy_boolean_forms']['both_branches_type_checked']);self.assertEqual(e['lazy_boolean_forms']['canonical_spelling'],'if')
        for name in ['prepared_reference','prepared_native','success_json_reader']:
            for key in ['source','library','guide']:
                if key in e[name]:self.assertTrue((T/e[name][key]).is_file())
        self.assertTrue(e['prepared_native']['evaluation_unsafe']);self.assertTrue(e['prepared_native']['separate_exact_kernel_admission_required'])
        self.assertFalse(e['success_json_reader']['source_or_kernel_execution']);self.assertFalse(e['success_json_reader']['origin_authenticated']);self.assertFalse(e['execution_admission']);self.assertFalse(e['performance_claim'])
        source=(T/e['prepared_reference']['source']).read_text()
        for key in ['prepare_source','prepare_arguments','evaluate']:self.assertTrue(re.search(r'\bpub fn '+re.escape(e['prepared_reference'][key])+r'(?:<[^>]+>)?\(',source),e['prepared_reference'][key])
    def test_no_profile_upgrade(self):
        value=c.describe_v4('4');self.assertEqual(value['program_schema'],'bagaev-typed-record/10');self.assertFalse(value['profile11_extensions']['supported']);self.assertNotIn('success_json_reader',value['profile11_extensions'])
if __name__=='__main__':unittest.main()
