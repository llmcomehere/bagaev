"""Check ordinary-native capture identities and full outcomes as data only."""
from pathlib import Path
import hashlib,json,unittest
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/inventory-native-baseline'


class BaselineData(unittest.TestCase):
    def test_source_identity(self):
        m=json.loads((D/'manifest.json').read_bytes())
        self.assertEqual(hashlib.sha256((D/'baseline.rs').read_bytes()).hexdigest(),m['source_sha256'])
        self.assertEqual(hashlib.sha256((T/m['shared_transport']['path']).read_bytes()).hexdigest(),m['shared_transport']['sha256'])
        self.assertFalse(m['measurement']);self.assertEqual(m['bagaev_calls'],0)

    def test_frozen_policy_values(self):
        frozen=json.loads((D/'frozen-inputs.json').read_bytes());expected={}
        for policy,folder in [('original','inventory-batch'),('total10','inventory-batch-change')]:
            raw=(T/'examples/probes'/folder/'cases.json').read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),frozen[policy]['sha256'])
            rows=json.loads(raw);self.assertEqual(len(rows),frozen[policy]['cases'])
            expected.update({(policy,row['id']):row['value'] for row in rows})
        observations=json.loads((D/'observations.json').read_bytes())
        self.assertEqual(len(observations),72);self.assertEqual({(x['policy'],x['id']) for x in observations},set(expected))
        for row in observations:self.assertEqual(row['output'],expected[row['policy'],row['id']])

    def test_named_refusal_captures(self):
        rows=json.loads((D/'refusals.json').read_bytes());self.assertEqual(len(rows),16)
        expected={'malformed':'BASELINE_TRANSPORT','oversized':'BASELINE_TRANSPORT','surrogate':'BASELINE_TEXT_PROFILE','long-text':'BASELINE_TEXT_PROFILE','bad-selector':'BASELINE_USAGE','bad-utf8':'BASELINE_TRANSPORT','symlink':'BASELINE_INPUT','directory':'BASELINE_INPUT'}
        self.assertEqual({(x['id'],x['opt']) for x in rows},{(name,opt) for name in expected for opt in (0,2)})
        for row in rows:self.assertEqual(row['error'],expected[row['id']])


if __name__=='__main__':unittest.main()
