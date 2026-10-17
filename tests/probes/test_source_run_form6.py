"""Independent form6 workflow fixtures with mocked reference capture only."""
import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import record_source_run as r
import record_run_verify as v
def fixtures():
    raw=(ROOT/'examples/probes/source-run-form6/cases.json').read_bytes()
    assert r.sha(raw)=='5dd8ec793309056d0d27f99b5b8b276d3cf16371e6067104892b50d1ceae9ed6'
    return json.loads(raw)
def prepare(base,case):
    source=base/'source.bagaev';arguments=base/'arguments.json';reference=base/'mock-reference'
    source.write_bytes(case['source'].encode());arguments.write_bytes(case['arguments'].encode());reference.write_bytes(b'not executed')
    return dict(source=source,arguments=arguments,reference=reference,source_sha256=r.sha(source.read_bytes()),
      arguments_sha256=r.sha(arguments.read_bytes()),reference_sha256=r.sha(reference.read_bytes()),output=base/'out')
def expected(meta,case,form='6'):
    profile='12' if form=='6' else '11';program=r.canonical(case['program']);stdout=r.canonical(case['expected'])+b'\n'
    invocation=('{"schema":"bagaev-typed-record-invocation/'+profile+'","program":').encode()+program+b',"arguments":'+case['arguments'].encode()+b'}'
    result=case['expected']
    receipt={'schema':'bagaev-record-source-run/2' if form=='6' else 'bagaev-record-source-run/1','status':'completed',
      'source_sha256':meta['source_sha256'],'arguments_sha256':meta['arguments_sha256'],'program_sha256':r.sha(program),
      'invocation_sha256':r.sha(invocation),'result_sha256':r.sha(stdout),'reference_sha256':meta['reference_sha256'],
      'runtime_status':result['status'],'reason':result['reason'],'location':result['location'],'work':result['work'],
      'reference_invoked':True,'execution_admission':False,'result_authentication':False,'application_expectation_checked':False}
    if form=='6':receipt['form']='record-form/6'
    files={'source.bagaev':case['source'].encode(),'arguments.json':case['arguments'].encode(),'program.json':program,
      'invocation.json':invocation,'reference.stdout':stdout,'reference.stderr':b'','receipt.json':r.canonical(receipt)}
    return receipt,files
