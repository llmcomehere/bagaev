"""Data-only consistency checks; does not compile or execute native code."""
from pathlib import Path
import base64,hashlib,json,struct,unittest
T=Path(__file__).resolve().parents[2]
class PreparedNativeEvidence(unittest.TestCase):
    def test_complete_frozen_frames(self):
        m=json.loads((T/'examples/probes/prepared-json11-native/manifest.json').read_bytes())
        self.assertEqual(m['native_calls'],288)
        self.assertEqual(m['source_preparations'],8)
        self.assertFalse(m['measurement'])
        for policy,folder in [('original','inventory-batch'),('total10','inventory-batch-change')]:
            observations=json.loads((T/'examples/probes'/folder/'native-observations.json').read_bytes())
            frames=bytearray()
            for row in observations:
                wire=base64.b64decode(row['wire_base64'],validate=True)
                self.assertEqual(hashlib.sha256(wire).hexdigest(),row['wire_sha256'])
                frames.extend(struct.pack('<I',len(wire)));frames.extend(wire)
            runs=[x for x in m['runs'] if x['policy']==policy]
            self.assertEqual({(x['optimization'],x['prefill']) for x in runs},{('O0',90),('O0',165),('O2',90),('O2',165)})
            for run in runs:
                self.assertEqual(run['calls'],len(observations))
                self.assertEqual(run['frames_sha256'],hashlib.sha256(frames).hexdigest())
    def test_exact_qualified_sources(self):
        m=json.loads((T/'examples/probes/prepared-json11-native/manifest.json').read_bytes())
        for path,digest in m['files'].items():
            self.assertEqual(hashlib.sha256((T/path).read_bytes()).hexdigest(),digest)
if __name__=='__main__':unittest.main()
