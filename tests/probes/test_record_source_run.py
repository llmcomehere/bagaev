"""Fixed mocked controls. No reference executable or submitted source is run."""
import contextlib,copy,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import record_source_run as runner
sha=lambda raw:hashlib.sha256(raw).hexdigest()
canon=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def exact(a,b):
    if type(a) is not type(b):return False
    if type(a) is dict:return a.keys()==b.keys() and all(exact(a[k],b[k]) for k in a)
    if type(a) is list:return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
    return a==b
def fixtures():
    raw=(ROOT/'examples/probes/source-run-flow/cases.json').read_bytes()
    assert sha(raw)=='366cfe976c889a0c2b92cd55bd24a0e07441a458819547f392ebd36d94fd829a'
    return json.loads(raw)
class RunTests(unittest.TestCase):
    def setup_case(self,base,case=None):
        case=case or fixtures()['real_cases'][0]
        source=base/'source.bagaev';arguments=base/'arguments.json';reference=base/'reference.bin';out=base/'out'
        source.write_bytes(case['source'].encode());arguments.write_bytes(case['arguments'].encode())
        reference.write_bytes(b'mock binary; never executed')
        return {'source':source,'arguments':arguments,'reference':reference,'output':out,
                'source_sha256':sha(source.read_bytes()),'arguments_sha256':sha(arguments.read_bytes()),
                'reference_sha256':sha(reference.read_bytes())}
    def error(self,code,fn):
        with self.assertRaises(runner.RunError) as caught:fn()
        self.assertEqual(caught.exception.code,code)
    def expected_receipt(self,meta,case,stdout,result=None):
        result=case['expected'] if result is None else result;program=canon(case['program'])
        invocation=b'{"schema":"bagaev-typed-record-invocation/11","program":'+program+b',"arguments":'+meta['arguments'].read_bytes()+b'}'
        return {'schema':'bagaev-record-source-run/1','status':'completed','source_sha256':meta['source_sha256'],
            'arguments_sha256':meta['arguments_sha256'],'program_sha256':sha(program),'invocation_sha256':sha(invocation),
            'result_sha256':sha(stdout),'reference_sha256':meta['reference_sha256'],'runtime_status':result['status'],
            'reason':result['reason'],'location':result['location'],'work':result['work'],
            'reference_invoked':True,'execution_admission':False,'result_authentication':False,'application_expectation_checked':False}
    def test_literal_mocked_runs(self):
        for case in fixtures()['real_cases']:
            with self.subTest(case=case['name']),tempfile.TemporaryDirectory() as directory:
                meta=self.setup_case(Path(directory),case);stdout=canon(case['expected'])+b'\n'
                before={meta[k]:meta[k].read_bytes() for k in ('source','arguments','reference')}
                program=canon(case['program'])
                invocation=b'{"schema":"bagaev-typed-record-invocation/11","program":'+program+b',"arguments":'+before[meta['arguments']]+b'}'
                def capture(argv):
                    self.assertEqual(argv,[str(meta['reference']),'run','--input',str(meta['output']/'invocation.json')])
                    self.assertEqual((meta['output']/'invocation.json').read_bytes(),invocation)
                    return 0,stdout,b''
                with patch.object(runner.capture_tools,'capture',side_effect=capture) as mocked:
                    actual=runner.run_flow(**meta)
                self.assertEqual(mocked.call_count,1)
                expected=self.expected_receipt(meta,case,stdout);self.assertTrue(exact(actual,expected))
                files={'source.bagaev':before[meta['source']],'arguments.json':before[meta['arguments']],
                       'program.json':program,'invocation.json':invocation,'reference.stdout':stdout,
                       'reference.stderr':b'','receipt.json':canon(expected)}
                self.assertEqual({p.name for p in meta['output'].iterdir()},set(files))
                for name,raw in files.items():self.assertEqual((meta['output']/name).read_bytes(),raw)
                for path,raw in before.items():self.assertEqual(path.read_bytes(),raw)
    def test_envelopes_and_raw_parser(self):
        data=fixtures()
        for value in data['accepted_envelopes']:
            self.assertTrue(exact(runner.result_value(canon(value)),value))
        for value in data['rejected_envelopes']:
            self.error('RUN_FLOW_RESULT',lambda value=value:runner.result_value(canon(value)))
        for case in data['raw_stdout_controls']:
            with self.subTest(case=case['name']):
                self.error(case['error'],lambda case=case:runner.result_value(bytes.fromhex(case['hex'])))
    def test_preflight_no_dispatch(self):
        for case in fixtures()['preflight_controls']:
            with self.subTest(case=case['name']),tempfile.TemporaryDirectory() as directory:
                meta=self.setup_case(Path(directory));fault=case.get('fault')
                if 'source' in case:
                    meta['source'].write_bytes(case['source'].encode());meta['source_sha256']=sha(meta['source'].read_bytes())
                if 'arguments' in case or 'arguments_hex' in case:
                    raw=bytes.fromhex(case['arguments_hex']) if 'arguments_hex' in case else case['arguments'].encode()
                    meta['arguments'].write_bytes(raw);meta['arguments_sha256']=sha(raw)
                if fault in ('source-pin','arguments-pin','reference-pin'):meta[fault.replace('-pin','_sha256')]='0'*64
                elif fault=='pin-syntax':meta['source_sha256']='g'*64
                elif fault=='existing-output':meta['output'].mkdir();(meta['output']/'keep').write_bytes(b'unchanged')
                with patch.object(runner.capture_tools,'capture',side_effect=AssertionError('unexpected dispatch')) as mocked:
                    self.error(case['error'],lambda:runner.run_flow(**meta))
                self.assertEqual(mocked.call_count,0)
                if fault=='existing-output':self.assertEqual((meta['output']/'keep').read_bytes(),b'unchanged')
                else:self.assertFalse(meta['output'].exists())
    def test_process_and_capture_failures(self):
        data=fixtures();stdout=canon(data['real_cases'][0]['expected'])
        for case in data['process_controls']:
            with tempfile.TemporaryDirectory() as directory:
                meta=self.setup_case(Path(directory))
                with patch.object(runner.capture_tools,'capture',return_value=(case['code'],stdout,case['stderr'].encode())):
                    self.error(case['error'],lambda:runner.run_flow(**meta))
                self.assertFalse((meta['output']/'receipt.json').exists())
                self.assertEqual((meta['output']/'reference.stdout').read_bytes(),stdout)
        for supplied,expected in data['capture_controls'].items():
            with tempfile.TemporaryDirectory() as directory:
                meta=self.setup_case(Path(directory))
                with patch.object(runner.capture_tools,'capture',side_effect=runner.capture_tools.FlowError(supplied)):
                    self.error(expected,lambda:runner.run_flow(**meta))
                self.assertFalse((meta['output']/'receipt.json').exists())
                self.assertFalse((meta['output']/'reference.stdout').exists())
    def test_size_controls(self):
        for case in fixtures()['size_controls']:
            with self.subTest(target=case['target']),tempfile.TemporaryDirectory() as directory:
                meta=self.setup_case(Path(directory));target=case['target']
                if target in ('source','arguments','reference'):
                    meta[target].write_bytes(b' '*case['bytes']);meta[target+'_sha256']=sha(meta[target].read_bytes())
                    with patch.object(runner.capture_tools,'capture',side_effect=AssertionError('unexpected dispatch')) as mocked:
                        self.error(case['error'],lambda:runner.run_flow(**meta))
                    self.assertEqual(mocked.call_count,0);self.assertFalse(meta['output'].exists())
                elif target=='invocation':
                    raw=b'[null'+b' '*(case['argument_bytes']-6)+b']';self.assertEqual(len(raw),case['argument_bytes'])
                    meta['arguments'].write_bytes(raw);meta['arguments_sha256']=sha(raw)
                    with patch.object(runner.capture_tools,'capture',side_effect=AssertionError('unexpected dispatch')):
                        self.error(case['error'],lambda:runner.run_flow(**meta))
                    self.assertFalse(meta['output'].exists())
                elif target=='stdout':
                    raw=case['base'].encode();raw+=b' '*(case['bytes']-len(raw))
                    self.error(case['error'],lambda:runner.result_value(raw))
                    with patch.object(runner.capture_tools,'capture',return_value=(0,raw,b'')):
                        self.error(case['error'],lambda:runner.run_flow(**meta))
                    self.assertFalse((meta['output']/'receipt.json').exists())
                else:
                    fixture=fixtures()['real_cases'][0]
                    result={'schema':'bagaev-typed-record-result/11','status':'invalid-ir','value_type':None,
                            'value':None,'work':0,'reason':'RR_BOUNDS','location':''}
                    base=self.expected_receipt(meta,fixture,b'',result)
                    length=case['bytes']-len(canon(base));result['location']='/'+'x'*(length-1)
                    stdout=canon(result);self.assertLessEqual(len(stdout),1048576)
                    expected=self.expected_receipt(meta,fixture,stdout,result)
                    self.assertEqual(len(canon(expected)),case['bytes'])
                    with patch.object(runner.capture_tools,'capture',return_value=(0,stdout,b'')):
                        self.error(case['error'],lambda:runner.run_flow(**meta))
                    self.assertFalse((meta['output']/'receipt.json').exists())
    def test_post_run_preservation(self):
        for target in fixtures()['preservation_targets']:
            with self.subTest(target=target),tempfile.TemporaryDirectory() as directory:
                meta=self.setup_case(Path(directory));original=runner.write_file
                def mutate(path,raw):
                    original(path,raw)
                    if path.name=='reference.stderr':
                        changed=meta[target] if target in ('source','arguments','reference') else meta['output']/target
                        changed.write_bytes(b'changed after capture')
                stdout=canon(fixtures()['real_cases'][0]['expected'])
                with patch.object(runner,'write_file',side_effect=mutate),patch.object(runner.capture_tools,'capture',return_value=(0,stdout,b'')):
                    self.error('RUN_FLOW_PRESERVATION',lambda:runner.run_flow(**meta))
                self.assertFalse((meta['output']/'receipt.json').exists())
    def test_publication_and_delivery(self):
        controls=fixtures()['publication_controls'];stdout=canon(fixtures()['real_cases'][0]['expected'])
        with tempfile.TemporaryDirectory() as directory:
            meta=self.setup_case(Path(directory));original=runner.write_file
            def fail_receipt(path,raw):
                if path.name=='receipt.json':path.write_bytes(b'{');raise runner.RunError('RUN_FLOW_OUTPUT')
                original(path,raw)
            with patch.object(runner,'write_file',side_effect=fail_receipt),patch.object(runner.capture_tools,'capture',return_value=(0,stdout,b'')):
                self.error(controls[0]['error'],lambda:runner.run_flow(**meta))
            self.assertEqual((meta['output']/'receipt.json').read_bytes(),b'{')
        with tempfile.TemporaryDirectory() as directory:
            meta=self.setup_case(Path(directory));actual_print=print;stderr=io.StringIO()
            argv=[str(meta['source'])]
            for flag,key in [('arguments','arguments'),('reference','reference'),('output','output'),
                             ('source-sha256','source_sha256'),('arguments-sha256','arguments_sha256'),('reference-sha256','reference_sha256')]:
                argv+=['--'+flag,str(meta[key])]
            def fail_stdout(*args,**kwargs):
                if kwargs.get('file',sys.stdout) is sys.stdout:raise BrokenPipeError('closed stdout')
                return actual_print(*args,**kwargs)
            with contextlib.redirect_stderr(stderr),patch('builtins.print',side_effect=fail_stdout),patch.object(runner.capture_tools,'capture',return_value=(0,stdout,b'')):
                code=runner.main(argv)
            self.assertEqual(code,1);self.assertEqual(stderr.getvalue(),controls[1]['error']+'\n')
            self.assertTrue(exact(json.loads((meta['output']/'receipt.json').read_bytes()),self.expected_receipt(meta,fixtures()['real_cases'][0],stdout)))
    def test_usage_no_dispatch(self):
        stderr=io.StringIO()
        with contextlib.redirect_stderr(stderr),patch.object(runner.capture_tools,'capture',side_effect=AssertionError('unexpected dispatch')) as mocked:
            self.assertEqual(runner.main([]),1)
        self.assertEqual(stderr.getvalue(),'TOOL_USAGE\n');self.assertEqual(mocked.call_count,0)
if __name__=='__main__':unittest.main()
