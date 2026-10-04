"""Codec and delegated-semantics checks; frozen expectations are never rewritten."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import bagaev_forms as f
import bagaev_l2 as l2

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / 'examples/probes/form-oracle.json'

class FormTests(unittest.TestCase):
    def assert_form_error(self, text, form, code='FORM_SYNTAX', **options):
        with self.assertRaises(f.FormError) as e:
            f.decode(text, form, **options)
        self.assertEqual(e.exception.code, code)

    def test_canonical_scalar_container_and_macro_encodings(self):
        value={'z':['literal',['call','not-a-reference']],'a':None}
        expected={
            'json':b'{"a":null,"z":["literal",["call","not-a-reference"]]}',
            'sexpr':b'(obj ("a" null) ("z" (literal (call "not-a-reference"))))',
            'familiar':b'{"a": None, "z": l2_literal(l2_call("not-a-reference"))}',
        }
        for form,wire in expected.items():
            self.assertEqual(f.encode(value,form),wire)
            self.assertEqual(f.decode(wire,form),value)
        for op in sorted(f.OPS):
            for form in f.FORMS:
                value=[op,0,True,None,{'x':[]}]
                self.assertEqual(f.decode(f.encode(value,form),form),value)

    def test_familiar_program_and_definition_constructors(self):
        value={'schema':'bagaev-l2/1','entry':False,'definitions':{'main':{'params':0,'body':['future']}},'pins':[]}
        wire=b'l2_program(entry=False, definitions={"main": l2_def(params=0, body=["future"])}, pins=[])'
        self.assertEqual(f.encode(value,'familiar'),wire)
        self.assertEqual(f.decode(wire,'familiar'),value)
        for value in [[],0,{}, {'schema':'wrong','definitions':{'x':0}}, {'definitions':{'x':{'params':[],'body':0,'extra':1}}}]:
            self.assertEqual(f.decode(f.encode(value,'familiar'),'familiar'),value)
        self.assertEqual(f.decode('{"definitions":{"x":l2_def(params=[],body=1)}}','familiar'),{'definitions':{'x':{'params':[],'body':1}}})

    def test_constructor_positions_and_keywords_are_not_host_python(self):
        for text in ['l2_def(params=[],body=0)', '[l2_program(entry="x",definitions={},pins={})]',
                     '{"x":l2_def(params=[],body=0)}','l2_program(definitions={},entry="x",pins={})',
                     'l2_program(entry="x",definitions=[l2_def(params=[],body=0)],pins={})',
                     'l2_program(entry="x",definitions={},pins={},)', 'l2_int_range(x,0,1)',
                     '__import__("os")', '(lambda: 1)()', '1+2', 'x.y', '[1 for x in []]',
                     'f"{1}"', 'l2_if(True,1,2).__class__']:
            self.assert_form_error(text,'familiar')
        self.assert_form_error('l2_program(entry="x",definitions={},pins={})','familiar',mode='patch')
        patch={'add':{'x':{'params':[],'body':1}},'replace':{},'schema':'bagaev-l2-patch/1'}
        wire=f.encode(patch,'familiar',mode='patch')
        self.assertIn(b'l2_def',wire)
        self.assertEqual(f.decode(wire,'familiar',mode='patch'),patch)

    def test_complete_syntax_duplicate_keys_boundaries_and_whitespace(self):
        for form,bad in [('sexpr',['(arr) (arr)','(obj ("a" 1) ("\\u0061" 2))','(unknown 1)','(arr truefalse)','(arr 1e)','(arr "a""b")','(arr 01)','(arr) # comment']),
                         ('familiar',['[] []','{"a":1,"\\u0061":2}','[1,]','{"a":1,}','l2_if(True,1,)','[TrueFalse]','[01]','[] # comment'])]:
            for text in bad:
                self.assert_form_error(text,form)
        self.assertEqual(f.decode(' \n(obj\t("a"\r(arr 1 2))) ','sexpr'),{'a':[1,2]})
        self.assertEqual(f.decode(' \n { "a" : [ 1 , 2 ] } ','familiar'),{'a':[1,2]})

    def test_transport_codes_bom_utf8_and_overrun(self):
        for form in ['sexpr','familiar']:
            for text in [b'\xff',b'\xef\xbb\xbf[]','\ud800']:
                self.assert_form_error(text,form)
            self.assert_form_error(b' '*(f.BYTE_LIMIT+1),form,'FORM_BOUNDS')
        for raw,code in [(b'{}{}','L2_JSON'),(b' '*(f.BYTE_LIMIT+1),'L2_BOUNDS')]:
            with self.assertRaises(l2.L2Error) as e:f.decode(raw,'json')
            self.assertEqual(e.exception.code,code)

    def test_source_depth_and_value_occurrence_boundaries(self):
        for form in ['sexpr','familiar']:
            begin,end=('(arr ',')') if form=='sexpr' else ('[',']')
            value=f.decode(begin*255+'0'+end*255,form)
            for _ in range(255):value=value[0]
            self.assertEqual(value,0)
            self.assert_form_error(begin*256+'0'+end*256,form,'FORM_BOUNDS')
            sep=' ' if form=='sexpr' else ','
            source=begin+sep.join(['0']*32767)+end
            self.assertEqual(len(f.decode(source,form)),32767)
            self.assert_form_error(begin+sep.join(['0']*32768)+end,form,'FORM_BOUNDS')

    def test_surrogates_and_float_tags_reach_l2_without_early_repair(self):
        for form,source in [('json','"\\ud800"'),('sexpr','"\\ud800"'),('familiar','"\\ud800"')]:
            self.assertEqual(f.decode(source,form),'\ud800')
            with self.assertRaises(l2.L2Error) as e:f.check(source,form)
            self.assertEqual(e.exception.code,'L2_PROGRAM')
            self.assertIs(type(f.decode('1.0',form)),float)
        for form in f.FORMS:
            with self.assertRaises(l2.L2Error) as e:f.check(f.encode({'schema':'bad','entry':False},form),form)
            self.assertEqual(e.exception.code,'L2_PROGRAM')

    def test_encoder_refuses_cycles_and_non_json_objects(self):
        cycle=[];cycle.append(cycle)
        for form in f.FORMS:
            with self.assertRaises(f.FormError):f.encode(cycle,form)
            with self.assertRaises(f.FormError):f.encode(object(),form)
            with self.assertRaises(f.FormError) as e:f.encode('x'*(f.BYTE_LIMIT+1),form)
            self.assertEqual(e.exception.code,'FORM_BOUNDS')

    def test_large_integer_reconstruction_is_exact_without_global_switches(self):
        value={'z':[2**80,-2**90,True,1.5], 'a':'1234567890123456789012345'}
        for form in f.FORMS:
            self.assertEqual(f.decode(f.encode(value,form),form),value)
            wire='9'*5000
            number=f.decode(wire,form)
            self.assertEqual(f.encode(number,form),wire.encode())
        self.assertEqual(f.decode('{"z":1208925819614629174706176,"a":[-1234567890123456789012345,1.5]}','json'),{'z':2**80,'a':[-1234567890123456789012345,1.5]})

    def test_root_string_never_becomes_another_program(self):
        oracle=json.loads(ORACLE.read_text())
        body=oracle['cases'][0]['input']['body']
        program={'schema':'bagaev-l2/1','entry':'main','definitions':{'main':{'params':['x'],'body':body}},'pins':oracle['identities']['F-LITERAL']['pins']}
        inner=json.dumps(program)
        for form in f.FORMS:
            for value in [inner, 'null', '\ud800', '0']:
                with self.assertRaises(l2.L2Error) as e:f.check(f.encode(value,form),form)
                self.assertEqual(e.exception.code,'L2_PROGRAM')

    def test_resource_refusals_and_malformed_maximal_prefix(self):
        for form in f.FORMS:
            for value in [[0]*32768, 1 << (f.BYTE_LIMIT*4+1)]:
                with self.assertRaises(f.FormError) as e:f.encode(value,form)
                self.assertEqual(e.exception.code,'FORM_BOUNDS')
            with self.assertRaises(f.FormError):f.encode({1:2},form)
        self.assert_form_error('(arr '+' '.join(['0']*32767),'sexpr')
        self.assert_form_error('['+','.join(['0']*32767),'familiar')

    @staticmethod
    def fixture_argument(spec):
        if 'argument' in spec:return copy.deepcopy(spec['argument'])
        if 'descriptor' in spec:
            assert spec['descriptor']==['float','1.5']
            return 1.5
        recipe=spec.get('argument_recipe')
        if recipe=='F-DEEP-D':
            value=None
            for _ in range(254):value=[value]
            return {'d':value}
        if recipe=='F-LARGE-INGRESS':return {'n':1208925819614629174706176,'s':'a'*4097,'a':[None]*257}
        if recipe=='F-STRING-PRIORITY':return {'a':'a'*4097,'b':'\ud800'}
        if recipe in ('F-NULL45','F-NULL46'):return [None]*(45 if recipe=='F-NULL45' else 46)
        if recipe=='F-STRINGS256':return ['s%03d'%i for i in range(256)]
        assert recipe is None
        return None

    def test_frozen_non_edit_programs_all_three_forms(self):
        raw=ORACLE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'fcbec0d9d06d4185bd823442163b5ae3a3f05eef4fa77a32a64d948d9b35c18d')
        oracle=json.loads(raw)
        count=0
        for case in oracle['cases']:
            if case['id'].startswith('F-EDIT-'):continue
            spec=case['input'];expected=case['expected']
            if 'program_value' in spec:program=copy.deepcopy(spec['program_value'])
            else:
                definitions=copy.deepcopy(spec.get('definitions',{}))
                definitions['main']={'params':['x'],'body':copy.deepcopy(spec['body'])}
                pins=copy.deepcopy(spec.get('literal_pins',oracle['identities'].get(case['id'],{}).get('pins',{})))
                program={'schema':'bagaev-l2/1','entry':'main','definitions':definitions,'pins':pins}
                for change in spec.get('program_change',[]):
                    target=program
                    for key in change['path'][:-1]:target=target[key]
                    target[change['path'][-1]]=copy.deepcopy(change['value'])
            original=copy.deepcopy(program)
            for form in f.FORMS:
                with self.subTest(case=case['id'],form=form):
                    wire=f.encode(program,form)
                    self.assertEqual(f.decode(wire,form),program)
                    if 'reconstructed' in expected:self.assertEqual(f.decode(wire,form),expected['reconstructed'])
                    argument=self.fixture_argument(spec)
                    if 'error' in expected:
                        with self.assertRaises(l2.L2Error) as e:f.evaluate(wire,argument,form)
                        self.assertEqual(e.exception.code,expected['error'])
                    else:
                        checked=f.check(wire,form)
                        self.assertEqual(l2.program_digest(checked),oracle['identities'][case['id']]['snapshot'])
                        self.assertEqual(l2.evaluate(checked,argument),expected['value'])
                    self.assertEqual(program,original)
                    count+=1
            for extra in spec.get('after',[]):
                for form,wire in extra['raw_by_form'].items():
                    with self.assertRaises(l2.L2Error if form=='json' else f.FormError):f.decode(wire,form)
        self.assertEqual(count,126)

    def test_observed_semantic_charges_match_frozen_literals(self):
        """Observe the existing counter, without changing evaluator semantics.

        This process-local trace reads only numeric charge totals from the exact
        nested charge code object. It is not a timing/performance measurement.
        """
        raw=ORACLE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'fcbec0d9d06d4185bd823442163b5ae3a3f05eef4fa77a32a64d948d9b35c18d')
        oracle=json.loads(raw)
        charges=[v for v in l2.evaluate.__code__.co_consts if hasattr(v,'co_name') and v.co_name=='charge']
        self.assertEqual(len(charges),1)
        charge_code=charges[0]
        observed=0
        for case in oracle['cases']:
            expected=case['expected']
            target=next((expected[k] for k in ('steps','first_forbidden_step','attempted_work') if k in expected),None)
            if target is None:continue
            spec=case['input'];definitions=copy.deepcopy(spec.get('definitions',{}))
            definitions['main']={'params':['x'],'body':copy.deepcopy(spec['body'])}
            program={'schema':'bagaev-l2/1','entry':'main','definitions':definitions,
                     'pins':copy.deepcopy(oracle['identities'][case['id']]['pins'])}
            for form in f.FORMS:
                with self.subTest(case=case['id'],form=form):
                    checked=f.check(f.encode(program,form),form)
                    last=[0]
                    def local(frame,event,arg):
                        if event in ('return','exception'):last[0]=frame.f_locals['steps']
                        return local
                    def trace(frame,event,arg):
                        return local if frame.f_code is charge_code else None
                    previous=sys.gettrace()
                    argument=self.fixture_argument(spec)
                    try:
                        sys.settrace(trace)
                        if 'error' in expected:
                            with self.assertRaises(l2.L2Error) as error:l2.evaluate(checked,argument)
                            self.assertEqual(error.exception.code,expected['error'])
                        else:self.assertEqual(l2.evaluate(checked,argument),expected['value'])
                    finally:sys.settrace(previous)
                    self.assertEqual(last[0],target)
                    observed+=1
        self.assertEqual(observed,99)
        self.assertEqual(ORACLE.read_bytes(),raw)

if __name__=='__main__':unittest.main()
