"""Data-only CLI observation consistency; no subprocess or kernel dispatch."""
from pathlib import Path
import json,base64,hashlib,unittest
T=Path(__file__).resolve().parents[2]
class CliEvidence(unittest.TestCase):
    def test_capture_consistency(self):
        m=json.loads((T/'examples/probes/native-result-json11/cli-observations.json').read_bytes())
        self.assertEqual(m['calls'],15);self.assertEqual(m['native_calls'],0);self.assertFalse(m['measurement'])
        self.assertEqual(m['source_sha256'],hashlib.sha256((T/'examples/probes/backend/rust/native_result_json11_main.rs').read_bytes()).hexdigest())
        rows={x['id']:x for x in m['observations']}
        for folder,index in [('inventory-batch',0),('inventory-batch',2),('inventory-batch-change',32)]:
            d=T/'examples/probes'/folder;case=json.loads((d/'cases.json').read_bytes())[index];wire=json.loads((d/'native-observations.json').read_bytes())[index]
            pin=base64.b64decode(wire['wire_base64'],validate=True)[24:56].hex();value=json.dumps(case['value'],ensure_ascii=False,sort_keys=True,separators=(',',':'))
            raw=('{"schema":"bagaev-native-result/11","source_pin":"sha256:'+pin+'","work":'+str(wire['work'])+',"value":'+value+'}\n').encode()
            self.assertEqual(rows[folder+'-'+str(index)]['stdout_sha256'],hashlib.sha256(raw).hexdigest())
        failures=[x for x in rows.values() if x['returncode']==2];self.assertEqual(len(failures),11)
        for row in failures:
            self.assertEqual(row['stdout_sha256'],hashlib.sha256(b'').hexdigest());self.assertEqual(json.loads(row['stderr'])['status'],'refused')
if __name__=='__main__':unittest.main()
