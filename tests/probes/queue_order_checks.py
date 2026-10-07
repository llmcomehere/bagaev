"""Finite public queue example checks; run only in an authorized profile."""
from pathlib import Path
import copy,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src import bagaev_l2 as l2
from src import bagaev_l2_backend as backend
from queue_order_baseline import ordinary

def main():
    d=ROOT/'examples/l2/queue'
    paths=[d/'initial.json',d/'missing-last.patch',d/'cases.json',d/'input.json']
    original={p:p.read_bytes() for p in paths}
    base=json.loads(original[paths[0]]);patch=json.loads(original[paths[1]])
    updated=l2.apply_patch(base,patch)
    cases=json.loads(original[paths[2]])['cases']
    count=0
    for revision,program in enumerate([l2.check_program(base),updated]):
        artifact=backend.compile_program(program)
        verified=backend.verify_artifact(artifact,program)
        namespace={'__name__':'queue_compiled_example'}
        exec(compile(verified,'<queue-example>','exec'),namespace)
        for case in cases:
            argument=copy.deepcopy(case['input']);before=copy.deepcopy(argument)
            expected=case[f'v{revision}']
            assert ordinary(argument,revision)==expected
            assert l2.evaluate(program,argument)==expected
            assert namespace['evaluate'](argument)==expected
            assert argument==before
            count+=1
    try:l2.apply_patch(updated,patch)
    except l2.L2Error as error:assert error.code=='L2_STALE'
    else:raise AssertionError('stale patch accepted')
    current=l2.program_value(updated)
    controls=[('missing-change',base['definitions']['key']),('urgency',copy.deepcopy(current['definitions']['key']))]
    controls[1][1]['body'][1]=0
    by_id={c['id']:c for c in cases}
    for case_id,wrong_key in controls:
        mutation=l2.prepare_patch(updated,{}, {'key':wrong_key})
        actual=l2.evaluate(l2.apply_patch(updated,mutation),by_id[case_id]['input'])
        assert actual=={'kind':'ok','order':['a','b']} and actual!=by_id[case_id]['v1']
    assert original=={p:p.read_bytes() for p in paths}
    print(json.dumps({'status':'PASSED','literal_cases':len(cases),'revisions':2,'comparisons':count,'normal_wrong_controls':2,'stale_patch_refused':True}))

if __name__=='__main__':main()
