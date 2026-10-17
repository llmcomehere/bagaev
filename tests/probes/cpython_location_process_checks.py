"""Synthetic failure-data controls, not authentic execution; use Python -B -S."""
import contextlib,io,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import record_cpython_run_location as location
v=location.run
SOURCE=b'bagaev record-form/5;\nprogram { entry main; fn main() -> Bool = option.is_some(some.int(9223372036854775807 + 1)); }\n'
PROGRAM={'schema':'bagaev-typed-record/11','entry':'main','records':{},'lists':{},'variants':{},'functions':{'main':{'params':[],'result':'Bool','body':['option.is_some',['some.int',['add',['int',9223372036854775807],['int',1]]]]}}}
POINTER='/program/functions/main/body/1/1'
ROW={'program_pointer':POINTER,'operation':'add','precision':'exact-expression','start_byte':88,'end_byte':111,'start_line':2,'start_column':67,'end_line':2,'end_column':90}

class LocationData(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.serial=0;self.retained={}
        for obj,name in ((subprocess,'Popen'),(v.runtime,'run_flow')):
            guard=patch.object(obj,name,side_effect=AssertionError('execution forbidden'))
            guard.start();self.addCleanup(guard.stop)

    def bundle(self,status='integer-overflow',pointer=POINTER):
        self.serial+=1;root=self.base/str(self.serial);root.mkdir();(root/'compiled').mkdir()
        programme=v.canonical(PROGRAM);python="raise AssertionError('DATA_MUST_NOT_EXECUTE')\n"
        artifact=v.canonical({'schema':'bagaev-record-cpython/1','profile':'bagaev-typed-record/11','program_sha256':v.sha(programme),'generator_sha256':'1'*64,'runtime_sha256':'2'*64,'python':python})
        compiled={'schema':'bagaev-record-cpython-compile/1','status':'compiled','form':'record-form/5','source_sha256':v.sha(SOURCE),'program_sha256':v.sha(programme),'checker_sha256':'3'*64,'artifact_sha256':v.sha(artifact),'python_sha256':v.sha(python.encode()),'generator_sha256':'1'*64,'runtime_sha256':'2'*64,'checker_invoked':True,'generated_code_executed':False,'execution_admission':False}
        result={'schema':'bagaev-typed-record-result/11','status':status,'value_type':None,'value':None,'reason':'RR_OVERFLOW','location':pointer,'work':5}
        if status=='success':result.update(value_type='Bool',value=True,reason=None,location=None)
        files={'compiled/source.bagaev':SOURCE,'compiled/program.json':programme,'compiled/artifact.json':artifact,'compiled/receipt.json':v.canonical(compiled),'compiled/checker.stderr':b'','compiled/checker.stdout':v.canonical({'schema':'bagaev-record-source-check/11','status':'checked','input_sha256':v.sha(programme),'program_sha256':v.sha(programme),'reason':None,'location':None,'execution_admission':False}),'arguments.json':b'[]','result.stdout':v.canonical(result)+b'\n'}
        receipt={k:compiled[k] for k in v.COMPILE_DIGESTS}
        receipt.update(schema='bagaev-record-cpython-run/1',status='executed',form='record-form/5',result_status=status,checker_invoked=True,generated_program_invocations=1,execution_admission=False,compile_receipt_sha256=v.sha(files['compiled/receipt.json']),arguments_sha256=v.sha(files['arguments.json']),result_sha256=v.sha(files['result.stdout']),runner_sha256='4'*64)
        files['receipt.json']=v.canonical(receipt)
        for name,raw in files.items():
            with (root/name).open('xb') as stream:self.assertEqual(stream.write(raw),len(raw))
        self.retained[root]=files
        pins={k:receipt[k] for k in ('source_sha256','program_sha256','arguments_sha256','runner_sha256')};pins['receipt_sha256']=v.sha(files['receipt.json'])
        return root,pins

    def tearDown(self):
        for root,files in self.retained.items():
            self.assertEqual({str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()},files)

    def test_literal_source_location_without_authentication(self):
        root,pins=self.bundle();report=location.verify(root,**pins)
        self.assertEqual(report['status'],'mapped');self.assertEqual(report['location'],ROW)
        self.assertEqual(report['excerpt'],'9223372036854775807 + 1')
        self.assertIs(report['excerpt_truncated'],False)
        for key in ('semantic_check','result_authentication','execution_admission','fresh_run','checker_invoked'):
            self.assertIs(report[key],False)
        self.assertEqual(report['generated_program_invocations'],0)

    def test_unmapped_is_explicit_and_success_is_refused(self):
        root,pins=self.bundle(pointer='/program/functions/main/body/99');report=location.verify(root,**pins)
        self.assertEqual(report['status'],'unmapped');self.assertIsNone(report['location']);self.assertIsNone(report['excerpt'])
        root,pins=self.bundle(status='success')
        with self.assertRaises(location.LocationError) as caught:location.verify(root,**pins)
        self.assertEqual(caught.exception.code,'CPY_LOCATION_STATUS')

    def test_each_stale_pin_is_refused(self):
        root,pins=self.bundle()
        for name in pins:
            with self.subTest(name=name):
                with self.assertRaises(v.VerifyError) as caught:location.verify(root,**dict(pins,**{name:'0'*64}))
                self.assertEqual(caught.exception.code,'CPY_VERIFY_PIN')

    def test_cli_preserves_occupied_output(self):
        root,pins=self.bundle();target=self.base/'report';target.write_bytes(b'keep')
        argv=[str(root)]
        for name,value in pins.items():argv+=['--'+name.replace('_','-'),value]
        argv+=['--output',str(target)]
        with contextlib.redirect_stdout(io.StringIO()) as out,contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(location.main(argv),1)
        self.assertEqual(out.getvalue(),'');self.assertEqual(err.getvalue(),'CPY_LOCATION_OUTPUT\n')
        self.assertEqual(target.read_bytes(),b'keep')

if __name__=='__main__':unittest.main()
