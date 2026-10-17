"""Malformed focused-export delta returns a structured refusal, not traceback."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tools'))
import bagaev_record_export as export
import bagaev_record_json_bool_change as bool_change
import record_export as cli
OBSERVATIONS=[]

def fixture(version):
    source=f'bagaev record-form/{version}; program {{ entry main; fn helper() -> Int64 = 3; fn main() -> Int64 = 1; }}'
    fragment=f'bagaev record-form/{version}; program {{ entry main; fn main() -> Int64 = 2; }}'
    edit={'4':export.narrow,'5':export.wide,'6':bool_change}[version]
    before=edit.form.decode(source)
    base=export.digest(before)
    packet=edit.replace(source,fragment,base_sha256=base,function_sha256=export.digest(before['functions']['main']))
    return source,base,packet,edit

def forged():
    return [
        {'add':[],'replace':['\ud800']},
        {'add':[],'replace':['main'],'\ud800':0},
        {'add':[],'replace':['main'],'extra':'\udfff'},
        '\ud800', ['\ud800'],
        {'add':[],'replace':[]},
        {'add':['helper'],'replace':['main']},
    ]

class ExportDelta(unittest.TestCase):
    def test_valid_and_forged_api(self):
        for version in ('4','5','6'):
            source,base,packet,edit=fixture(version)
            self.assertEqual(packet['delta'],{'add':[],'replace':['main']})
            self.assertIs(packet['semantic_check'],False)
            self.assertIs(packet['execution_admission'],False)
            raw=export.export_source(source,packet,base_sha256=base,target_sha256=packet['target'],form_version=version)
            expected=edit.form.decode(source)
            expected['functions']['main']['body']=['int',2]
            self.assertEqual(edit.form.decode(raw),expected)
            for delta in forged():
                with self.subTest(form=version,delta=ascii(delta)):
                    bad=copy.deepcopy(packet);bad['delta']=delta;before=copy.deepcopy(bad)
                    with self.assertRaises(export.DraftError) as ctx:
                        export.export_source(source,bad,base_sha256=base,target_sha256=packet['target'],form_version=version)
                    self.assertEqual(ctx.exception.code,'EXPORT_PACKET')
                    self.assertEqual(bad,before)

    def test_cli_refusal_and_output_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for version in ('4','5','6'):
                source,base,packet,edit=fixture(version)
                original=root/('source'+version);original.write_text(source)
                for index,delta in enumerate(forged()):
                    bad=copy.deepcopy(packet);bad['delta']=delta
                    draft=root/f'draft{version}-{index}'
                    payload=json.dumps(bad,ensure_ascii=True).encode();draft.write_bytes(payload)
                    for existing in (False,True):
                        output=root/f'out{version}-{index}-{existing}'
                        if existing:output.write_bytes(b'preserve-existing')
                        args=[str(original),'--draft',str(draft),'--base',base,'--target',packet['target'],'--form',version,'--output',str(output)]
                        stdout,stderr=io.StringIO(),io.StringIO()
                        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):status=cli.main(args)
                        self.assertEqual(status,2)
                        self.assertEqual(json.loads(stdout.getvalue()),{'schema':'bagaev-record-export/1','ok':False,'error':{'code':'EXPORT_PACKET'}})
                        self.assertEqual(stderr.getvalue(),'')
                        self.assertEqual(output.read_bytes() if existing else output.exists(),b'preserve-existing' if existing else False)
                        self.assertEqual(original.read_text(),source);self.assertEqual(draft.read_bytes(),payload)
                        OBSERVATIONS.append({'form':version,'case':index,'existing':existing,'status':status,'receipt':json.loads(stdout.getvalue())})
                good=root/('good'+version);good.write_text(json.dumps(packet))
                output=root/('valid'+version)
                stdout=io.StringIO()
                with contextlib.redirect_stdout(stdout):status=cli.main([str(original),'--draft',str(good),'--base',base,'--target',packet['target'],'--form',version,'--output',str(output)])
                self.assertEqual(status,0)
                receipt=json.loads(stdout.getvalue());self.assertIs(receipt['semantic_check'],False);self.assertIs(receipt['execution_admission'],False)
                self.assertEqual(edit.form.decode(output.read_bytes()),packet['program'])
                OBSERVATIONS.append({'form':version,'case':'valid','status':status,'receipt':receipt})

    def test_layout_routes(self):
        for version in ('5','6'):
            source,base,packet,_=fixture(version)
            bad=copy.deepcopy(packet);bad['delta']={'add':[],'replace':['\ud800']}
            emitter=export if version=='5' else bool_change
            with self.assertRaises(export.DraftError) as ctx:
                emitter.export_source_preserving_layout(source,bad,base_sha256=base,target_sha256=packet['target'],source_sha256=hashlib.sha256(source.encode()).hexdigest())
            self.assertEqual(ctx.exception.code,'EXPORT_PACKET')

if __name__=='__main__':unittest.main()
