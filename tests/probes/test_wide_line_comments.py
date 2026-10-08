"""Lexical trivia, retained comments and exact source positions; no evaluation."""
from pathlib import Path
import sys,json,hashlib,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_form as f
import bagaev_record_wide_format as fmt
import bagaev_record_wide_spans as spans
import bagaev_record_wide_diagnostics as diagnostics
import bagaev_record_json_form as old
class LineComments(unittest.TestCase):
    def test_graph_format_and_ranges(self):
        for case in json.loads((T/'examples/probes/wide-line-comments/cases.json').read_bytes()):
            raw=case['source'];graph=f.decode(raw);self.assertEqual(graph,f.decode(case['plain']));self.assertTrue(diagnostics.diagnose(raw)['valid_form'])
            out=fmt.format_source(raw);self.assertEqual(f.decode(out),graph);self.assertEqual(fmt.format_source(out),out)
            comments=lambda s:[token.rstrip() for token,_,_,comment in f.Reader(s).token_items if comment]
            self.assertEqual(comments(raw),comments(out));self.assertEqual(f.encode(graph),f.encode(f.decode(case['plain'])))
            mapping=spans.source_map(raw)
            if case['id']!='slash-string':
                for pointer,text in [('/program/functions/main/body/1','1'),('/program/functions/main/body/2','2')]:
                    row=next(x for x in mapping['locations'] if x['program_pointer']==pointer);self.assertEqual(raw.encode()[row['start_byte']:row['end_byte']].decode(),text)
    def test_default_format_bytes(self):
        expected={'Batch.bagaev':'405408953a38cfac1dfb58b1954377033a29a1735d7c351b63cb8b6b9ce1b23e','Batch.lazy.bagaev':'192bdef45f3ca11f1584b30272ab6d2425fcce8a6e19d196b5814b02ea0be4fd'}
        for file,digest in expected.items():self.assertEqual(hashlib.sha256(fmt.format_source((T/'examples/probes/inventory-batch'/file).read_bytes())).hexdigest(),digest)
    def test_header_control_and_bounds(self):
        base='bagaev record-form/5; program { fn main() -> Int64 = 1; entry main; }'
        for raw in ['// before\n'+base,base.replace('; program','; // Ж\0bad\nprogram'),base+' //'+('a'*f.old.BYTE_LIMIT)]:
            with self.assertRaises(f.FormError):f.decode(raw)
            self.assertFalse(diagnostics.diagnose(raw)['valid_form'])
        raw=base.replace('; program','; // Ж\0bad\nprogram');span=diagnostics.diagnose(raw)['error']['span'];self.assertEqual(span['start_byte'],len(raw[:raw.index('\0')].encode()))
        with self.assertRaises(old.FormError):old.decode(base.replace('record-form/5','record-form/4')+' // old')
if __name__=='__main__':unittest.main()
