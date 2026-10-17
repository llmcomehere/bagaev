"""Literal flow oracles, synthetic runner controls and bounded capture controls."""
import contextlib,copy,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import record_source_check as flow
CASES=json.loads((ROOT/'examples/probes/source-check-flow/cases.json').read_bytes())
def raw(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def verdict(case):
    pin=sha(raw(case['ast']))
    return {'schema':'bagaev-record-source-check/'+('12' if case['form']=='6' else '11'),
      'status':case['status'],'input_sha256':pin,'program_sha256':pin if case['status']=='checked' else None,
      'reason':case['reason'],'location':case['pointer'],'execution_admission':False}
class FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.p=Path(self.temp.name)
        self.binary=self.p/'checker';self.binary.write_bytes(b'synthetic runner identity; never executed')
        self.pin=sha(self.binary.read_bytes());self.source=self.p/'source.bagaev'
    def tearDown(self):self.temp.cleanup()
    def invoke(self,case,name='out',result=None):
        self.source.write_text(case['source']);stdout=raw(verdict(case))+b'\n' if result is None else result
        with patch.object(flow,'capture',return_value=(0,stdout,b'')) as runner:
            got=flow.run_flow(self.source,self.binary,self.pin,self.p/name,case['form'])
        argv=runner.call_args.args[0]
        self.assertEqual(argv,[str(self.binary),'check']+(['--profile','12'] if case['form']=='6' else [])+['--input',str(self.p/name/'program.json')])
        self.assertEqual(runner.call_count,1);return got,stdout
    def test_literal_complete_flows(self):
        for case in CASES:
            got,stdout=self.invoke(case,case['name']);out=self.p/case['name'];program=raw(case['ast'])
            expected={'schema':'bagaev-record-check-flow/1','status':case['status'],'form':'record-form/'+case['form'],
                'source_sha256':sha(case['source'].encode()),'program_sha256':sha(program),'input_sha256':sha(program),
                'result_sha256':sha(stdout),'checker_sha256':self.pin,'checker_invoked':True,'execution_admission':False}
            self.assertEqual(got,expected);self.assertEqual((out/'receipt.json').read_bytes(),raw(expected))
            self.assertEqual((out/'program.json').read_bytes(),program)
            self.assertEqual((out/'checker.stdout').read_bytes(),stdout)
            self.assertEqual((out/'checker.stderr').read_bytes(),b'')
            self.assertEqual((out/'source.bagaev').read_bytes(),case['source'].encode())
            if case['status']=='refused':
                mapped=json.loads((out/'location.json').read_bytes());self.assertEqual(mapped['excerpt'],case['excerpt'])
                start=case['source'].index(case['excerpt'])
                self.assertEqual(mapped['location']['start_byte'],start)
                self.assertEqual(mapped['location']['end_byte'],start+len(case['excerpt']))
                for flag in ('semantic_check','result_authentication','execution_admission'):self.assertIs(mapped[flag],False)
            else:self.assertFalse((out/'location.json').exists())
            self.assertEqual(self.source.read_text(),case['source']);self.assertEqual(sha(self.binary.read_bytes()),self.pin)
    def test_preflight_never_dispatches(self):
        self.source.write_text(CASES[0]['source'])
        with patch.object(flow,'capture') as runner:
            for pin,form,code in [('0'*64,'5','CHECK_FLOW_PIN'),(self.pin,'7','TOOL_USAGE')]:
                with self.assertRaises(flow.FlowError) as e:flow.run_flow(self.source,self.binary,pin,self.p/'missing',form)
                self.assertEqual(e.exception.code,code);self.assertFalse((self.p/'missing').exists())
            self.source.write_text('invalid source')
            with self.assertRaises(flow.FlowError) as e:flow.run_flow(self.source,self.binary,self.pin,self.p/'missing')
            self.assertEqual(e.exception.code,'CHECK_FLOW_SOURCE');self.assertFalse((self.p/'missing').exists())
            self.source.write_text(CASES[0]['source']);(self.p/'existing').mkdir();(self.p/'existing'/'keep').write_bytes(b'unchanged')
            with self.assertRaises(flow.FlowError) as e:flow.run_flow(self.source,self.binary,self.pin,self.p/'existing')
            self.assertEqual(e.exception.code,'CHECK_FLOW_OUTPUT');self.assertEqual((self.p/'existing'/'keep').read_bytes(),b'unchanged')
            runner.assert_not_called()
    def test_invalid_envelopes_never_complete(self):
        case=CASES[0];base=verdict(case);bad=[]
        for field,value in [('schema','bagaev-record-source-check/12'),('input_sha256','0'*64),
                            ('program_sha256','0'*64),('execution_admission',True),('reason','RR_TYPE'),('status','unknown')]:
            item=copy.deepcopy(base);item[field]=value;bad.append(raw(item))
        bad += [b'{"x":false,"x":false}',raw(base).decode().encode('utf-16'),b' '*1048577]
        for i,data in enumerate(bad):
            with self.assertRaises(flow.FlowError) as e:self.invoke(case,'bad'+str(i),data)
            self.assertEqual(e.exception.code,'CHECK_FLOW_RESULT');self.assertFalse((self.p/('bad'+str(i))/'receipt.json').exists())
    def test_runner_failures_and_unmapped(self):
        self.source.write_text(CASES[0]['source'])
        for i,returned in enumerate([(1,b'',b''),(0,raw(verdict(CASES[0])),b'warning'),(0,b'',b'x'*4097)]):
            with patch.object(flow,'capture',return_value=returned):
                with self.assertRaises(flow.FlowError) as e:flow.run_flow(self.source,self.binary,self.pin,self.p/str(i))
            self.assertEqual(e.exception.code,'CHECK_FLOW_PROCESS');self.assertFalse((self.p/str(i)/'receipt.json').exists())
        with patch.object(flow,'capture',side_effect=flow.FlowError('CHECK_FLOW_PROCESS')):
            with self.assertRaises(flow.FlowError):flow.run_flow(self.source,self.binary,self.pin,self.p/'timeout')
        self.assertFalse((self.p/'timeout'/'receipt.json').exists())
        case=CASES[1];v=verdict(case);v['location']=''
        self.invoke(case,'unmapped',raw(v));m=json.loads((self.p/'unmapped'/'location.json').read_bytes())
        self.assertEqual(m['status'],'unmapped');self.assertIsNone(m['location']);self.assertIsNone(m['excerpt'])
    def test_real_capture_limits(self):
        # Own fixed synthetic control code, not Bagaev source or a fake checker.
        for snippet,timeout,code in [
            ('import sys;sys.stdout.write("x"*1048577)',15,'CHECK_FLOW_RESULT'),
            ('import sys;sys.stderr.write("x"*4097)',15,'CHECK_FLOW_PROCESS'),
            ('import time;time.sleep(1)',0.05,'CHECK_FLOW_PROCESS')]:
            with self.assertRaises(flow.FlowError) as e:flow.capture([sys.executable,'-B','-S','-c',snippet],timeout)
            self.assertEqual(e.exception.code,code)
        self.assertEqual(flow.capture([sys.executable,'-B','-S','-c','print("ok")']),(0,b'ok\n',b''))
    def test_retained_bundle_mutation(self):
        case=CASES[0];self.source.write_text(case['source']);out=self.p/'mutated'
        def mutate(argv):
            (out/'program.json').write_bytes(b'changed')
            return 0,raw(verdict(case)),b''
        with patch.object(flow,'capture',side_effect=mutate):
            with self.assertRaises(flow.FlowError) as e:flow.run_flow(self.source,self.binary,self.pin,out)
        self.assertEqual(e.exception.code,'CHECK_FLOW_OUTPUT');self.assertFalse((out/'receipt.json').exists())
    def test_delivery_failure_keeps_completed_receipt(self):
        case=CASES[0];self.source.write_text(case['source']);out=self.p/'delivery'
        class Closed(io.StringIO):
            def write(self,text):raise BrokenPipeError('synthetic closed delivery')
        with patch.object(flow,'capture',return_value=(0,raw(verdict(case)),b'')),patch.object(sys,'stdout',Closed()),contextlib.redirect_stderr(io.StringIO()) as errors:
            code=flow.main([str(self.source),'--checker',str(self.binary),'--checker-sha256',self.pin,'--output',str(out)])
        self.assertEqual(code,1);self.assertEqual(errors.getvalue(),'CHECK_FLOW_DELIVERY\n')
        self.assertEqual(json.loads((out/'receipt.json').read_bytes())['status'],'checked')
if __name__=='__main__':unittest.main()
