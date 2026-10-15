"""Independent literal profile6 history acceptance, frozen before implementation."""
import copy,contextlib,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tools'))
import bagaev_record_revisions as old
import bagaev_record_revisions_form6 as r
import record_revisions as cli
def raw(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def source(value):
    return ('bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = json.bool_or(x, '+value+'); }').encode()
def ast(value):
    body=['bool',value=='true'] if value in ('false','true') else ['int',int(value)]
    return {'schema':'bagaev-typed-record/12','records':{},'lists':{},'variants':{},'entry':'main',
        'functions':{'main':{'params':[['x','Json']],'result':'Bool','body':['json.bool_or',['arg','x'],body]}}}
def pins(value):return dict(source_sha256=sha(source(value)),program_sha256=sha(raw(ast(value))))
class Histories(unittest.TestCase):
    def first(self):return r.initialize(source('false'),**pins('false'))
    def add(self,p,value):return r.append(p,source(value),expected_package_sha256=sha(raw(p)),expected_head=p['head'],**pins(value))
    def refuse(self,code,fn,*args,**kwargs):
        with self.assertRaises(old.RevisionError) as error:fn(*args,**kwargs)
        self.assertEqual(error.exception.code,code)
    def test_literal_lineage_and_handoff(self):
        a=self.first();saved=copy.deepcopy(a)
        identity=dict(parent=None,form='record-form/6',**pins('false'))
        self.assertEqual(a['head'],sha(raw(identity)))
        b=self.add(a,'true');self.assertEqual(a,saved)
        self.assertEqual(b['head'],sha(raw(dict(parent=a['head'],form='record-form/6',**pins('true')))))
        fresh=r.loads(raw(b));self.assertEqual(r.checkout(fresh,a['head']),source('false'))
        self.assertEqual(r.checkout(fresh,b['head']),source('true'))
        back=self.add(b,'false');self.assertNotEqual(back['head'],a['head'])
        self.assertEqual(back['schema'],'bagaev-record-revisions/2')
        self.assertFalse(r.inspect(back)['semantic_check']);self.assertFalse(r.inspect(back)['execution_admission'])
        fresh['revisions'][0]['source']='changed';self.assertEqual(a,saved)
    def test_stale_noop_and_profile(self):
        a=self.first();b=self.add(a,'true')
        self.refuse('REVISION_STALE_HEAD',r.append,b,source('false'),expected_package_sha256=sha(raw(b)),expected_head=a['head'],**pins('false'))
        self.refuse('REVISION_STALE_PACKAGE',r.append,b,source('false'),expected_package_sha256=sha(raw(a)),expected_head=b['head'],**pins('false'))
        self.refuse('REVISION_NO_CHANGE',self.add,a,'false')
        layout=source('false')+b'\n'
        self.refuse('REVISION_NO_CHANGE',r.append,a,layout,expected_package_sha256=sha(raw(a)),expected_head=a['head'],source_sha256=sha(layout),program_sha256=pins('false')['program_sha256'])
        self.refuse('REVISION_PROFILE',old.loads,raw(a))
        p5=b'bagaev record-form/5; program { entry main; fn main() -> Int64 = 0; }'
        self.refuse('REVISION_SOURCE',r.initialize,p5,source_sha256=sha(p5),program_sha256='0'*64)
        bad=copy.deepcopy(a);bad['schema']='bagaev-record-revisions/1';bad['form']='record-form/5'
        self.refuse('REVISION_PROFILE',r.loads,raw(bad))
    def test_full_history_bounds_and_illtyped(self):
        a=self.first();b=self.add(a,'true');bad=copy.deepcopy(b)
        bad['revisions'][1]['source']='tampered'
        self.refuse('REVISION_SOURCE_PIN',r.checkout,bad,a['head'])
        p=a
        for i in range(1,16):p=self.add(p,'true' if i%2 else 'false')
        self.assertEqual(len(p['revisions']),16)
        self.refuse('REVISION_BOUNDS',self.add,p,'false')
        ill=r.initialize(source('0'),**pins('0'))
        self.assertEqual(r.checkout(ill,ill['head']),source('0'))
        self.assertFalse(ill['semantic_check']);self.assertFalse(ill['execution_admission'])
        self.refuse('REVISION_JSON',r.loads,b'{"x":false,"x":false}')
        self.refuse('REVISION_BOUNDS',r.loads,b' '*1048577)
        self.refuse('REVISION_BOUNDS',r.loads,b'['*33+b']'*33)
    def test_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);s=p/'source';s.write_bytes(source('false'))
            a=p/'a';b=p/'b';view=p/'view';checkout=p/'checkout'
            pinargs=lambda value:['--source-sha256',pins(value)['source_sha256'],'--program-sha256',pins(value)['program_sha256']]
            self.assertEqual(cli.main(['init',str(s),'--form','6','--output',str(a),*pinargs('false')]),0)
            first=a.read_bytes();s.write_bytes(source('true'))
            self.assertEqual(cli.main(['append',str(a),'--form','6','--source',str(s),'--output',str(b),'--head',json.loads(first)['head'],'--package-sha256',sha(first),*pinargs('true')]),0)
            self.assertEqual(cli.main(['inspect',str(b),'--form','6','--output',str(view)]),0)
            self.assertEqual(json.loads(view.read_bytes())['form'],'record-form/6')
            args=['checkout',str(b),'--form','6','--revision',json.loads(first)['head'],'--output',str(checkout)]
            self.assertEqual(cli.main(args),0);self.assertEqual(checkout.read_bytes(),source('false'))
            with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(cli.main(args),1)
            self.assertEqual(checkout.read_bytes(),source('false'));self.assertEqual(a.read_bytes(),first)
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(cli.main(['inspect',str(b),'--output',str(p/'wrong')]),1)
            self.assertEqual(errors.getvalue(),'REVISION_PROFILE\n');self.assertFalse((p/'wrong').exists())
    def test_import_guards_and_default_bytes(self):
        a=self.first();layout=source('false')+b'\n';bad=copy.deepcopy(a)
        identity=dict(form='record-form/6',parent=a['head'],source_sha256=sha(layout),program_sha256=pins('false')['program_sha256'])
        row={key:value for key,value in identity.items() if key!='form'}
        row.update(id=sha(raw(identity)),source=layout.decode());bad['revisions'].append(row);bad['head']=row['id']
        self.refuse('REVISION_NO_CHANGE',r.loads,raw(bad))
        for field,value,code in [('id','0'*64,'REVISION_ID'),('parent','0'*64,'REVISION_LINEAGE')]:
            bad=copy.deepcopy(a);bad['revisions'][0][field]=value
            self.refuse(code,r.loads,raw(bad))
        for flag in ('semantic_check','execution_admission'):
            bad=copy.deepcopy(a);bad[flag]=True;self.refuse('REVISION_ASSURANCE',r.loads,raw(bad))
        self.refuse('REVISION_UTF8',r.loads,b'"\\ud800"')
        for encoded in (b'0',b'1.0',b'NaN'):self.refuse('REVISION_JSON',r.loads,encoded)
        oversized=source('false')+b'\t'*600000
        self.assertLess(len(oversized),1048576)
        bad=copy.deepcopy(a);bad['revisions'][0]['source']=oversized.decode()
        self.assertGreater(len(raw(bad)),1048576)
        self.refuse('REVISION_BOUNDS',r.validate,bad)
        s5=b'bagaev record-form/5; program { entry main; fn main() -> Int64 = 0; }'
        a5={'schema':'bagaev-typed-record/11','records':{},'lists':{},'variants':{},'entry':'main',
            'functions':{'main':{'params':[],'result':'Int64','body':['int',0]}}}
        pins5=dict(source_sha256=sha(s5),program_sha256=sha(raw(a5)))
        expected=old.canonical(old.initialize(s5,**pins5))
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);(p/'source').write_bytes(s5)
            args=['init',str(p/'source'),'--output',str(p/'out'),'--source-sha256',pins5['source_sha256'],'--program-sha256',pins5['program_sha256']]
            self.assertEqual(cli.main(args),0);self.assertEqual((p/'out').read_bytes(),expected)
            invalid=list(args);invalid[1]=str(p/'missing');invalid+=['--form','7']
            with contextlib.redirect_stderr(io.StringIO()) as errors:self.assertEqual(cli.main(invalid),1)
            self.assertEqual(errors.getvalue(),'TOOL_USAGE\n');self.assertEqual((p/'out').read_bytes(),expected)
if __name__=='__main__':unittest.main()
