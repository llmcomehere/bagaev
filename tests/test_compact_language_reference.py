"""Primary reading budget and source-grounded coverage; no model-fit claim."""
from pathlib import Path
import ast,json,re,sys,unittest
T=Path(__file__).resolve().parents[1];sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_form as form
import bagaev_component_record_list_form as component
import bagaev_l2_filter as l2
import bagaev_l0 as l0
class CompactReference(unittest.TestCase):
    def setUp(self):self.text=(T/'docs/choose-and-start.md').read_text()
    def test_primary_budget_and_existing_entry_anchors(self):
        self.assertLessEqual(len(self.text.encode()),32768);readme=(T/'README.md').read_text();self.assertLessEqual(len(readme.encode()),4096)
        for h in ['Choose a route from the task','Start with readable typed source','Finish one change','Decide what to try next']:self.assertIn('## '+h,self.text)
        for h in ['Why a language for change?','Start with one real change','What exists today','Help test the thesis']:self.assertIn('## '+h,readme)
        self.assertIn('not measured tokens',self.text);self.assertIn('No runtime semantics changed here',self.text)
    def test_actual_intrinsic_coverage(self):
        for name in form.INTRINSICS:self.assertIn('`'+name+'(',self.text,name)
        for token in ['fold (N, initial)','let x = value in body','match (value)','OptionInt64 omit_none','65,536','2,048','32,768','RR_RECORD_LIST_ITEMS','declaration order','sorted field-name order','--callee-context','--source-body','record_draft.py']:
            self.assertIn(token,self.text)
    def test_legacy_operation_coverage(self):
        section=self.text.split('## Existing dynamic L2 programs',1)[1].split('## Original L0 compatibility',1)[0]
        for path in ['src/bagaev_l2.py','src/bagaev_l2_filter.py']:
            tree=ast.parse((T/path).read_text());tables=[ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='arities' for t in n.targets)]
            self.assertEqual(len(tables),1)
            for op in set(tables[0])|{'call','array','and','or'}:self.assertIn('["'+op+'",',section,op)
        section=self.text.split('## Original L0 compatibility',1)[1]
        for name in l0.OP_FIELDS:self.assertIn('| '+name+' |',section,name)
    def test_complete_literal_examples_parse(self):
        blocks=re.findall(r'^```([^\n]*)\n(.*?)^```',self.text,re.M|re.S);seen=[]
        for language,source in blocks:
            if language=='bagaev':
                p=form.decode(source);self.assertEqual(p['entry'],'total');self.assertEqual(p['lists']['Items']['capacity'],16);seen.append(language)
            elif language=='component':
                p=component.decode(source);self.assertEqual(p['schema'],'bagaev-component-source/2');self.assertEqual(p['component']['replace_fields'],['quantity']);seen.append(language)
            elif language=='l2-draft':
                l2.prepare_program(json.loads(source));seen.append(language)
        self.assertEqual(seen,['bagaev','component','l2-draft'])
if __name__=='__main__':unittest.main()
