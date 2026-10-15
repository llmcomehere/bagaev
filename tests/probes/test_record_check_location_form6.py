import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tools'))
import bagaev_record_check_location as loc
import record_check_location as cli
from bagaev_record_draft import DraftError

def sha(raw):return hashlib.sha256(raw).hexdigest()
def raw(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
SOURCE=b'bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = json.bool_or(x, 0); }'
PROGRAM={'schema':'bagaev-typed-record/12','records':{},'lists':{},'variants':{},'entry':'main',
         'functions':{'main':{'params':[['x','Json']],'result':'Bool','body':['json.bool_or',['arg','x'],['int',0]]}}}

class Form6Locations(unittest.TestCase):
    def setUp(self):
        self.input=raw(PROGRAM)
        self.result=(ROOT/'examples/probes/record-check-location/type-refusal12.json').read_bytes()
        self.pins=dict(source_sha256=sha(SOURCE),program_sha256=sha(self.input),
                       input_sha256=sha(self.input),result_sha256=sha(self.result))

    def test_retained_fallback(self):
        self.assertEqual(json.loads(self.result),{'schema':'bagaev-record-source-check/12',
            'status':'refused','reason':'RR_TYPE','location':'/functions/main/body/2',
            'input_sha256':sha(self.input),'program_sha256':None,'execution_admission':False})
        got=loc.locate_form6(SOURCE,self.input,self.result,**self.pins)
        self.assertEqual(got['schema'],'bagaev-record-check-location/2')
        self.assertEqual(got['excerpt'],'0')
        self.assertEqual(got['location']['precision'],'exact-expression')
        self.assertEqual(got['location']['start_byte'],SOURCE.index(b'0'))
        self.assertEqual(got['location']['end_byte'],SOURCE.index(b'0')+1)
        self.assertFalse(got['semantic_check']);self.assertFalse(got['execution_admission'])

    def test_profiles_and_pins(self):
        with self.assertRaises(loc.form.FormError):loc.locate(SOURCE,self.input,self.result,**self.pins)
        result=json.loads(self.result);result['schema']='bagaev-record-source-check/11';retained=raw(result)
        with self.assertRaises(DraftError) as error:
            loc.locate_form6(SOURCE,self.input,retained,**dict(self.pins,result_sha256=sha(retained)))
        self.assertEqual(error.exception.code,'CHECK_LOCATION_RESULT')
        for name in self.pins:
            with self.assertRaises(DraftError):loc.locate_form6(SOURCE,self.input,self.result,**dict(self.pins,**{name:'0'*64}))
        source5=b'bagaev record-form/5; program { entry main; fn main() -> Int64 = true; }'
        program5={'schema':'bagaev-typed-record/11','records':{},'lists':{},'variants':{},'entry':'main',
                  'functions':{'main':{'params':[],'result':'Int64','body':['bool',True]}}}
        input5=raw(program5);wrong=json.loads(self.result)
        wrong['input_sha256']=sha(input5);wrong['location']='/functions/main/body';retained=raw(wrong)
        with self.assertRaises(DraftError) as error:
            loc.locate(source5,input5,retained,source_sha256=sha(source5),program_sha256=sha(input5),
                       input_sha256=sha(input5),result_sha256=sha(retained))
        self.assertEqual(error.exception.code,'CHECK_LOCATION_RESULT')

    def test_unicode_crlf_and_cli(self):
        source=SOURCE.replace(b'; program', '; // Ж\r\nprogram'.encode())
        pins=dict(self.pins,source_sha256=sha(source))
        got=loc.locate_form6(source,self.input,self.result,**pins)
        self.assertEqual(got['location']['start_line'],2)
        self.assertEqual(got['location']['start_column'],66)
        self.assertEqual(got['location']['start_byte'],source.index(b'0'))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,data in [('source',source),('input',self.input),('result',self.result)]:
                (root/name).write_bytes(data)
            args=[str(root/'source'),'--form','6','--checked-input',str(root/'input'),'--result',str(root/'result'),
                  '--output',str(root/'out')]
            for name,pin in pins.items():args+=['--'+name.replace('_','-'),pin]
            self.assertEqual(cli.main(args),0)
            self.assertEqual(json.loads((root/'out').read_bytes()),got)
            before=(root/'out').read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(cli.main(args),1)
            self.assertEqual((root/'out').read_bytes(),before)
            invalid=list(args);invalid[0]=str(root/'missing');invalid[2]='7'
            with contextlib.redirect_stderr(io.StringIO()) as errors:self.assertEqual(cli.main(invalid),1)
            self.assertEqual(errors.getvalue(),'TOOL_USAGE\n')
            self.assertEqual((root/'out').read_bytes(),before)

if __name__=='__main__':unittest.main()
