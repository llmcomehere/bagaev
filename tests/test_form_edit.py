"""Frozen edit-frame traces and independently derived boundary/ownership checks."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import bagaev_forms as forms
import bagaev_form_edit as edit
import bagaev_l2 as l2
ROOT=Path(__file__).resolve().parents[1]

class EditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/'examples/probes/form-oracle.json').read_bytes()
        if hashlib.sha256(cls.raw).hexdigest()!='fcbec0d9d06d4185bd823442163b5ae3a3f05eef4fa77a32a64d948d9b35c18d':
            raise RuntimeError('frozen form oracle identity changed')
        cls.oracle=json.loads(cls.raw)

    @staticmethod
    def change(value, changes):
        value=copy.deepcopy(value)
        for change in changes:
            current=value
            for key in change['path'][:-1]:current=current[key]
            if 'value' in change:current[change['path'][-1]]=copy.deepcopy(change['value'])
            else:del current[change['path'][-1]]
        return value

    def frame(self,spec,form):
        if 'raw_frame' in spec:return spec['raw_frame']
        if spec.get('frame_recipe')=='F-FRAME-BYTES':return ' '*2097153
        if spec.get('frame_recipe')=='F-FRAME-DEPTH':return '['*8+'null'+']'*8
        if 'frame_value' in spec:return json.dumps(spec['frame_value'],ensure_ascii=True)
        frame=copy.deepcopy(self.oracle['frames'][spec['frame']]);frame['form']=form
        patch=copy.deepcopy(self.oracle['patches'][frame.pop('patch_ref')])
        patch=copy.deepcopy(spec.get('patch_value',patch))
        patch=self.change(patch,spec.get('patch_change',[]))
        frame['patch']=' '*1048577 if spec.get('patch_recipe')=='F-PATCH-BYTES' else forms.encode(patch,form,mode='patch').decode()
        frame=self.change(frame,spec.get('frame_change',[]))
        return json.dumps(frame,ensure_ascii=True,separators=(',',':'))

    def assert_error(self, original, wire, code, location=None, candidate_map=None):
        with self.assertRaises((l2.L2Error,forms.FormError)) as e:
            edit.draft(original,wire,candidate_map=candidate_map)
        self.assertEqual(e.exception.code,code)
        self.assertEqual(getattr(e.exception,'location',None),location)

    def test_complete_frozen_edit_traces_in_all_forms(self):
        count=0
        for case in self.oracle['cases']:
            if not case['id'].startswith('F-EDIT-'):continue
            stages=[{k:v for k,v in case['input'].items() if k!='after'}]+case['input'].get('after',[])
            expects=[case['expected']]+case['expected'].get('after',[])
            self.assertEqual(len(stages),len(expects))
            for stage,(spec,expected) in enumerate(zip(stages,expects)):
                for form in forms.FORMS:
                    with self.subTest(case=case['id'],stage=stage,form=form):
                        original=copy.deepcopy(self.oracle['snapshots'][spec['original']]);before=copy.deepcopy(original)
                        wire=self.frame(spec,form)
                        if 'code' in expected:self.assert_error(original,wire,expected['code'],expected['location'],spec.get('candidate_map'))
                        else:
                            result=edit.draft(original,wire)
                            exact={k:expected[k] for k in ('schema','status','base','target','admission')}
                            exact['program']=self.oracle['snapshots'][expected['program']]
                            exact['patch']=self.oracle['patches'][expected['patch']]
                            self.assertEqual(result,exact)
                            self.assertIs(result['admission'],False)
                            result['program']['definitions']['main']['body']=99
                            result['patch']['add']['helper']['body']=99
                            self.assertEqual(self.oracle['patches']['P01']['add']['helper']['body'],1)
                        self.assertEqual(original,before)
                        count+=1
        self.assertEqual(count,51)
        self.assertEqual((ROOT/'examples/probes/form-oracle.json').read_bytes(),self.raw)

    def test_original_validation_precedes_all_frame_work(self):
        self.assert_error({},b' '*2097153,'L2_PROGRAM')
        self.assert_error({},b'\xff','L2_PROGRAM')

    def test_candidate_binding_is_exact_and_precedes_base_cas(self):
        patch=self.oracle['patches']['P01'];pin='sha256:'+hashlib.sha256(json.dumps(patch,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.assertEqual(edit._content_pin(patch),pin)
        spec={'frame':'E0','frame_change':[{'path':['candidate_id'],'value':'choice'}]}
        for form in forms.FORMS:
            wire=self.frame(spec,form);mapping={'choice':{'kind':'patch','pin':pin}};saved=copy.deepcopy(mapping)
            result=edit.draft(self.oracle['snapshots']['S0'],wire,candidate_map=mapping)
            self.assertEqual(result['program'],self.oracle['snapshots']['S1']);self.assertEqual(mapping,saved)
            self.assert_error(self.oracle['snapshots']['S1'],wire,'L2_STALE',candidate_map=mapping)
            for bad in [None,{},[],{'choice':{'kind':'program','pin':pin}},{'choice':{'kind':'patch','pin':'sha256:'+'0'*64}}]:
                self.assert_error(self.oracle['snapshots']['S1'],wire,'FORM_CANDIDATE','/candidate_id',bad)

    def test_patch_root_string_never_reparsed_and_base_order(self):
        original=self.oracle['snapshots']['S0'];patch=self.oracle['patches']['P01']
        for form in forms.FORMS:
            spec={'frame':'E0','patch_value':json.dumps(patch),'frame_change':[{'path':['base'],'value':'sha256:'+'0'*64}]}
            self.assert_error(original,self.frame(spec,form),'L2_PATCH')
            for changes in [[{'path':['add'],'value':{}},{'path':['replace'],'value':{}}],[{'path':['add','main'],'value':{'params':[],'body':0}}]]:
                spec={'frame':'E0','patch_change':changes,'frame_change':[{'path':['base'],'value':'sha256:'+'0'*64}]}
                self.assert_error(original,self.frame(spec,form),'L2_PATCH')

    def test_outer_syntax_and_field_order(self):
        original=self.oracle['snapshots']['S0']
        for wire in [b'\xff',b'\xef\xbb\xbf{}','{}{}','{"schema":NaN}','{"schema":1e999}']:
            self.assert_error(original,wire,'FORM_SYNTAX','')
        for name in ['schema','form','patch']:
            spec={'frame':'E0','frame_change':[{'path':[name],'value':'\ud800'}]}
            self.assert_error(original,self.frame(spec,'json'),'FORM_SHAPE','/'+name)
        self.assert_error(original,'{"x":"\\ud800"}','FORM_SHAPE','')
        self.assert_error(original,'{"'+('\\ud800')+'":'+('['*8)+'0'+(']'*8)+'}','FORM_BOUNDS','')
        self.assert_error(original,'['+','.join(['0']*32)+']','FORM_BOUNDS','')

    def test_patch_escape_boundary_and_detached_original_snapshot(self):
        original=l2.check_program(self.oracle['snapshots']['S0']);pin=original.digest
        spec={'frame':'E0','patch_change':[{'path':['add','helper','body'],'value':'\ud800'}]}
        for form in forms.FORMS:
            self.assert_error(original,self.frame(spec,form),'L2_PROGRAM')
        self.assertEqual(original.digest,pin)
        good=edit.draft(original,self.frame({'frame':'E0'},'json'))
        good['patch']['replace'].clear();good['program']['pins'].clear()
        self.assertEqual(original.digest,pin)
        self.assertEqual(l2.evaluate(original,None),0)

if __name__=='__main__':unittest.main()
