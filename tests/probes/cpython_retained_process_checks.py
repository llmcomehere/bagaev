"""Synthetic retained-data controls; run explicitly with python -B -S."""
import contextlib, io, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import record_cpython_run_expectation as reader
v=reader.run

class RetainedData(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.bundle=self.base/'bundle'
        self.bundle.mkdir();(self.bundle/'compiled').mkdir()
        source=b'bagaev record-form/5;\nprogram { entry main; fn main(input: Json) -> Bool = json.is_text(input); }\n'
        programme=v.canonical({'schema':'bagaev-typed-record/11','entry':'main','records':{},'lists':{},'variants':{},'functions':{'main':{'params':[['input','Json']],'result':'Bool','body':['json.is_text',['arg','input']]}}})
        python="raise AssertionError('RETAINED_DATA_MUST_NOT_EXECUTE')\n"
        artifact=v.canonical({'schema':'bagaev-record-cpython/1','profile':'bagaev-typed-record/11','program_sha256':v.sha(programme),'generator_sha256':'1'*64,'runtime_sha256':'2'*64,'python':python})
        compile_receipt={'schema':'bagaev-record-cpython-compile/1','status':'compiled','form':'record-form/5','source_sha256':v.sha(source),'program_sha256':v.sha(programme),'checker_sha256':'3'*64,'artifact_sha256':v.sha(artifact),'python_sha256':v.sha(python.encode()),'generator_sha256':'1'*64,'runtime_sha256':'2'*64,'checker_invoked':True,'generated_code_executed':False,'execution_admission':False}
        result={'schema':'bagaev-typed-record-result/11','status':'success','value_type':'Bool','value':True,'reason':None,'location':None,'work':2}
        self.expected={k:result[k] for k in reader.FIELDS}
        files={'compiled/source.bagaev':source,'compiled/program.json':programme,'compiled/artifact.json':artifact,'compiled/receipt.json':v.canonical(compile_receipt),'compiled/checker.stderr':b'','compiled/checker.stdout':v.canonical({'schema':'bagaev-record-source-check/11','status':'checked','input_sha256':v.sha(programme),'program_sha256':v.sha(programme),'reason':None,'location':None,'execution_admission':False}),'arguments.json':b'["ascii"]','result.stdout':v.canonical(result)+b'\n'}
        receipt={k:compile_receipt[k] for k in v.COMPILE_DIGESTS}
        receipt.update(schema='bagaev-record-cpython-run/1',status='executed',form='record-form/5',result_status='success',checker_invoked=True,generated_program_invocations=1,execution_admission=False,compile_receipt_sha256=v.sha(files['compiled/receipt.json']),arguments_sha256=v.sha(files['arguments.json']),result_sha256=v.sha(files['result.stdout']),runner_sha256='4'*64)
        files['receipt.json']=v.canonical(receipt)
        for name,raw in files.items():(self.bundle/name).write_bytes(raw)
        self.before=files
        self.pins={k:receipt[k] for k in ('source_sha256','program_sha256','arguments_sha256','runner_sha256')}
        self.pins['receipt_sha256']=v.sha(files['receipt.json'])
        self.spec=self.base/'expectations.json'
        self.document={'schema':'bagaev-record-run-expectations/2','form':'record-form/5','cases':[{'id':'ascii','arguments_raw':'["ascii"]','argument_count':1,'expected':dict(self.expected)}]}
        self.write_spec()
        for obj,name in ((subprocess,'Popen'),(v.runtime,'run_flow'),(reader.spec.run,'run_flow')):
            guard=patch.object(obj,name,side_effect=AssertionError('execution forbidden'))
            guard.start();self.addCleanup(guard.stop)

    def write_spec(self):
        raw=v.canonical(self.document);self.spec.write_bytes(raw)
        self.comparison=dict(self.pins,expectations=self.spec,expectation_sha256=v.sha(raw),case_id='ascii')

    def tearDown(self):
        self.assertEqual({str(p.relative_to(self.bundle)):p.read_bytes() for p in self.bundle.rglob('*') if p.is_file()},self.before)

    def test_inert_artifact_is_consistent_without_authentication(self):
        report=v.verify(self.bundle,**self.pins)
        self.assertEqual(report['status'],'consistent')
        for key in ('fresh_run','checker_invoked','result_authentication','execution_admission','application_expectation_checked'):
            self.assertIs(report[key],False)
        self.assertEqual(report['generated_program_invocations'],0)

    def test_literal_match_and_valid_mismatch(self):
        report=reader.verify(self.bundle,**self.comparison)
        self.assertEqual(report['status'],'matched');self.assertIs(report['independent_oracle_verified'],False)
        self.document['cases'][0]['expected']['value']=False;self.write_spec()
        report=reader.verify(self.bundle,**self.comparison)
        self.assertEqual(report['status'],'mismatched');self.assertIs(report['actual']['value'],True)
        self.assertFalse(reader.spec.bundle.exact({'step':True},{'step':1}))

    def test_wrong_pins_raw_arguments_and_report_overwrite(self):
        with self.assertRaises(v.VerifyError) as caught:v.verify(self.bundle,**dict(self.pins,receipt_sha256='0'*64))
        self.assertEqual(caught.exception.code,'CPY_VERIFY_PIN')
        self.document['cases'][0]['arguments_raw']+=' ';self.write_spec()
        with self.assertRaises(reader.ExpectError) as caught:reader.verify(self.bundle,**self.comparison)
        self.assertEqual(caught.exception.code,'CPY_EXPECT_ARGUMENTS')
        target=self.base/'occupied';target.write_bytes(b'keep')
        argv=[str(self.bundle)]
        for name,value in self.pins.items():argv+=['--'+name.replace('_','-'),value]
        argv+=['--output',str(target)]
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(v.main(argv),1)
        self.assertEqual(stderr.getvalue(),'CPY_VERIFY_OUTPUT\n');self.assertEqual(target.read_bytes(),b'keep')

if __name__=='__main__':unittest.main()
