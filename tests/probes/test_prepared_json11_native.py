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
    def test_reused_storage_captures(self):
        m=json.loads((T/'examples/probes/prepared-json11-native/reuse-observations.json').read_bytes())
        self.assertEqual(m['total_native_calls'],608)
        self.assertEqual(m['final_template_replay']['template_sha256'],hashlib.sha256((T/'tests/probes/backend/prepared_native11_reuse.rs.in').read_bytes()).hexdigest())
        self.assertEqual(sum(x['calls'] for x in m['runs']),576)
        self.assertEqual(sum(x['calls'] for x in m['failure_runs']),32)
        for policy,folder in [('original','inventory-batch'),('total10','inventory-batch-change')]:
            rows=json.loads((T/'examples/probes'/folder/'native-observations.json').read_bytes())
            wires=[base64.b64decode(x['wire_base64'],validate=True) for x in rows]
            frames=b''.join(struct.pack('<I',len(w))+w for w in wires+list(reversed(wires)))
            for run in [x for x in m['runs'] if x['policy']==policy]:
                self.assertEqual(run['frames_sha256'],hashlib.sha256(frames).hexdigest())
        for run in m['failure_runs']:
            wire=bytes.fromhex(run['wire_hex']);self.assertEqual(len(wire),32)
            self.assertEqual(run['frames_sha256'],hashlib.sha256((struct.pack('<I',32)+wire)*2).hexdigest())
    def test_exact_qualified_sources(self):
        m=json.loads((T/'examples/probes/prepared-json11-native/manifest.json').read_bytes())
        for path,digest in m['files'].items():
            self.assertEqual(hashlib.sha256((T/path).read_bytes()).hexdigest(),digest)
if __name__=='__main__':unittest.main()
