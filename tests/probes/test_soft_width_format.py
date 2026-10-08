"""Explicit presentation wrapping preserves token data and exact graph."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
from unittest.mock import patch
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'));sys.path.insert(0,str(T/'tools'))
import bagaev_record_wide_format as fmt
import record_format as cli
class SoftWidth(unittest.TestCase):
    def tokens(self,s):return [(t.rstrip() if c else t,c) for t,_,_,c in fmt.form.Reader(s).token_items]
    def test_legacy_and_wrapped_invariants(self):
        baseline={'examples/probes/inventory-batch/Batch.bagaev': '405408953a38cfac1dfb58b1954377033a29a1735d7c351b63cb8b6b9ce1b23e', 'examples/probes/inventory-batch/Batch.lazy.bagaev': '192bdef45f3ca11f1584b30272ab6d2425fcce8a6e19d196b5814b02ea0be4fd', 'examples/probes/annotated-named-change/BatchLimited.named.bagaev': '4e11f11378c6186b0bcfb52d4bd15196ee85cfb57a544a413a431f23126eed4c'}
        for path,digest in baseline.items():
            source=(T/path).read_bytes();self.assertEqual(hashlib.sha256(fmt.format_source(source)).hexdigest(),digest)
            for width in (40,80,120):
                out=fmt.format_source_wrapped(source,width=width);self.assertEqual(fmt.form.decode(out),fmt.form.decode(source));self.assertEqual(self.tokens(out),self.tokens(source));self.assertEqual(fmt.format_source_wrapped(out,width=width),out)
    def test_comments_literals_and_width_softness(self):
        literal='ёж'*100;comment='note '*40;source=('bagaev record-form/5;\r\nprogram { // '+comment+'\r\n entry main; fn main() -> Text = "'+literal+'"; }').encode()
        out=fmt.format_source_wrapped(source,width=40);self.assertIn(('"'+literal+'"').encode(),out);self.assertIn(('// '+comment.rstrip()).encode(),out);self.assertEqual(self.tokens(source),self.tokens(out));self.assertTrue(any(len(x)>40 for x in out.decode().splitlines()));self.assertEqual(fmt.format_source_wrapped(out,width=40),out)
    def test_expanded_output_bound(self):
        prefix=b'bagaev record-form/5; program {\n//';suffix=b'\nfn main() -> Int64 = 1; entry main; }'
        raw=prefix+b'x'*(fmt.form.old.BYTE_LIMIT-len(prefix)-len(suffix))+suffix
        fmt.form.decode(raw)
        with self.assertRaises(fmt.form.FormError) as err:fmt.format_source_wrapped(raw,width=80)
        self.assertEqual(err.exception.code,'FORM_BOUNDS')
    def test_wrapped_indent_uses_line_start_depth(self):
        source='bagaev record-form/5; program { entry main; fn main(x: Int64) -> Int64 = (if (x < 0) then (0) else (x)); }\n'
        expected='bagaev record-form/5;\nprogram {\n  entry main;\n  fn main(x: Int64) -> Int64 =(if(x < 0)\n    then(0)\n    else(x));\n}\n'
        out=fmt.format_source_wrapped(source,width=80)
        self.assertEqual(out,expected.encode());self.assertEqual(fmt.format_source_wrapped(out,width=80),out)
        self.assertEqual(self.tokens(source),self.tokens(out));self.assertEqual(fmt.form.decode(source),fmt.form.decode(out))
    def test_invalid_width(self):
        for width in (True,False,None,39,121,40.0,'80'):
            with self.assertRaises(fmt.form.FormError) as err:fmt.format_source_wrapped(b'invalid',width=width)
            self.assertEqual(err.exception.code,'FORM_WIDTH')
        with patch.object(cli.transport,'read_input',side_effect=AssertionError('must not read')):
            for form,width in [('4','80'),('5','39'),('5','121'),('5','no'),('5','８０')]:
                with contextlib.redirect_stdout(io.StringIO()) as b:code=cli.main(['missing','--form',form,'--width',width,'--output','unused'])
                self.assertEqual(code,2);self.assertEqual(json.loads(b.getvalue())['error']['code'],'TOOL_USAGE')
    def test_cli_receipts_nooverwrite(self):
        source=T/'examples/probes/annotated-named-change/BatchLimited.named.bagaev';raw=source.read_bytes()
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            for width in (None,80):
                out=d/str(width);args=[str(source),'--form','5','--output',str(out)]+([] if width is None else ['--width',str(width)])
                with contextlib.redirect_stdout(io.StringIO()) as b:self.assertEqual(cli.main(args),0)
                receipt=json.loads(b.getvalue());self.assertEqual(receipt.get('soft_width'),width)
                expected=fmt.format_source(raw) if width is None else fmt.format_source_wrapped(raw,width=width);self.assertEqual(out.read_bytes(),expected)
                with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(cli.main(args),2)
                self.assertEqual(out.read_bytes(),expected)
        self.assertEqual(source.read_bytes(),raw)
if __name__=='__main__':unittest.main()
