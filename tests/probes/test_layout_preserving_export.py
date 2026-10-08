"""Exact-layout focused export tests; no execution of the changed program."""
from pathlib import Path
import json,sys,hashlib,copy,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_export as e
import bagaev_record_wide_spans as spans
B=T/'examples/probes/inventory-batch';C=T/'examples/probes/inventory-batch-change'
class LayoutExport(unittest.TestCase):
    def setUp(self):
        self.raw=(B/'Batch.bagaev').read_bytes();self.pins=json.loads((C/'pins.json').read_bytes());self.fragment=(C/'BatchLimited.fragment.bagaev').read_bytes();self.target=json.loads((C/'program.json').read_bytes())
        self.packet=e.wide.replace(self.raw,self.fragment,base_sha256=self.pins['base'],function_sha256=self.pins['function'])
    def emit(self,raw,packet=None,**changes):
        args=dict(base_sha256=self.pins['base'],target_sha256=self.pins['target'],source_sha256=hashlib.sha256(raw).hexdigest());args.update(changes)
        return e.export_source_preserving_layout(raw,self.packet if packet is None else packet,**args)
    def test_all_frozen_layouts(self):
        comments=self.raw.replace(b'program {','program {\n// global Ж note'.encode(),1).replace(b'-> BatchOutcome =\n    let size',b'-> BatchOutcome =\n    // leading body note\n    let size',1).replace(b'let size = option.or(json.len(orders), 0) in\n',b'let size = option.or(json.len(orders), 0) in\n    // replaced-body-note\n',1)
        cases={'lf':self.raw,'comments':comments,'crlf':comments.replace(b'\n',b'\r\n'),'lazy':(B/'Batch.lazy.bagaev').read_bytes(),'named':e.wide.form.encode_named(e.wide.form.decode(self.raw))}
        observed={x['id']:x for x in json.loads((T/'examples/probes/layout-preserving-export/observations.json').read_bytes())['observations']}
        saved=copy.deepcopy(self.packet)
        for name,raw in cases.items():
            out=self.emit(raw);self.assertEqual(e.wide.form.decode(out),self.target)
            rows=[next(x for x in spans.source_map(s)['locations'] if x['program_pointer']=='/program/functions/batch_apply/body') for s in [raw,out]];old,new=rows
            self.assertEqual(raw[:old['start_byte']],out[:new['start_byte']]);self.assertEqual(raw[old['end_byte']:],out[new['end_byte']:])
            self.assertEqual(hashlib.sha256(raw).hexdigest(),observed[name]['input_sha256']);self.assertEqual(hashlib.sha256(out).hexdigest(),observed[name]['output_sha256'])
            canonical=e.export_source(raw,self.packet,base_sha256=self.pins['base'],target_sha256=self.pins['target'],form_version='5');self.assertEqual(hashlib.sha256(canonical).hexdigest(),'8caccd806134b0a96cf10492e3aac5ac14a18212f0e2cb4303feea7187dc8e88')
        self.assertEqual(self.packet,saved)
    def test_stale_pins_and_packet_scope(self):
        for key in ['source_sha256','base_sha256','target_sha256']:
            with self.assertRaises(e.DraftError):self.emit(self.raw,**{key:'0'*64})
        bad=copy.deepcopy(self.packet);bad['semantic_check']=True
        with self.assertRaises(e.DraftError):self.emit(self.raw,bad)
        bad=copy.deepcopy(self.packet);bad['program']['functions']['sku_ok']['body']=['bool',False];bad['target']=e.digest(bad['program'])
        with self.assertRaises(e.DraftError):self.emit(self.raw,bad,target_sha256=bad['target'])
    def test_output_bound(self):
        raw=self.raw+b'\n//'+b'a'*(e.wide.form.old.BYTE_LIMIT-len(self.raw)-3)
        with self.assertRaises(e.DraftError) as caught:self.emit(raw)
        self.assertEqual(caught.exception.code,'EXPORT_BOUNDS')
if __name__=='__main__':unittest.main()
