"""Data-only reconstruction of expected JSON projection observations."""
from pathlib import Path
import base64,hashlib,json,unittest
T=Path(__file__).resolve().parents[2]
class JsonProjectionEvidence(unittest.TestCase):
    def test_complete_projected_values(self):
        m=json.loads((T/'examples/probes/native-result-json11/observations.json').read_bytes())
        count=0
        for folder in ['inventory-batch','inventory-batch-change']:
            d=T/'examples/probes'/folder
            cases=json.loads((d/'cases.json').read_bytes());wires=json.loads((d/'native-observations.json').read_bytes())
            observed=[x for x in m['observations'] if x['policy']==folder]
            self.assertEqual(len(observed),len(cases))
            for case,wire,row in zip(cases,wires,observed):
                self.assertEqual(row['id'],case['id']);self.assertEqual(wire['id'],case['id'])
                binding=base64.b64decode(wire['wire_base64'],validate=True)[24:56].hex()
                value=json.dumps(case['value'],sort_keys=True,ensure_ascii=False,separators=(',',':'))
                raw=('{"schema":"bagaev-native-result/11","source_pin":"sha256:'+binding+'","work":'+str(wire['work'])+',"value":'+value+'}').encode()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),row['json_sha256']);count+=1
        self.assertEqual(count,72);self.assertEqual(len(m['malformed_refusals']),14)
        self.assertEqual(m['native_calls'],0);self.assertFalse(m['measurement'])
        for path,digest in m['files'].items():self.assertEqual(hashlib.sha256((T/path).read_bytes()).hexdigest(),digest)
if __name__=='__main__':unittest.main()
