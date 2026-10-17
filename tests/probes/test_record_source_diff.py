"""Literal data-only comparison controls; no programme or checker execution."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import call, patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tools'))
import bagaev_record_source_diff as diff
import record_source_diff as cli
DATA=ROOT/'examples/probes/source-diff'
canon=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
sha=lambda b:hashlib.sha256(b).hexdigest()

def load(name,pin):
    raw=(DATA/name).read_bytes();assert sha(raw)==pin
    return json.loads(raw)
CASES=load('cases.json','38714eac86b80e2cfe77a32b42ce558bae8ff56d560f745f4ce97c100a2dbe54')
PROGRAMS={row['id']:row for row in load('programmes.json','c0f8fa8e274d027ec9a09b9a19a6993732681edc8f19d91bb53f9064551f403e')['cases']}
IDENTITIES=load('real-identities.json','f58b5b1ae1e8a92515711628e48ad58e2ad7422986ba4f0bb2ede9f7ccf677d8')

def wanted(row,old,new):
    before,after=row['before'].encode(),row['after'].encode()
    namespaces={name:{'added':[],'removed':[],'changed':[]} for name in ('records','lists','variants','functions')}
    # Classification is taken from the frozen literal rows, never from a diff.
    for namespace,changes in row['changes'].items():
        for action,items in changes.items():
            for item in items:
                name=item['name'] if isinstance(item,dict) else item
                value={'name':name}
                if action!='added':value['before_sha256']=sha(canon(old[namespace][name]))
                if action!='removed':value['after_sha256']=sha(canon(new[namespace][name]))
                if isinstance(item,dict):value.update({k:item[k] for k in ('signature_changed','body_changed')})
                namespaces[namespace][action].append(value)
    return {'schema':'bagaev-record-source-diff/1','status':'compared','form':'record-form/5',
            'before':{'source_sha256':sha(before),'program_sha256':sha(canon(old)),'source_bytes':len(before)},
            'after':{'source_sha256':sha(after),'program_sha256':sha(canon(new)),'source_bytes':len(after)},
            'source_equal':row['source_equal'],'program_equal':row['program_equal'],
            'entry':{'before':old['entry'],'after':new['entry'],'changed':row['entry_changed']},
            'declarations':{k:namespaces[k] for k in ('records','lists','variants')},'functions':namespaces['functions'],
            'semantic_check':False,'execution_admission':False,'patch_application':False}

class SourceDiff(unittest.TestCase):
    def setUp(self):
        self.assertEqual(diff.SOURCE_LIMIT,1048576);self.assertEqual(diff.REPORT_LIMIT,1048576)
        guard=patch.object(subprocess,'Popen',side_effect=AssertionError('No execution'))
        guard.start();self.addCleanup(guard.stop)
        self.before=CASES['cases'][0]['before'].encode()

    def compare(self,before,after,**pins):
        return diff.compare_sources(before,after,**dict({'before_sha256':sha(before),'after_sha256':sha(after)},**pins))

    def refused(self,code,side,before=None,after=None,**pins):
        before=self.before if before is None else before;after=self.before if after is None else after
        defaults={'before_sha256':sha(before) if type(before)is bytes else sha(self.before),
                  'after_sha256':sha(after) if type(after)is bytes else sha(self.before)}
        with self.assertRaises(diff.DiffError) as caught:
            diff.compare_sources(before,after,**dict(defaults,**pins))
        self.assertEqual((caught.exception.code,caught.exception.side),(code,side))

    def test_literal_reports_against_manual_programmes(self):
        self.assertEqual(len(CASES['cases']),13)
        self.assertEqual(set(PROGRAMS),{row['id'] for row in CASES['cases']})
        for row in CASES['cases']:
            with self.subTest(case=row['id']):
                before,after=row['before'].encode(),row['after'].encode()
                original=(before,after)
                report=self.compare(before,after)
                literal=PROGRAMS[row['id']]
                self.assertEqual(canon(report),canon(wanted(row,literal['before'],literal['after'])))
                self.assertEqual(diff.encode_report(report),canon(report))
                self.assertEqual((before,after),original)

    def test_real_one_function_journey(self):
        before=(ROOT/'examples/probes/inventory-batch-change/BatchLimited.bagaev').read_bytes()
        fragment=(ROOT/'examples/probes/typed-journey/PerSku.fragment.bagaev').read_bytes()
        start=before.index(b'= let size =')+2;end=before.index(b';\n  fn batch_main')
        after=before[:start]+fragment[fragment.index(b'let size ='):fragment.rindex(b';')]+before[end:]
        frozen=CASES['real_journey'];report=self.compare(before,after)
        for side,raw in (('before',before),('after',after)):
            self.assertEqual(report[side],{'source_sha256':frozen[side+'_source_sha256'],
                'program_sha256':frozen[side+'_program_sha256'],'source_bytes':len(raw)})
        empty={'added':[],'removed':[],'changed':[]}
        self.assertEqual(report['declarations'],{name:empty for name in ('records','lists','variants')})
        self.assertEqual(report['functions'],{'added':[],'removed':[],'changed':[{
            'name':'batch_apply','before_sha256':IDENTITIES['before_sha256'],
            'after_sha256':IDENTITIES['after_sha256'],'signature_changed':False,'body_changed':True}]})
        self.assertFalse(report['source_equal']);self.assertFalse(report['program_equal'])
        self.assertEqual(report['entry'],{'before':'batch_main','after':'batch_main','changed':False})
        for key in ('semantic_check','execution_admission','patch_application'):self.assertIs(report[key],False)

    def test_refusal_identity_syntax_types_and_precedence(self):
        for side in ('before','after'):
            self.refused('DIFF_PIN',side,**{side+'_sha256':'bad'})
            self.refused('DIFF_'+side.upper(),side,**{side+'_sha256':'0'*64})
            self.refused('DIFF_INPUT',side,**{side:bytearray(self.before)})
            self.refused('DIFF_BOUNDS',side,**{side:b' '*(diff.SOURCE_LIMIT+1)})
            self.refused('FORM_VERSION',side,**{side:self.before.replace(b'record-form/5',b'record-form/6')})
        self.refused('FORM_SYNTAX','before',before=b'\xff')
        self.refused('FORM_SYNTAX','after',after=self.before[:-1])
        self.refused('FORM_BOUNDS','before',before=b'bagaev record-form/5; '+b'x '*32769)
        self.refused('DIFF_PIN','after',before=bytearray(self.before),after_sha256='bad')

    def test_real_source_and_report_limits(self):
        padded=self.before+b' '*(diff.SOURCE_LIMIT-len(self.before))
        report=self.compare(self.before,padded)
        self.assertFalse(report['source_equal']);self.assertTrue(report['program_equal'])
        prefix=b'bagaev record-form/5; program { entry main; fn main() -> Int64 = 7; fn '
        suffix=b'() -> Int64 = 1; }'
        before=prefix+b'a'*(530*1024)+suffix;after=prefix+b'b'*(530*1024)+suffix
        self.assertLess(len(before),diff.SOURCE_LIMIT);self.assertLess(len(after),diff.SOURCE_LIMIT)
        self.refused('DIFF_BOUNDS',None,before=before,after=after)
        # Labelled serialization-limit seam, separate from the real witness above.
        with patch.object(diff,'REPORT_LIMIT',1):self.refused('DIFF_BOUNDS',None)

    def test_cli_preservation_and_readback_seams(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);before=base/'before';after=base/'after'
            before.write_bytes(self.before);after.write_bytes(self.before)
            def argv(output):return [str(before),str(after),'--before-sha256',sha(self.before),
                '--after-sha256',sha(self.before),'--output',str(output)]
            captured=[]
            def envelope(value,code):captured.append((value,code));return code
            original=cli._read_side;counts={'before':0,'after':0}
            def drift(path,side):
                counts[side]+=1
                return b'changed' if side=='before' and counts[side]==2 else original(path,side)
            target=base/'drift'
            with patch.object(cli,'_read_side',side_effect=drift),patch.object(cli,'_envelope',side_effect=envelope):
                self.assertEqual(cli.main(argv(target)),2)
            self.assertEqual(captured[-1][0]['error'],{'code':'DIFF_CHANGED','side':'before'})
            self.assertFalse(target.exists())
            target=base/'readback';original_read=cli.transport.read_input
            def no_readback(path):
                if path==str(target):raise cli.transport.Refusal('RECORD_IO')
                return original_read(path)
            with patch.object(cli.transport,'read_input',side_effect=no_readback),patch.object(cli,'_envelope',side_effect=envelope):
                self.assertEqual(cli.main(argv(target)),2)
            self.assertEqual(captured[-1][0]['error'],{'code':'DIFF_OUTPUT','side':None})
            self.assertEqual(target.read_bytes(),diff.encode_report(self.compare(self.before,self.before)))
            self.assertEqual(before.read_bytes(),self.before);self.assertEqual(after.read_bytes(),self.before)

    def test_delivery_seams_do_not_retry_stdout(self):
        with patch.object(cli.os,'write',return_value=3) as write:
            self.assertEqual(cli._write_stdout(b'abc',0),0);write.assert_called_once_with(1,b'abc')
        with patch.object(cli.os,'write',side_effect=[1,14]) as write:
            self.assertEqual(cli._write_stdout(b'abc',0),1)
            self.assertEqual(write.call_args_list,[call(1,b'abc'),call(2,b'DIFF_DELIVERY\n')])
        with patch.object(cli.os,'write',side_effect=[BrokenPipeError(),14]) as write:
            self.assertEqual(cli._write_stdout(b'abc',0),1);self.assertEqual(write.call_count,2)
        with patch.object(cli.os,'write',side_effect=OSError()) as write:
            self.assertEqual(cli._write_stdout(b'abc',0),1);self.assertEqual(write.call_count,2)

if __name__=='__main__':unittest.main()
