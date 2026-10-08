"""Verify saved concrete mutant witnesses as data; no execution dispatcher."""
from pathlib import Path
import copy,hashlib,json,unittest
T=Path(__file__).resolve().parents[2]
D=T/'examples/probes/inventory-batch'


class Controls(unittest.TestCase):
    def test_five_single_site_witnesses(self):
        program=json.loads((D/'program.json').read_bytes())
        cases={x['id']:x for x in json.loads((D/'cases.json').read_bytes())}
        rows=json.loads((T/'examples/probes/inventory-batch-controls/observations.json').read_bytes())
        self.assertEqual(len(rows),5)
        self.assertEqual({x['id'] for x in rows},{'skip-first-stock','tentative-rollback','reverse-order','drop-prior-receipts','first-shape-only'})
        for row in rows:
            with self.subTest(mutant=row['id']):
                mutant=copy.deepcopy(program);obj=mutant;parts=row['pointer'].split('/')[1:]
                for part in parts[:-1]:obj=obj[int(part)] if isinstance(obj,list) else obj[part]
                key=int(parts[-1]) if isinstance(obj,list) else parts[-1]
                self.assertEqual(obj[key],row['before']);self.assertNotEqual(row['before'],row['after'])
                obj[key]=row['after']
                raw=json.dumps(mutant,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),row['mutant_program_sha256'])
                self.assertEqual(row['status'],'DETECTED_WRONG_VALUE')
                self.assertEqual(row['result']['status'],'success')
                self.assertEqual(row['expected_value'],cases[row['case']]['value'])
                self.assertNotEqual(row['result']['value'],row['expected_value'])
                obj[key]=row['before'];self.assertEqual(mutant,program)


if __name__=='__main__':unittest.main()
