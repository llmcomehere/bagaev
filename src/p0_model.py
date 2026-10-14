"""Finite serial checker for the frozen P0 model, not candidate execution."""
from copy import deepcopy
from . import p0_scenario as S
from . import p0_behavior as B
from . import p0_admission as A
from . import p0_handoff as H
from . import p0_orders as O

def check(oracle):
    fixtures=oracle['fixtures']
    cases={c['id']:c for c in oracle['cases']}
    assert len(cases)==len(oracle['cases'])==85
    bhv={k:{'input':{a:b for a,b in v['steps'][0].items() if a!='expect'},'expect':v['steps'][0]['expect']}
         for k,v in cases.items() if k.startswith('BHV-')}

    def resolve(x,trail=()):
        if type(x) is list:return [resolve(v,trail) for v in x]
        if type(x) is not dict:return deepcopy(x)
        if set(x)=={'$ref'}:
            key=x['$ref'];assert key not in trail
            return resolve(fixtures[key],trail+(key,))
        for token,field in (('$case_input','input'),('$case_expect','expect')):
            if set(x)=={token}:return deepcopy(bhv[x[token]][field])
        if '$case_results_ref' in x:
            assert set(x)<={'$case_results_ref','omit_case_ids','replace'}
            key=x['$case_results_ref'];assert key not in trail
            source=resolve(fixtures[key],trail+(key,));assert type(source) is list
            ids=[v['case_id'] for v in source];assert len(ids)==len(set(ids))
            omit=x.get('omit_case_ids',[]);replacements=resolve(x.get('replace',[]),trail)
            rid=[v['case_id'] for v in replacements]
            assert len(omit)==len(set(omit)) and len(rid)==len(set(rid))
            assert set(omit).isdisjoint(rid) and set(omit+rid)<=set(ids)
            replacements=dict(zip(rid,replacements))
            return [replacements.get(v['case_id'],v) for v in source if v['case_id'] not in omit]
        assert not any(k.startswith('$') for k in x)
        return {k:resolve(v,trail) for k,v in x.items()}

    def named(x):
        return resolve(fixtures[x]) if type(x) is str else resolve(x)

    def exact(a,b):
        if type(a) is not type(b):return False
        if type(b) is dict:return set(a)==set(b) and all(exact(a[k],v) for k,v in b.items())
        if type(b) is list:return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
        return a==b

    def project(a,b):
        assert type(a) is type(b),(a,b)
        if type(b) is dict:
            assert set(b)<=set(a)
            projected={}
            for k,v in b.items():
                if k=='allowed_serial_results':
                    assert sum(exact(a[k],alternative) for alternative in v)==1
                    projected[k]=deepcopy(a[k])
                else:projected[k]=project(a[k],v)
            return projected
        if type(b) is list:
            assert len(a)==len(b)
            return [project(x,y) for x,y in zip(a,b)]
        assert a==b,(a,b)
        return a

    rows=[]
    for cid in cases:
        case=deepcopy(cases[cid])
        initial=named(case['initial']) if 'initial' in case else None
        sessions=resolve(fixtures['sessions'])
        initial_before,sessions_before=deepcopy(initial),deepcopy(sessions)
        model=None
        if cid.startswith('HND-'):
            model=H.Handoff(initial or named('handoff-acceptance-state'),bhv)
        elif case.get('initial')=='admission-current':model=A.Admission(initial,sessions)
        elif initial is not None:model=S.Scenario(initial,sessions)
        observations=[]
        for index,raw in enumerate(case['steps']):
            # Criteria never enter an implementation event.
            step=resolve({k:v for k,v in raw.items() if k!='expect'})
            event=step['event']
            results=[]
            if event=='run_behavior':
                results=[B.run(step['operation'],step['input'],step.get('entry_id'),step.get('tag'))]
            elif event=='compare_migrations':results=[B.compare_migrations(step['left'],step['right'])]
            elif event=='validate_handoff':results=[model.validate(named(step['checkpoint']),step['successor_run'])]
            elif event=='accept_handoff':results=[model.accept(named(step['acceptance']))]
            elif event in ('retain_candidate','attempt_admission'):
                results=[model.command(event,step['session'],named(step['candidate']))]
            elif event=='revoke_grant':
                target=model if isinstance(model,A.Admission) else model.receiver
                target.fixture_revoke(step['principal'],step['grant'])
            elif event.startswith('advance_'):
                field=event[len('advance_'):]
                if isinstance(model,A.Admission):model.fixture_contract(step[field])
                else:model.receiver.fixture_revision(field,step[field])
            elif event=='deliver_transfer_concurrently':
                requests=[{'fixture_name':v['intent'],'intent':named(v['intent']),'session':v['session']} for v in step['requests']]
                results=O.transfer_orders(initial,sessions,requests)['serial_observations']
            elif event=='receiver_without_enforcement':
                results=[O.stale_receiver(initial,sessions,step['coordinator_epoch'],step['receiver_epoch'],named(step['late_request']))]
            else:
                for key in ('intent','request'):
                    if key in step:step[key]=named(step[key])
                results=[model.event(step)]
            if 'expect' in raw:
                wanted=resolve(raw['expect'])
                if type(wanted.get('response',{}).get('value')) is str:
                    wanted['response']['value']=named(wanted['response']['value'])
                assert results,'Expected observation not produced'
                for result in results:
                    observations.append({'step':index,'event':event,'projection':project(result,wanted)})
            assert exact(case,cases[cid])
            assert exact(initial,initial_before) and exact(sessions,sessions_before)
        rows.append({'case_id':cid,'status':'MATCHED','observations':observations})
    # Matcher refusal controls include special serial alternatives and bool/int confusion.
    bad=[(True,1),({}, {'missing':0}),([1],[1,2]),({'x':2},{'x':1}),
         ({'allowed_serial_results':[{'ok':True}]},{'allowed_serial_results':[[{'ok':1}]]}),
         ({'allowed_serial_results':[[{'ok':1}]]},{'allowed_serial_results':[[{'ok':1}]]})]
    for actual,wanted in bad:
        try:project(actual,wanted)
        except AssertionError:pass
        else:raise AssertionError('Wrong observation accepted')
    return {'status':'ALL_FROZEN_P0_MODEL_CASES_MATCHED', 'case_count':len(rows), 'projection_count':sum(len(r['observations']) for r in rows), 'cases':rows, 'checker_refusals':len(bad)}
