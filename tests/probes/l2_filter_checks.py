"""Own finite new-profile checks, run only under the approved no-network profile."""
from pathlib import Path
import argparse,copy,hashlib,json,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/l2-filter'
sys.path.insert(0,str(T))
from src import bagaev_l2_filter as new
from src import bagaev_l2 as old
from src import bagaev_l2_filter_backend as backend
from src import bagaev_l2_backend as old_backend
canonical=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()

def program(body,version=2):
    definition={'params':['x'],'body':body}
    raw=json.dumps({'schema':f'bagaev-l2-definition/{version}','definition':definition,'dependencies':{}},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    return {'schema':f'bagaev-l2/{version}','entry':'main','definitions':{'main':definition},'pins':{'main':'sha256:'+hashlib.sha256(raw).hexdigest()}}

def ordinary(arg,field):
    if type(arg)is not list:raise ValueError('L2_TYPE')
    if len(arg)>256:raise ValueError('L2_BOUNDS')
    out=[]
    for item in arg:
        if type(item)is not dict:raise ValueError('L2_TYPE')
        if field not in item:raise ValueError('L2_FIELD')
        if type(item[field])is not bool:raise ValueError('L2_TYPE')
        if item[field]:out.append(copy.deepcopy(item))
    return out

def observe(fn):
    try:return {'value':fn()}
    except (new.L2Error,old.L2Error,ValueError) as e:return {'error':getattr(e,'code',str(e))}

def containers(x):
    pending=[x];ids=set()
    while pending:
        q=pending.pop()
        if type(q) in (dict,list):ids.add(id(q));pending.extend(q.values() if type(q)is dict else q)
    return ids

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);R=parser.parse_args().output
    assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir()
    original=json.loads((D/'legacy-modules.json').read_bytes())['sha256']
    assert all(hashlib.sha256((T/n).read_bytes()).hexdigest()==h for n,h in original.items())
    frozen=json.loads((D/'manifest.json').read_bytes())['sha256'];assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==h for n,h in frozen.items())
    rows=[]
    for case in json.loads((D/'cases.json').read_bytes())['cases']:
        field='keep' if case['predicate']=='keep-field' else 'absent'
        source=program(['filter',['var','x'],'item',['get',['var','item'],field]])
        checked=new.check_program(source);artifact=backend.compile_program(checked);raw=backend.verify_artifact(artifact,checked)
        namespace={'__name__':'owned_filter_lowering'};exec(compile(raw,'<owned-filter>','exec'),namespace)
        inp=copy.deepcopy(case['input']);before=canonical(inp);expected={'error':case['error']} if 'error'in case else {'value':case['expected']}
        a=observe(lambda:ordinary(inp,field));b=observe(lambda:new.evaluate(checked,inp))
        try:c={'value':namespace['evaluate'](inp)}
        except namespace['L2RuntimeError'] as e:c={'error':e.code}
        assert canonical(a)==canonical(b)==canonical(c)==canonical(expected),(case['id'],a,b,c,expected)
        assert canonical(inp)==before
        for got in (a,b,c):
            if 'value'in got:assert not containers(inp)&containers(got['value'])
        rows.append({'id':case['id'],'observation':b})
    static=[]
    for case in json.loads((D/'static-cases.json').read_bytes())['cases']:
        got=observe(lambda:new.check_program(program(case['body'])))
        assert got=={'error':case['error']},(case,got)
        static.append(case['id'])
    body=['filter',['var','x'],'item',True]
    for checker,source in [(old.check_program,program(body,1)),(old.check_program,program(body)),(new.check_program,program(['var','x'],1))]:
        assert observe(lambda:checker(source))=={'error':'L2_PROGRAM'}
    p1=program(['var','x'],1);p2=program(['var','x'],2)
    a1=old_backend.compile_program(p1);a2=backend.compile_program(p2);assert a1!=a2
    for bad in (a1,a2+b' '):
        try:backend.verify_artifact(bad,p2)
        except backend.ArtifactError:pass
        else:raise AssertionError('wrong artifact admitted')
    assert all(hashlib.sha256((T/n).read_bytes()).hexdigest()==h for n,h in original.items())
    result={'status':'PASSED','runtime_cases':len(rows),'static_cases':len(static),'profile_refusals':3,'artifact_refusals':2,'old_files_unchanged':len(original),'rows':rows,'scope':'Separate /2 pure profile only; no Store, native, model or production acceptance.'}
    (R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))

if __name__=='__main__':main()
