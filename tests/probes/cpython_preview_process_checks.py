"""Explicit data-only process checks; synthetic packets do not prove compilation."""
import hashlib, importlib.util, json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('preview_subject',ROOT/'tools/record_cpython_preview.py')
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
canon=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
TEXT=b"raise RuntimeError('must remain inert review data')\n"
FALSES=('fresh_compilation','checker_invoked','compiler_authentication','semantic_check',
        'source_program_equivalence_checked','program_python_equivalence_checked','python_syntax_checked','execution_admission')

def packet():
    source=b'review data, deliberately not parsed as language\n'
    program=canon({'schema':'bagaev-typed-record/11'})
    p=sha(program);fake='1'*64
    artifact=canon({'schema':'bagaev-record-cpython/1','profile':'bagaev-typed-record/11',
        'program_sha256':p,'generator_sha256':fake,'runtime_sha256':fake,'python':TEXT.decode()})
    receipt=canon({'schema':'bagaev-record-cpython-compile/1','status':'compiled','form':'record-form/5',
        'source_sha256':sha(source),'program_sha256':p,'checker_sha256':fake,'artifact_sha256':sha(artifact),
        'python_sha256':sha(TEXT),'generator_sha256':fake,'runtime_sha256':fake,
        'checker_invoked':True,'generated_code_executed':False,'execution_admission':False})
    checker=canon({'schema':'bagaev-record-source-check/11','status':'checked','input_sha256':p,
        'program_sha256':p,'reason':None,'location':None,'execution_admission':False})
    return {'source.bagaev':source,'program.json':program,'artifact.json':artifact,
            'receipt.json':receipt,'checker.stdout':checker,'checker.stderr':b''}

class PreviewProcessChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).absolute();self.base=self.root/'compiled';self.base.mkdir()
        self.data=packet();self.install()
        self.events=[]
        capture=patch.object(cli,'emit',side_effect=lambda value,fd=1:self.events.append((fd,value)))
        capture.start();self.addCleanup(capture.stop)

    def install(self):
        for name,raw in self.data.items():(self.base/name).write_bytes(raw)
        self.args=SimpleNamespace(compiled=str(self.base),output=str(self.root/'preview'),
            receipt_sha256=sha(self.data['receipt.json']),source_sha256=sha(self.data['source.bagaev']),
            program_sha256=sha(self.data['program.json']))

    def test_complete_inert_preview_report_and_manifest(self):
        original=dict(self.data);self.assertEqual(cli.preview(self.args),0)
        out=Path(self.args.output);self.assertEqual({p.name for p in out.iterdir()},{'python.txt','report.json','MANIFEST.json'})
        self.assertEqual((out/'python.txt').read_bytes(),TEXT)
        inputs={n:{'bytes':len(raw),'sha256':sha(raw)} for n,raw in sorted(self.data.items())}
        packet_pin=sha(canon(inputs));fake='1'*64
        expected={'schema':'bagaev-record-cpython-preview/1','status':'consistent',
            'form':'record-form/5','profile':'bagaev-typed-record/11','packet_sha256':packet_pin,
            'compile_receipt_sha256':self.args.receipt_sha256,'source_sha256':self.args.source_sha256,
            'program_sha256':self.args.program_sha256,'artifact_sha256':sha(self.data['artifact.json']),
            'python_sha256':sha(TEXT),'python_bytes':len(TEXT),'claimed_checker_sha256':fake,
            'claimed_generator_sha256':fake,'claimed_runtime_sha256':fake,'input_files':inputs,
            **{key:False for key in FALSES}}
        report=canon(expected);self.assertEqual((out/'report.json').read_bytes(),report)
        manifest=canon({'schema':'bagaev-record-cpython-preview-files/1','packet_sha256':packet_pin,
            'files':{'python.txt':{'bytes':len(TEXT),'sha256':sha(TEXT)},
                     'report.json':{'bytes':len(report),'sha256':sha(report)}},'execution_admission':False})
        self.assertEqual((out/'MANIFEST.json').read_bytes(),manifest)
        self.assertEqual(self.events,[(1,{'schema':'bagaev-record-cpython-preview-result/1','status':'preview',
            'packet_sha256':packet_pin,'python_sha256':sha(TEXT),'report_sha256':sha(report),
            'manifest_sha256':sha(manifest),'execution_admission':False})])
        self.assertEqual({n:(self.base/n).read_bytes() for n in self.data},original)

    def test_schema_flags_external_pin_and_existing_destination(self):
        for field,value in (('form','record-form/6'),('checker_invoked',1),('generated_code_executed',0)):
            with self.subTest(field=field):
                self.data=packet();receipt=json.loads(self.data['receipt.json']);receipt[field]=value
                self.data['receipt.json']=canon(receipt);self.install()
                with self.assertRaises(cli.PreviewError) as caught:cli.preview(self.args)
                self.assertEqual(caught.exception.code,'PREVIEW_RECEIPT')
                self.assertFalse(Path(self.args.output).exists())
        self.data=packet();self.install();self.args.receipt_sha256='0'*64
        with self.assertRaises(cli.PreviewError) as caught:cli.preview(self.args)
        self.assertEqual(caught.exception.code,'PREVIEW_PIN')
        self.install();Path(self.args.output).mkdir()
        with self.assertRaises(cli.PreviewError) as caught:cli.preview(self.args)
        self.assertEqual(caught.exception.code,'PREVIEW_EXISTS')
        self.assertEqual(list(Path(self.args.output).iterdir()),[])

    def test_metadata_bounds_help_and_write_failure_seam(self):
        self.assertEqual(cli.metadata(b'{"x":0}'),{'x':0})
        for raw in (b'{"x":0,"x":1}',b'{"x":0.5}',b'{"x":NaN}',b'{"x":"\\ud800"}'):
            with self.assertRaises(cli.PreviewError):cli.metadata(raw)
        for count,ok in ((32765,True),(32766,False)):
            raw=canon({'x':[0]*count})
            if ok:self.assertEqual(len(cli.metadata(raw)['x']),count)
            else:
                with self.assertRaises(cli.PreviewError) as caught:cli.metadata(raw)
                self.assertEqual(caught.exception.code,'PREVIEW_BOUNDS')
        writes=[]
        with patch.object(cli,'write_all',side_effect=lambda fd,raw:writes.append((fd,raw))):
            self.assertEqual(cli.main(['--help']),0)
        self.assertEqual(writes,[(1,cli.HELP.encode())])
        # Explicit injected writer seam; real partial-write/delivery controls are separate.
        with patch.object(cli,'save',side_effect=OSError('injected write failure')):
            with self.assertRaises(cli.PreviewError) as caught:cli.preview(self.args)
        self.assertEqual((caught.exception.code,caught.exception.uncertain),('PREVIEW_UNCERTAIN',True))
        self.assertEqual(list(Path(self.args.output).iterdir()),[])

if __name__=='__main__':unittest.main()
