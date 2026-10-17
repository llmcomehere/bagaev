import copy
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
def raw(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def program(body):return {'schema':'bagaev-typed-record/11','records':{},'lists':{},'variants':{},
    'entry':'main','functions':{'main':{'params':[],'result':'Int64','body':body}}}
SOURCE=b'bagaev record-form/5; program { entry main; fn main() -> Int64 = true; }'

class Locations(unittest.TestCase):
    def packet(self, source=SOURCE, value=None, pointer='/functions/main/body',reason='RR_TYPE'):
        value=program(['bool',True]) if value is None else value
        inp=raw(value)
        result={'schema':'bagaev-record-source-check/11','status':'refused','program_sha256':None,
                'input_sha256':sha(inp),'reason':reason,'location':pointer,'execution_admission':False}
        return source,inp,result

    def call(self, packet, **changes):
        source,inp,result=packet;retained=raw(result)
        pins=dict(source_sha256=sha(source),program_sha256=sha(inp),input_sha256=sha(inp),result_sha256=sha(retained))
        pins.update(changes)
        return loc.locate(source,inp,retained,**pins)

    def refusal(self, code, fn, *args, **kwargs):
        with self.assertRaises(DraftError) as caught:fn(*args,**kwargs)
        self.assertEqual(caught.exception.code,code)

    def test_exact_type_and_call(self):
        got=self.call(self.packet())
        self.assertEqual(got['status'],'mapped');self.assertEqual(got['excerpt'],'true')
        start=SOURCE.index(b'true')
        self.assertEqual((got['location']['start_byte'],got['location']['end_byte']),(start,start+4))
        self.assertEqual(got['location']['precision'],'exact-expression')
        source=SOURCE.replace(b'true',b'missing()')
        got=self.call(self.packet(source,program(['call','missing']),reason='RR_REFERENCE'))
        self.assertEqual(got['excerpt'],'missing()')
        self.assertFalse(got['semantic_check']);self.assertFalse(got['result_authentication'])

    def test_unused_unicode_crlf(self):
        source=('bagaev record-form/5; // Ж\r\nprogram { entry main;\r\n'
                'fn bad() -> Int64 = true;\r\nfn main() -> Int64 = 0; }').encode()
        value=program(['int',0]);value['functions']['bad']={'params':[],'result':'Int64','body':['bool',True]}
        got=self.call(self.packet(source,value,'/functions/bad/body'))
        self.assertEqual(got['excerpt'],'true')
        self.assertEqual(got['location']['start_byte'],source.index(b'true'))
        self.assertEqual(got['location']['start_line'],3)
        # "fn bad() -> Int64 = " has20 characters; one-based true starts at21.
        self.assertEqual(got['location']['start_column'],21)

    def test_coarse_and_unmapped(self):
        source=SOURCE.replace(b'true',b'1 + 2 + 3')
        value=program(['add',['add',['int',1],['int',2]],['int',3]])
        got=self.call(self.packet(source,value,'/functions/main/body/1'))
        self.assertEqual(got['location']['precision'],'enclosing-expression')
        self.assertEqual(got['excerpt'],'1 + 2 + 3')
        for pointer in ('','/schema','/functions/main/result','/functions/missing/body'):
            got=self.call(self.packet(pointer=pointer))
            self.assertEqual(got['status'],'unmapped')
            self.assertIsNone(got['location']);self.assertIsNone(got['excerpt'])

    def test_binding_and_shape_refusals(self):
        packet=self.packet()
        for pin,code in [('source_sha256','CHECK_LOCATION_LAYOUT'),('program_sha256','CHECK_LOCATION_PROGRAM'),
                         ('input_sha256','CHECK_LOCATION_INPUT_PIN'),('result_sha256','CHECK_LOCATION_RESULT_PIN')]:
            self.refusal(code,self.call,packet,**{pin:'0'*64})
        for field,value,code in [('input_sha256','0'*64,'CHECK_LOCATION_BINDING'),
                                 ('execution_admission',True,'CHECK_LOCATION_RESULT'),
                                 ('execution_admission',0,'CHECK_LOCATION_RESULT'),
                                 ('status','checked','CHECK_LOCATION_RESULT'),
                                 ('location','/bad~2','CHECK_LOCATION_POINTER'),
                                 ('location','not-a-pointer','CHECK_LOCATION_POINTER')]:
            bad=copy.deepcopy(packet);bad[2][field]=value
            self.refusal(code,self.call,bad)
        bad=copy.deepcopy(packet);bad[2]['extra']=False
        self.refusal('CHECK_LOCATION_RESULT',self.call,bad)

    def test_cli_preserves_existing(self):
        source,inp,result=self.packet();retained=raw(result)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,content in [('source',source),('input',inp),('result',retained)]:
                (root/name).write_bytes(content)
            output=root/'diagnostic'
            args=[str(root/'source'),'--checked-input',str(root/'input'),'--result',str(root/'result'),
                  '--source-sha256',sha(source),'--program-sha256',sha(inp),'--input-sha256',sha(inp),
                  '--result-sha256',sha(retained),'--output',str(output)]
            self.assertEqual(cli.main(args),0)
            before=output.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()) as errors:self.assertEqual(cli.main(args),1)
            self.assertEqual(errors.getvalue(),'RECORD_PATH\n');self.assertEqual(output.read_bytes(),before)

    def test_parser_controls(self):
        for value in (b'{"x":false,"x":true}',b'1.5',b'"\\ud800"'):
            self.refusal('CHECK_LOCATION_JSON',loc._json,value)
        self.refusal('CHECK_LOCATION_BOUNDS',loc._json,b'['*129+b']'*129)
        self.refusal('CHECK_LOCATION_BOUNDS',loc._raw,b' '*1048577)

    def test_noncanonical_and_retained_refusal(self):
        source,inp,result=self.packet()
        retained=(ROOT/'examples/probes/record-check-location/type-refusal.json').read_bytes()
        self.assertEqual(json.loads(retained),result)
        got=loc.locate(source,inp,retained,source_sha256=sha(source),program_sha256=sha(inp),
            input_sha256=sha(inp),result_sha256=sha(retained))
        self.assertEqual(got['excerpt'],'true')
        spaced=b' '+inp+b'\n';result['input_sha256']=sha(spaced);modified=raw(result)
        got=loc.locate(source,spaced,modified,source_sha256=sha(source),program_sha256=sha(inp),
            input_sha256=sha(spaced),result_sha256=sha(modified))
        self.assertEqual(got['excerpt'],'true')
        self.assertNotEqual(got['input_sha256'],got['program_sha256'])

    def test_excerpt_and_absent_refusal_output(self):
        literal='Ж'*300
        source=SOURCE.replace(b'true',('"'+literal+'"').encode())
        got=self.call(self.packet(source,program(['text',literal])))
        self.assertEqual(len(got['excerpt']),256);self.assertTrue(got['excerpt_truncated'])
        source,inp,result=self.packet();retained=raw(result)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,content in [('source',source),('input',inp),('result',retained)]:
                (root/name).write_bytes(content)
            output=root/'absent'
            args=[str(root/'source'),'--checked-input',str(root/'input'),'--result',str(root/'result'),
                '--source-sha256','0'*64,'--program-sha256',sha(inp),'--input-sha256',sha(inp),
                '--result-sha256',sha(retained),'--output',str(output)]
            with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(cli.main(args),1)
            self.assertFalse(output.exists())

if __name__=='__main__':unittest.main()
