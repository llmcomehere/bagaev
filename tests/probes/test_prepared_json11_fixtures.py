"""Verify derived prepared-call inputs against unchanged frozen application data."""
from pathlib import Path
import hashlib,json,unittest
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/prepared-json11'


class PreparedFixtures(unittest.TestCase):
    def test_exact_frozen_arguments(self):
        manifest=json.loads((D/'manifest.json').read_bytes())
        for policy,folder in [('original','inventory-batch'),('total10','inventory-batch-change')]:
            oracle=(T/'examples/probes'/folder/'cases.json').read_bytes()
            rows=json.loads(oracle);raw=(D/(policy+'.arguments.jsonl')).read_bytes()
            expected=('\n'.join(json.dumps([x['request']],ensure_ascii=False,separators=(',',':')) for x in rows)+'\n').encode()
            self.assertEqual(raw,expected)
            self.assertEqual(len(rows),manifest[policy]['cases'])
            self.assertEqual(hashlib.sha256(oracle).hexdigest(),manifest[policy]['oracle_sha256'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(),manifest[policy]['arguments_sha256'])


if __name__=='__main__':unittest.main()
