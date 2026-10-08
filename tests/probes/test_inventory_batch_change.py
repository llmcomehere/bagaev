"""Frozen changed-policy values, exact one-function scope and captured wire data."""
from pathlib import Path
import base64,copy,hashlib,importlib.util,json,sys,unittest
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/inventory-batch-change';B=T/'examples/probes/inventory-batch'
sys.path.insert(0,str(T/'src'));sys.path.insert(0,str(T/'tests/probes'))
import bagaev_record_wide_form as form
import bagaev_record_wide_function as edit
from bagaev_record_draft import digest
from native_wide_wire import decode
spec=importlib.util.spec_from_file_location('ordinary_change',D/'ordinary.py');ordinary=importlib.util.module_from_spec(spec);spec.loader.exec_module(ordinary)


class BatchChange(unittest.TestCase):
    def test_frozen_ordinary_values(self):
        raw=(D/'cases.json').read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),'986ddffa275848e609ed3dfc69650b0b03b50d4bf63dee7e17ce80ef3f300e7b')
        rows=json.loads(raw);self.assertEqual(len(rows),40)
        for row in rows:
            before=copy.deepcopy(row['request']);self.assertEqual(ordinary.batch(row['request']),row['value'],row['id']);self.assertEqual(row['request'],before)
        old={x['id']:x for x in json.loads((B/'cases.json').read_bytes())}
        current={x['id']:x for x in rows}
        self.assertEqual([name for name in old if old[name]!=current[name]],['sixteen-long-four'])

    def test_exact_replacement_and_old_input(self):
        pins=json.loads((D/'pins.json').read_bytes());source=(B/'Batch.bagaev').read_bytes();base=form.decode(source)
        result=edit.replace(source,(D/'BatchLimited.fragment.bagaev').read_bytes(),base_sha256=pins['base'],function_sha256=pins['function'])
        target=json.loads((D/'program.json').read_bytes())
        self.assertEqual(result['program'],target);self.assertEqual(result['target'],pins['target'])
        self.assertEqual(digest(base),pins['base']);self.assertEqual(digest(base['functions']['batch_apply']),pins['function'])
        self.assertEqual(form.decode((D/'BatchLimited.bagaev').read_bytes()),target)
        self.assertEqual([n for n in base['functions'] if base['functions'][n]!=target['functions'][n]],['batch_apply'])
        for key in ['schema','records','lists','variants','entry']:self.assertEqual(base[key],target[key])
        for base_pin,function_pin,code in [('0'*64,pins['function'],'FUNCTION_BASE'),(pins['base'],'0'*64,'FUNCTION_PIN')]:
            with self.assertRaises(edit.DraftError) as error:edit.replace(source,(D/'BatchLimited.fragment.bagaev').read_bytes(),base_sha256=base_pin,function_sha256=function_pin)
            self.assertEqual(error.exception.code,code)

    def test_captured_native_values(self):
        envelope=json.loads((D/'native.binding.json').read_bytes());source=envelope['binding']['source'].encode();pin=hashlib.sha256(source).digest();graph=json.loads(source)
        self.assertEqual(graph,json.loads((D/'program.json').read_bytes()));self.assertEqual(envelope['binding']['source_pin'],'sha256:'+pin.hex())
        rows={x['id']:x for x in json.loads((D/'cases.json').read_bytes())};observations=json.loads((D/'native-observations.json').read_bytes())
        self.assertEqual(len(observations),40);self.assertEqual({x['id'] for x in observations},set(rows))
        for item in observations:
            raw=base64.b64decode(item['wire_base64'],validate=True);self.assertEqual(len(raw),item['wire_bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),item['wire_sha256'])
            value,work=decode(graph,raw,pin);self.assertEqual(value,rows[item['id']]['value']);self.assertEqual(work,item['work'])


if __name__=='__main__':unittest.main()