class Form6Tests(unittest.TestCase):
    def make(self,base,case):
        meta=prepare(base,case);receipt,files=expected(meta,case)
        with patch.object(r.capture_tools,'capture',return_value=(0,files['reference.stdout'],b'')) as capture:
            actual=r.run_flow(**meta,form_version='6')
        capture.assert_called_once_with([str(meta['reference']),'run','--input',str(meta['output']/'invocation.json')])
        self.assertTrue(v.exact(actual,receipt));self.assertEqual({p.name:p.read_bytes() for p in meta['output'].iterdir()},files)
        return meta,receipt,files
    def test_literal_runs_and_reports(self):
        for case in fixtures()['cases']:
            with self.subTest(case=case['name']),tempfile.TemporaryDirectory() as d:
                meta,receipt,files=self.make(Path(d),case)
                with patch.object(r.capture_tools,'capture',side_effect=AssertionError('offline dispatch')):
                    report=v.verify(meta['output'],r.sha(files['receipt.json']))
                result=case['expected']
                want={'schema':'bagaev-record-run-verification/2','status':'consistent','form':'record-form/6',
                  'receipt_sha256':r.sha(files['receipt.json']),
                  **{key:receipt[key] for key in ('source_sha256','arguments_sha256','program_sha256','invocation_sha256','result_sha256')},
                  'claimed_reference_sha256':meta['reference_sha256'],'runtime_status':result['status'],
                  'reason':result['reason'],'location':result['location'],'work':result['work'],'fresh_run':False,
                  'reference_invoked':False,'result_authentication':False,'execution_admission':False,'application_expectation_checked':False}
                self.assertTrue(v.exact(report,want));self.assertEqual({p.name:p.read_bytes() for p in meta['output'].iterdir()},files)
    def test_form5_default_is_identical(self):
        case=json.loads((ROOT/'examples/probes/source-run-flow/cases.json').read_bytes())['real_cases'][0]
        with tempfile.TemporaryDirectory() as d:
            meta=prepare(Path(d),case);receipt,files=expected(meta,case,'5')
            for selection in ({},{'form_version':'5'}):
                meta['output']=Path(d)/('default' if not selection else 'explicit')
                with patch.object(r.capture_tools,'capture',return_value=(0,files['reference.stdout'],b'')):
                    self.assertTrue(v.exact(r.run_flow(**meta,**selection),receipt))
                self.assertEqual({p.name:p.read_bytes() for p in meta['output'].iterdir()},files)
    def test_preflight_and_wrong_profile(self):
        base=fixtures()['cases'][0]
        for control in fixtures()['preflight']:
            with tempfile.TemporaryDirectory() as d:
                case=dict(base);form=control.get('form','6')
                if 'source' in control:case.update(source=control['source'],arguments=control['arguments'])
                if control['name']=='explicit6-rejects-source5':case['source']=case['source'].replace('form/6','form/5')
                meta=prepare(Path(d),case)
                with patch.object(r.capture_tools,'capture',side_effect=AssertionError('preflight dispatch')):
                    with self.assertRaises(r.RunError) as caught:r.run_flow(**meta,form_version=form)
                self.assertEqual(caught.exception.code,control['error']);self.assertFalse(meta['output'].exists())
        for form,profile in [('6',11),('5',12)]:
            with tempfile.TemporaryDirectory() as d:
                case=dict(base)
                if form=='5':case=json.loads((ROOT/'examples/probes/source-run-flow/cases.json').read_bytes())['real_cases'][0]
                meta=prepare(Path(d),case)
                result={'schema':'bagaev-typed-record-result/'+str(profile),'status':'invalid-ir','value_type':None,'value':None,
                        'work':0,'reason':'RR_VERSION','location':'/schema'}
                raw=r.canonical(result)+b'\n'
                with patch.object(r.capture_tools,'capture',return_value=(0,raw,b'')):
                    with self.assertRaises(r.RunError) as caught:r.run_flow(**meta,form_version=form)
                self.assertEqual(caught.exception.code,'RUN_FLOW_RESULT');self.assertFalse((meta['output']/'receipt.json').exists())
                self.assertEqual((meta['output']/'reference.stdout').read_bytes(),raw)
    def test_receipt_schema_confusion(self):
        for name in fixtures()['receipt_controls']:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                meta,receipt,files=self.make(Path(d),fixtures()['cases'][0]);out=meta['output'];code='RUN_VERIFY_RECEIPT'
                if name=='old-schema-with-form':receipt['schema']='bagaev-record-source-run/1'
                elif name=='new-schema-missing-form':del receipt['form']
                elif name=='new-schema-wrong-form':receipt['form']='record-form/5'
                elif name=='form-as-integer':receipt['form']=6
                else:
                    target={'new-schema-with-old-source':'source.bagaev','new-schema-with-old-program':'program.json',
                            'new-schema-with-old-invocation':'invocation.json','new-schema-with-old-result':'reference.stdout'}[name]
                    raw=files[target].replace(b'form/6',b'form/5') if target=='source.bagaev' else files[target].replace(b'/12',b'/11')
                    (out/target).write_bytes(raw)
                    key={'source.bagaev':'source_sha256','program.json':'program_sha256','invocation.json':'invocation_sha256','reference.stdout':'result_sha256'}[target]
                    receipt[key]=r.sha(raw);code='RUN_VERIFY_SOURCE' if target in ('source.bagaev','program.json') else 'RUN_VERIFY_INVOCATION' if target=='invocation.json' else 'RUN_VERIFY_RESULT'
                raw=r.canonical(receipt);(out/'receipt.json').write_bytes(raw)
                with patch.object(r.capture_tools,'capture',side_effect=AssertionError('offline dispatch')):
                    with self.assertRaises(v.VerifyError) as caught:v.verify(out,r.sha(raw))
                self.assertEqual(caught.exception.code,code)
if __name__=='__main__':unittest.main()
