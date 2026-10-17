"""Version-specific legacy codec tree checks; no language evaluation."""
import copy
import importlib
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
DATA = ROOT/'examples/probes'
PROFILES = [
 ('bagaev_component_arithmetic_form','component-arithmetic','component',3,2),
 ('bagaev_component_match_form','component-match','component',4,3),
 ('bagaev_component_text_list_form','component-text-list','component',5,3),
 ('bagaev_component_fold_form','component-fold','component',6,4),
 ('bagaev_component_record_list_form','component-record-list','component',7,4),
 ('bagaev_record_form','pure-record-form','record',1,4),
 ('bagaev_record_option_form','pure-option-form','record',2,4),
 ('bagaev_record_optional_fields_form','pure-optional-fields','record',3,4),
]
IF = ['if',['bool',True],['int',2],['int',3]]
LET = ['let','n',['int',3],['add',['use','n'],['int',1]]]
MATCH = ['match',['variant','Choice','Value',['int',4]],[['Value','n',['use','n']]]]
LOOP = ['loop',2,'i','total',['int',0],['add',['use','total'],['int',1]]]
CONTROLS = (IF,LET,MATCH,LOOP)

def document(kind, body, result='Int64'):
    if kind == 'component':
        cases = json.loads((DATA/'component-outcomes/form/cases.json').read_bytes())['cases']
        value = copy.deepcopy(next(c['expected']['source'] for c in cases if c['id']=='EXACT'))
        p = value['program']
    else:
        value = {'schema':'bagaev-typed-record/10','records':{},'lists':{},'variants':{},'entry':'probe','functions':{}}
        p = value
    p['variants']['Choice'] = {'Value':'Int64'}
    p['functions']['probe'] = {'params':[],'result':result,'body':copy.deepcopy(body)}
    return value

class LegacyOperands(unittest.TestCase):
    def test_literal_and_positions(self):
        count=0
        for name, _, kind, version, allowed in PROFILES:
            form=importlib.import_module(name)
            for control in CONTROLS[:allowed]:
                for op in ('add','sub','mul','lt'):
                    for left,right in ((control,['int',10]),(['int',10],control),(control,control)):
                        with self.subTest(codec=name,control=control[0],op=op,left=left[0],right=right[0]):
                            value=document(kind,[op,left,right],'Bool' if op=='lt' else 'Int64')
                            before=copy.deepcopy(value)
                            encoded=form.encode(value)
                            self.assertEqual(form.decode(encoded),value)
                            self.assertEqual(form.encode(form.decode(encoded)),encoded)
                            self.assertEqual(value,before)
                            count+=1
            # Source text is authored independently of encode for the changed body.
            value=document(kind,['add',IF,['int',10]])
            plain=form.encode(document(kind,['int',0])).decode()
            source=plain.replace('fn probe() -> Int64 = 0;', 'fn probe() -> Int64 = (if true then 2 else 3) + 10;')
            self.assertNotEqual(source,plain)
            self.assertEqual(form.decode(source),value)
        self.assertEqual(count,336)

    def test_nested_plain_and_boundaries(self):
        for name,_,kind,version,_ in PROFILES:
            form=importlib.import_module(name)
            with self.subTest(codec=name):
                value=document(kind,['mul',['if',['bool',False],IF,LET],['int',10]])
                self.assertEqual(form.decode(form.encode(value)),value)
                plain=form.encode(document(kind,['add',['int',2],['mul',['int',3],['int',4]]]))
                self.assertIn(b'fn probe() -> Int64 = (2 + (3 * 4));',plain)
                bad=plain.replace((kind+'-form/'+str(version)).encode(),(kind+'-form/999').encode(),1)
                with self.assertRaises(form.FormError) as ctx:form.decode(bad)
                self.assertEqual(ctx.exception.code,'FORM_VERSION')
                with self.assertRaises(form.FormError) as ctx:form.encode(document(kind,['json.kind',['int',0]]))
                self.assertEqual(ctx.exception.code,'FORM_PROFILE')
                unrepresentable=document(kind,['let','n',['int',3],['arg','n']])
                before=copy.deepcopy(unrepresentable)
                with self.assertRaises(form.FormError) as ctx:form.encode(unrepresentable)
                self.assertEqual(ctx.exception.code,'FORM_PROFILE')
                self.assertEqual(unrepresentable,before)

    def test_frozen_codec_cases(self):
        positive=negative=0
        for name,folder,_,_,_ in PROFILES:
            form=importlib.import_module(name)
            fixture=json.loads((DATA/folder/'cases.json').read_bytes())
            for case in fixture.get('positive',fixture.get('cases',[])):
                with self.subTest(codec=name,case=case.get('id')):
                    source=case.get('source',case.get('text'))
                    wanted=case.get('expected',case.get('expected_source',case.get('program')))
                    self.assertEqual(form.decode(source),wanted)
                    self.assertEqual(form.decode(form.encode(wanted)),wanted)
                    positive+=1
            for case in fixture.get('syntax',fixture.get('negative',[])):
                if 'expression' in case:
                    source=fixture['template'].replace('\n}', '\n fn bad(state: Stock) -> Int64 = '+case['expression']+';\n}')
                else:source=case['source']
                with self.subTest(codec=name,refusal=case.get('id')):
                    with self.assertRaises(form.FormError) as ctx:form.decode(source)
                    self.assertEqual(ctx.exception.code,case.get('code',case.get('error')))
                    negative+=1
        self.assertEqual((positive,negative),(58,32))

if __name__=='__main__':unittest.main()
