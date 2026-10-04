"""Context orchestration tests; the kernel checker is explicit test-double input.

These tests do not establish a kernel compiler's correctness. A separate host
integration can replace CHECKER_CACHE with exact independently checked bytes.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import bagaev_probe_context as c
import bagaev_l2 as l2
ROOT=Path(__file__).resolve().parents[1]
CHECKER_CACHE=None

def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()

def pin(value):return 'sha256:'+hashlib.sha256(canonical(value)).hexdigest()

class ContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/'examples/probes/context-oracle.json').read_bytes()
        if hashlib.sha256(cls.raw).hexdigest()!='090d64ba08ca17d9f61f4a8bf7b91dda0a827ee6c6fb71b49764d49cdc5c1661':raise RuntimeError('frozen context oracle changed')
        cls.oracle=json.loads(cls.raw)

    def parts(self, spec):
        parts={k:copy.deepcopy(self.oracle[k]) for k in ['context','expectation','evidence','request','response']}
        for change in spec.get('changes',[]):
            target=parts
            for key in change['path'][:-1]:target=target[key]
            if change.get('omit'):del target[change['path'][-1]]
            else:target[change['path'][-1]]=copy.deepcopy(change['value'])
        for name in spec.get('rehash',[]):
            self.assertEqual(name,'context.candidate_set')
            rows=[{k:r[k] for k in ('id','kind','state','pin')} for r in parts['context']['candidates']]
            parts['context']['candidate_set']=pin({'schema':'probe-candidate-set/1','candidates':rows})
        return parts

    def checker(self, program):
        wire=canonical(program)
        if CHECKER_CACHE is not None:
            if wire not in CHECKER_CACHE:raise c.ContextUnavailable('program absent from externally checked cache')
            return CHECKER_CACHE[wire]
        # A test double restricted to this one explicit valid fixture. Never
        # accepts arbitrary programs or asserts native validation happened here.
        if program!=self.oracle['baseline']:raise c.KernelRefusal('IR_SHAPE','')
        return wire

    def test_frozen_context_phase_refusals(self):
        names=['C-MISSING-EXPECTATION','C-STALE-SNAPSHOT','C-UNKNOWN-AXIS','C-MISSING-SOURCE','C-SOURCE-PIN','C-SOURCE-STALE','C-REFERENCE-SPAN','C-OBLIGATION-PIN','C-MISSING-OBLIGATION','C-REMAPPED','C-CANDIDATE-PIN','C-DUPLICATE','C-OVERSIZE']
        cases={x['id']:x for x in self.oracle['cases']}
        for name in names:
            with self.subTest(case=name):
                case=cases[name];parts=self.parts(case['input']);expected=case['expected']
                raw=b' '*4194305 if name=='C-OVERSIZE' else canonical(parts['context'])
                exp=canonical(parts['expectation']) if 'expectation' in parts else None
                with self.assertRaises(c.ContextError) as e:c.inspect(raw,exp,kernel_checker=self.checker)
                self.assertEqual((e.exception.code,e.exception.location),(expected['code'],expected['location']))
        self.assertEqual((ROOT/'examples/probes/context-oracle.json').read_bytes(),self.raw)

    def test_valid_context_retains_unknowns_and_has_no_admission(self):
        context=canonical(self.oracle['context']);expected=canonical(self.oracle['expectation'])
        result=c.inspect(context,expected,kernel_checker=self.checker)
        self.assertEqual(result['snapshot'],self.oracle['context']['snapshot'])
        self.assertEqual(result['candidate_set'],self.oracle['context']['candidate_set'])
        self.assertEqual(result['unknowns'],['u']);self.assertEqual(result['open_effects'],['e'])
        self.assertIs(result['admission'],False);self.assertEqual(result['model_calls'],0)
        result['unknowns'].clear()
        self.assertEqual(c.inspect(context,expected,kernel_checker=self.checker)['unknowns'],['u'])

    def test_no_checker_fallback_or_changed_checked_bytes(self):
        raw=canonical(self.oracle['context']);exp=canonical(self.oracle['expectation'])
        with self.assertRaises(c.ContextUnavailable):c.inspect(raw,exp)
        for checker in [lambda _: b'{}',lambda _: True]:
            with self.assertRaises(c.ContextUnavailable):c.inspect(raw,exp,kernel_checker=checker)
        def refused(_):raise c.KernelRefusal('IR_REFERENCE','/entry')
        with self.assertRaises(c.KernelRefusal) as e:c.inspect(raw,exp,kernel_checker=refused)
        self.assertEqual(e.exception.location,'/baseline/entry')

    def test_duplicate_json_precedes_context_shape_and_missing_expectation(self):
        for raw in [b'{"schema":0,"schema":1}',b'\xff',b'{}{}']:
            with self.assertRaises(c.ContextError) as e:c.inspect(raw,None)
            self.assertEqual(e.exception.code,'CTX_JSON')
        with self.assertRaises(c.ContextError) as e:c.inspect(b'{}',None)
        self.assertEqual(e.exception.code,'CTX_SHAPE')

    def test_utf8_span_boundaries_and_required_obligation_staleness(self):
        context=copy.deepcopy(self.oracle['context']);expected=copy.deepcopy(self.oracle['expectation'])
        context['sources'][0]['text']='éx';sp='sha256:'+hashlib.sha256('éx'.encode()).hexdigest()
        context['sources'][0]['pin']=sp;expected['sources'][0]['pin']=sp
        for name in ['obligations','open_effects']:
            ref=context[name][0]['refs'][0];ref.update({'pin':sp,'start':0,'end':1})
        with self.assertRaises(c.ContextError) as e:c.inspect(canonical(context),canonical(expected),kernel_checker=self.checker)
        self.assertEqual((e.exception.code,e.exception.location),('CTX_SHAPE','/obligations/0/refs/0'))
        expected=copy.deepcopy(self.oracle['expectation']);expected['obligations'][0]['pin']='sha256:'+'0'*64
        with self.assertRaises(c.ContextError) as e:c.inspect(canonical(self.oracle['context']),canonical(expected),kernel_checker=self.checker)
        self.assertEqual((e.exception.code,e.exception.location),('CTX_STALE','/obligations/0/pin'))

    def test_all_frozen_exchange_cases_and_ordered_traces(self):
        count=0
        for case in self.oracle['cases']:
            spec=case['input'];expected=case['expected'];parts=self.parts(spec)
            context=b' '*4194305 if spec.get('raw_context_recipe') else canonical(parts['context'])
            expectation=canonical(parts['expectation']) if 'expectation' in parts else None
            evidence=canonical(parts['evidence']) if 'evidence' in parts else None
            if 'trace' in spec:
                outputs=[]
                for step in spec['trace']:
                    req=copy.deepcopy(parts['request']);req.update(step.get('request_change',{}))
                    response=copy.deepcopy(parts['response']);response.update(step.get('response_change',{}));response['request']=pin(req)
                    result=c.process(context,expectation,evidence=evidence,request=canonical(req),response=canonical(response),kernel_checker=self.checker)
                    event=result['events'][-1];outputs.append({k:v for k,v in event.items() if k!='phase'})
                    self.assertEqual(result['unknowns'],expected['unknowns']);self.assertEqual(result['open_effects'],expected['open_effects'])
                self.assertEqual(outputs,expected['events'])
                self.assertEqual(parts['context']['candidate_set'],expected.get('old_map',self.oracle['context']['candidate_set']))
            elif 'code' in expected:
                with self.subTest(case=case['id']),self.assertRaises(c.ContextError) as e:
                    c.process(context,expectation,evidence=evidence,request=canonical(parts['request']),response=canonical(parts['response']),kernel_checker=self.checker)
                self.assertEqual((e.exception.code,e.exception.location),(expected['code'],expected['location']))
            else:
                result=c.process(context,expectation,evidence=evidence,request=canonical(parts['request']),response=canonical(parts['response']),kernel_checker=self.checker)
                for key in ('events','unknowns','open_effects'):self.assertEqual(result[key],expected[key])
                self.assertIs(result['admission'],False);self.assertEqual(result['model_calls'],0)
            count+=1
        self.assertEqual(count,23)
        self.assertEqual((ROOT/'examples/probes/context-oracle.json').read_bytes(),self.raw)

    def test_l2_program_and_patch_choices_use_actual_checker(self):
        context=copy.deepcopy(self.oracle['context']);expected=copy.deepcopy(self.oracle['expectation'])
        baseline=json.loads((ROOT/'examples/l2/catalog.json').read_bytes())
        patch=json.loads((ROOT/'examples/l2/catalog-01.patch').read_bytes())
        for value in (context,expected):
            value['axes']['semantic']=value['axes']['ir']='bagaev-l2/1'
            value['snapshot']=pin(baseline)
        expected['baseline']=baseline
        context['candidates']=[{'id':'a','kind':'program','state':'choice','content':copy.deepcopy(baseline),'pin':pin(baseline)},
                               {'id':'b','kind':'patch','state':'choice','content':patch,'pin':pin(patch)}]
        def bind():
            for row in context['candidates']:row['pin']=pin(row['content'])
            context['candidate_set']=pin({'schema':'probe-candidate-set/1','candidates':[{k:r[k] for k in ('id','kind','state','pin')} for r in context['candidates']]})
            expected['candidate_set']=context['candidate_set']
        bind()
        before=copy.deepcopy((context,expected))
        result=c.process(canonical(context),canonical(expected))
        self.assertIs(result['admission'],False)
        self.assertEqual((context,expected),before)
        # An externally matched content hash cannot replace semantic patch CAS.
        context['candidates'][1]['content']['base']='sha256:'+'0'*64;bind()
        with self.assertRaises(l2.L2Error):c.inspect(canonical(context),canonical(expected))
        # Program pins remain semantic input, not repaired by envelope binding.
        context,expected=copy.deepcopy(before)
        first=next(iter(context['candidates'][0]['content']['pins']))
        context['candidates'][0]['content']['pins'][first]='sha256:'+'0'*64;bind()
        with self.assertRaises(l2.L2Error):c.inspect(canonical(context),canonical(expected))

    def test_response_binding_evidence_and_unknown_results_do_not_admit(self):
        base={k:copy.deepcopy(self.oracle[k]) for k in ('context','expectation','evidence','request','response')}
        def run(parts):return c.process(canonical(parts['context']),canonical(parts['expectation']),evidence=canonical(parts['evidence']),request=canonical(parts['request']),response=canonical(parts['response']),kernel_checker=self.checker)
        for field,code in [('request','CTX_STALE'),('context','CTX_STALE'),('snapshot','CTX_STALE'),('candidate_set','CTX_REMAPPED')]:
            parts=copy.deepcopy(base);parts['response'][field]='sha256:'+'0'*64
            with self.assertRaises(c.ContextError) as e:run(parts)
            self.assertEqual((e.exception.code,e.exception.location),(code,'/'+field))
        for label in ('negative','indeterminate','not-run','supported'):
            parts=copy.deepcopy(base);parts['evidence']['records'][0]['result']=label
            result=run(parts);self.assertEqual(result['events'][1]['records'][0]['result'],label);self.assertIs(result['admission'],False)
        parts=copy.deepcopy(base);parts['response'].update({'outcome':'refused','candidate_id':None,'code':'CTX_UNSUPPORTED'})
        result=run(parts);self.assertEqual(result['events'][-1]['outcome'],'refused');self.assertIs(result['events'][-1]['admission'],False)
        parts=copy.deepcopy(base);parts['response']['content']={}
        with self.assertRaises(c.ContextError) as e:run(parts)
        self.assertEqual(e.exception.code,'CTX_SHAPE')

if __name__=='__main__':unittest.main()
