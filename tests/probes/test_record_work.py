"""Literal tests for conditional work analysis; no evaluator dispatch."""
from pathlib import Path
import sys, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from bagaev_record_work import analyze


def summarize(negated=False):
    left = ['list.len', ['use', 'ys']]
    right = ['list.len', ['arg', 'xs']]
    predicate = ['not', ['eq', right, left]] if negated else ['lt', left, right]
    return ['let', 'ys', ['list.unique', ['arg', 'xs']],
            ['record', 'Report', predicate, ['use', 'ys']]]


class Work(unittest.TestCase):
    def test_frozen_literal_bounds(self):
        for n,b,w,fit in ((0,0,10,True),(1,0,11,True),(1,4,19,True),
                          (64,479,65418,True),(64,480,65546,False),
                          (64,4096,528394,False)):
            args={'xs':{'type':'TextList','items':n,'bytes':b}}
            r=analyze(summarize(),args)
            self.assertEqual(r['upper_work'],w)
            self.assertEqual(r['fits_work_budget'],fit)
            self.assertFalse(r['semantic_check']);self.assertFalse(r['execution_admission'])
            self.assertTrue(r['requires_checked_program'])
            self.assertEqual(analyze(summarize(True),args)['upper_work'],w+1)

    def test_unknown_never_has_bound(self):
        for e in (['call','f'],['loop'],['if'],['list.contains'],['use','missing'],
                  ['eq',['text','x'],['text','y']],['not',['int',1]],None):
            r=analyze(e,{})
            self.assertEqual(r['status'],'UNKNOWN');self.assertNotIn('upper_work',r)

    def test_bad_shapes(self):
        for shape in ({'type':'TextList','items':True,'bytes':0},
                      {'type':'TextList','items':0,'bytes':1},
                      {'type':'TextList','items':65,'bytes':0},
                      {'type':'TextList','items':64,'bytes':4097},
                      {'type':'TextList','items':1,'bytes':1025},
                      {'type':'Int64','extra':1},{}):
            self.assertEqual(analyze(['arg','x'],{'x':shape})['status'],'UNKNOWN')

    def test_extra_charges_and_local_shadow(self):
        self.assertEqual(analyze(['text','é'],{})['upper_work'],3)
        self.assertEqual(analyze(['list.increasing',['arg','xs']],
                         {'xs':{'type':'TextList','items':3,'bytes':5}})['upper_work'],15)
        e=['let','a',['int',1],['let','a',['bool',False],['not',['use','a']]]]
        self.assertEqual(analyze(e,{})['upper_work'],6)

    def test_depth_and_occurrence_bounds(self):
        e=['bool',True]
        for _ in range(32):e=['not',e]
        self.assertEqual(analyze(e,{})['reason'],'analysis-bounds')
        e=['int',0]
        for _ in range(4):e=['record','R']+[e]*8
        self.assertEqual(analyze(e,{})['reason'],'analysis-bounds')
        self.assertEqual(analyze(['text','x'*257],{})['status'],'UNKNOWN')
        self.assertEqual(analyze(['text','\ud800'],{})['status'],'UNKNOWN')

    def test_conditional_maximum_and_shape_join(self):
        args={'c':{'type':'Bool'},'xs':{'type':'TextList','items':3,'bytes':5}}
        c=['arg','c'];xs=['arg','xs']
        self.assertEqual(analyze(['if',c,['int',1],['int',2]],args)['upper_work'],3)
        branch=['if',c,['list.unique',xs],xs]
        self.assertEqual(analyze(branch,args)['upper_work'],43)
        self.assertEqual(analyze(['list.unique',branch],args)['upper_work'],83)
        self.assertEqual(analyze(['if',c,['text','é'],['text','abc']],args)['upper_work'],6)
        # Joining independent maxima must not select only the cheaper arm.
        args['ys']={'type':'TextList','items':4,'bytes':1}
        self.assertEqual(analyze(['list.unique',['if',c,xs,['arg','ys']]],args)['upper_work'],60)

    def test_conditional_unknown_arms_and_types(self):
        for e in (['if',['bool',False],['call','missing'],['int',0]],
                  ['if',['bool',True],['int',1],['bool',False]],
                  ['if',['int',0],['int',1],['int',2]]):
            r=analyze(e,{})
            self.assertEqual(r['status'],'UNKNOWN');self.assertNotIn('upper_work',r)

    def test_helper_scope_and_repeated_cost(self):
        args={'xs':{'type':'TextList','items':3,'bytes':5}}
        functions={'dedup':{'params':[['x','TextList']],'result':'TextList',
                            'body':['list.unique',['arg','x']]},
                   'wrap':{'params':[['u','TextList']],'result':'TextList',
                           'body':['call','dedup',['arg','u']]},
                   'identity':{'params':[['x','Int64']],'result':'Int64','body':['arg','x']}}
        call=['call','dedup',['arg','xs']]
        self.assertEqual(analyze(call,args,functions)['upper_work'],43)
        self.assertEqual(analyze(['call','wrap',['arg','xs']],args,functions)['upper_work'],45)
        self.assertEqual(analyze(['let','y',call,['call','dedup',['use','y']]],args,functions)['upper_work'],87)
        self.assertEqual(analyze(['call','identity',['int',1]],{},functions)['upper_work'],3)
        self.assertEqual(analyze(call,args)['status'],'UNKNOWN')

    def test_helper_refusals(self):
        args={'xs':{'type':'TextList','items':3,'bytes':5}}
        for body in (['arg','xs'],['use','outer'],['call','f',['arg','x']]):
            funcs={'f':{'params':[['x','TextList']],'result':'TextList','body':body}}
            r=analyze(['let','outer',['arg','xs'],['call','f',['arg','xs']]],args,funcs)
            self.assertEqual(r['status'],'UNKNOWN');self.assertNotIn('upper_work',r)
        funcs={'f':{'params':[],'result':'Int64','body':['call','g']},
               'g':{'params':[],'result':'Int64','body':['call','f']}}
        self.assertEqual(analyze(['call','f'],{},funcs)['reason'],'call-cycle')
        funcs={'f':{'params':[['x','Int64']],'result':'Int64','body':['arg','x']}}
        for call in (['call','f'],['call','f',['bool',True]]):
            self.assertEqual(analyze(call,{},funcs)['status'],'UNKNOWN')
        funcs['f']['result']='Report'
        self.assertEqual(analyze(['call','f',['int',1]],{},funcs)['status'],'UNKNOWN')

    def test_expanded_call_budget(self):
        funcs={'f0':{'params':[],'result':'Bool','body':['bool',True]}}
        for i in range(1,12):
            funcs['f'+str(i)]={'params':[],'result':'Bool',
                              'body':['eq',['call','f'+str(i-1)],['call','f'+str(i-1)]]}
        r=analyze(['call','f11'],{},funcs)
        self.assertEqual(r['status'],'UNKNOWN');self.assertEqual(r['reason'],'analysis-bounds')


if __name__=='__main__':unittest.main()
