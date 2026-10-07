"""Own borrowed-value/work-budget supplement; not additional pre-code cases."""
from pathlib import Path
import argparse,hashlib,json,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/l2-filter'
sys.path.insert(0,str(T))
from src import bagaev_l2_filter as language
from src import bagaev_l2_filter_backend as backend
from l2_filter_checks import program

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);R=parser.parse_args().output
    assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir()
    manifest=json.loads((D/'manifest.json').read_bytes())['sha256']
    assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
    raw=(D/'boundary-cases.json').read_bytes()
    rows=[]
    for c in json.loads(raw)['cases']:
        name=c['id'];body=['filter',['var','x'],'item',['get',['var','item'],'keep']]
        if name=='empty-nonboolean':body=['filter',['var','x'],'item',1];argument=[]
        elif name=='float-predicate':argument=[{'keep':0.0}]
        elif 'depth' in name:
            depth=5000 if name=='unselected-depth5000' else 100;payload=None
            for _ in range(depth):payload=[payload]
            argument=[{'keep':name.startswith('selected'),'payload':payload}]
        elif 'surrogate'in name:argument=[{'keep':name.startswith('selected'),'payload':'\ud800'}]
        else:
            n=128 if name=='nested-work-under128' else 256;argument=list(range(n))
            body=['filter',['var','x'],'outer',['eq',['length',['filter',['var','x'],'inner',['eq',['var','inner'],['var','inner']]]],n]]
        checked=language.check_program(program(body));artifact=backend.compile_program(checked);code=backend.verify_artifact(artifact,checked);ns={'__name__':'owned_filter_boundary'};exec(compile(code,'<owned-filter-boundary>','exec'),ns)
        expected={'error':c['error']} if 'error'in c else {'value':list(range(128)) if 'recipe_expected'in c else c['expected']}
        observations=[]
        for engine,fn,error in [('reference',lambda:language.evaluate(checked,argument),language.L2Error),('cpython',lambda:ns['evaluate'](argument),ns['L2RuntimeError'])]:
            try:got={'value':fn()}
            except error as e:got={'error':e.code}
            assert got==expected,(name,engine,got,expected);observations.append({'engine':engine,'observation':got})
        rows.append({'id':name,'results':observations})
    (R/'result.json').write_text(json.dumps({'status':'PASSED','supplement_cases':len(rows),'rows':rows,'scope':'Additional borrowed-value and work-bound checks; not initial pre-code oracles, not CLI transport or performance evidence.'},indent=2)+'\n');print({'status':'PASSED','supplement_cases':len(rows)})

if __name__=='__main__':main()
