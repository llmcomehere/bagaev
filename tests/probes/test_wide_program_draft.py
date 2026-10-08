"""Detached form5 function additions/replacements with unchanged old modes."""
from pathlib import Path
import copy,hashlib,json,subprocess,sys,tempfile,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_draft as e
import bagaev_record_export as export
CASES=json.loads((T/'examples/probes/wide-program-draft/cases.json').read_bytes())
class WideDraft(unittest.TestCase):
    def setUp(self):self.c=CASES['5'];self.raw=self.c['original'];self.candidate=self.c['candidate']
    def make(self,source=None,**kwargs):
        source=self.candidate if source is None else source
        target=kwargs.get('target',e.digest(e.form.decode(source)))
        return e.draft(self.raw,source,base_sha256=kwargs.get('base',self.c['base']),target_sha256=target)
    def test_literal_graph_scope_and_detachment(self):
        p=self.make();self.assertEqual(p['program'],self.c['expected']);self.assertEqual(p['delta'],{'add':['plus_one'],'replace':['main']});self.assertEqual(p['schema'],'bagaev-record-draft/2');self.assertFalse(p['semantic_check']);self.assertFalse(p['execution_admission'])
        p['program']['functions']['main']['body'][1]='changed';self.assertEqual(self.make()['program'],self.c['expected'])
        wrong=self.candidate.replace('= x+1','= 0');self.assertEqual(self.make(wrong)['program']['functions']['plus_one']['body'],['int',0])
        with self.assertRaises(e.DraftError):export.export_source(self.raw,self.make(),base_sha256=self.c['base'],target_sha256=self.c['target'],form_version='5')
    def test_multiple_replacements_sorted(self):
        old='bagaev record-form/5; program { entry z; fn z() -> Int64 = 1; fn a() -> Int64 = 2; }';new=old.replace('= 1','= 3').replace('= 2','= 4')
        p=e.draft(old,new,base_sha256=e.digest(e.form.decode(old)),target_sha256=e.digest(e.form.decode(new)));self.assertEqual(p['delta'],{'add':[],'replace':['a','z']})
    def test_pins_and_refusals(self):
        for key in ['base','target']:
            for value in ['0'*64,'X'*64,False]:
                with self.assertRaises(e.DraftError):self.make(**{key:value})
        with self.assertRaises(e.DraftError) as err:e.draft(self.raw,'invalid',base_sha256='0'*64,target_sha256=self.c['target'])
        self.assertEqual(err.exception.code,'DRAFT_BASE')
        for source in [self.raw,self.raw+'\n',self.candidate.replace('entry main','entry plus_one'),self.candidate.replace('program {','program { record Extra { x: Int64 };'),self.candidate.replace('fn main(x: Int64)','fn main(y: Int64)'),self.candidate.replace('fn main(x: Int64) -> Int64 = plus_one(x);','')]:
            with self.assertRaises(e.DraftError):self.make(source)
    def test_batch_helper_extraction_literal_scope(self):
        root=T/'examples/probes';old=(root/'inventory-batch-change/BatchLimited.bagaev').read_text();new=(root/'wide-program-draft/BatchWithHelper.bagaev').read_text()
        base='b4755a73e1090e2b4ed563f42c29250dc759c5b1224d3c5765a239cb6584351e';target='bfdc00afd4771e5ce8d3301b788bcc969c9d449a193e05fa0767640d1d2b560b'
        p=e.draft(old,new,base_sha256=base,target_sha256=target)
        self.assertEqual(p['delta'],{'add':['receipts_total'],'replace':['batch_apply']});self.assertFalse(p['semantic_check']);self.assertFalse(p['execution_admission'])
        before=e.form.decode(old);restored=copy.deepcopy(p['program']);helper=restored['functions'].pop('receipts_total')
        self.assertEqual(helper['params'],[['receipts','Receipts']]);self.assertEqual(helper['result'],'Int64')
        argument=['field',['use','done'],'receipts'];calls=[]
        def substitute(x):
            if x==['arg','receipts']:return copy.deepcopy(argument)
            return [substitute(y) for y in x] if isinstance(x,list) else x
        def inline(x):
            if isinstance(x,list) and x[:2]==['call','receipts_total']:
                self.assertEqual(x[2:],[argument]);calls.append(x);return substitute(helper['body'])
            return [inline(y) for y in x] if isinstance(x,list) else x
        restored['functions']['batch_apply']['body']=inline(restored['functions']['batch_apply']['body'])
        self.assertEqual(len(calls),1);self.assertEqual(restored,before)
        # Structural inlining is not work equivalence or a runtime check.
        self.assertEqual(hashlib.sha256((root/'inventory-batch-change/cases.json').read_bytes()).hexdigest(),'986ddffa275848e609ed3dfc69650b0b03b50d4bf63dee7e17ce80ef3f300e7b')
    def test_cli_legacy_and_form5(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory)
            for ver,c in CASES.items():
                old=d/('old'+ver);new=d/('new'+ver);out=d/('out'+ver);old.write_text(c['original']);new.write_text(c['candidate']);args=[sys.executable,'-B',str(T/'tools/record_draft.py'),str(old),str(new),'--form',ver,'--base',c['base'],'--target',c['target'],'--output',str(out)]
                p=subprocess.run(args,capture_output=True,timeout=10);self.assertEqual(p.returncode,0,p.stdout);self.assertEqual(p.stderr,b'');raw=out.read_bytes();v=json.loads(raw)
                if ver!='5':self.assertEqual(hashlib.sha256(raw).hexdigest(),c['packet_sha256']);self.assertEqual(json.loads(p.stdout),c['receipt'])
                else:self.assertEqual(v,self.make())
                self.assertEqual(subprocess.run(args,capture_output=True,timeout=10).returncode,2);self.assertEqual(out.read_bytes(),raw);self.assertEqual(old.read_text(),c['original']);self.assertEqual(new.read_text(),c['candidate'])
            p=subprocess.run([sys.executable,'-B',str(T/'tools/record_draft.py'),'missing','missing','--form','3','--base','0'*64,'--target','0'*64,'--output',str(d/'unused')],capture_output=True,timeout=10);self.assertEqual(p.returncode,2);self.assertEqual(json.loads(p.stdout)['error']['code'],'TOOL_USAGE')
if __name__=='__main__':unittest.main()
