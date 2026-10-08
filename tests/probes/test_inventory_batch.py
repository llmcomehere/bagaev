"""Frozen values and captured-wire data checks; no native invocation."""
from pathlib import Path
import base64,copy,hashlib,importlib.util,json,sys,unittest
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/inventory-batch'
sys.path.insert(0,str(T/'src'));sys.path.insert(0,str(T/'tests/probes'))
import bagaev_record_wide_form as form
from native_wide_wire import decode
from native_wide_qualification import same
spec=importlib.util.spec_from_file_location('ordinary_batch',D/'ordinary.py');ordinary=importlib.util.module_from_spec(spec);spec.loader.exec_module(ordinary)


class BatchTests(unittest.TestCase):
    def test_literal_ordinary_oracle(self):
        raw=(D/'cases.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'aeda80170902abf7201d42a7117c26ef47d8d1269a209e743a189164a1aff4e8')
        rows=json.loads(raw);self.assertEqual(len(rows),32)
        for row in rows:
            with self.subTest(case=row['id']):
                before=copy.deepcopy(row['request'])
                self.assertEqual(ordinary.batch(row['request']),row['value'])
                self.assertEqual(row['request'],before)

    def test_source_and_predecessor_functions(self):
        graph=form.decode((D/'Batch.bagaev').read_bytes())
        self.assertEqual(graph,json.loads((D/'program.json').read_bytes()))
        self.assertEqual(form.decode(form.encode(graph)),graph)
        old=json.loads((T/'examples/probes/inventory-json-change/program.json').read_bytes())
        self.assertEqual(len(old['functions']),11)
        for name,function in old['functions'].items():self.assertEqual(graph['functions'][name],function)
        self.assertEqual(graph['entry'],'batch_main')
        self.assertEqual(sum(len(graph[k]) for k in ['records','lists','variants']),8)

    def test_captured_native_data(self):
        envelope=json.loads((D/'native.binding.json').read_bytes());source=envelope['binding']['source'].encode();pin=hashlib.sha256(source).digest()
        self.assertEqual(envelope['binding']['source_pin'],'sha256:'+pin.hex())
        graph=json.loads(source);self.assertEqual(graph,json.loads((D/'program.json').read_bytes()))
        rows={x['id']:x for x in json.loads((D/'cases.json').read_bytes())}
        observations=json.loads((D/'native-observations.json').read_bytes())
        self.assertEqual({x['id'] for x in observations},set(rows));self.assertEqual(len(observations),len(rows))
        for item in observations:
            raw=base64.b64decode(item['wire_base64'],validate=True)
            self.assertEqual(len(raw),item['wire_bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(),item['wire_sha256'])
            value,work=decode(graph,raw,pin)
            self.assertTrue(same(value,rows[item['id']]['value']))
            self.assertEqual(work,item['work'])


if __name__=='__main__':unittest.main()
