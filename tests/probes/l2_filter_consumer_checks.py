"""Own queue consumer of the new private filter profile, no external effects."""
from pathlib import Path
import argparse,copy,hashlib,json,subprocess,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/l2-filter'
sys.path.insert(0,str(T));sys.path.insert(0,str(T/'tests/probes'))
from src import bagaev_l2 as old
from src import bagaev_l2_filter as new
from src import bagaev_l2_filter_backend as backend
from queue_order_baseline import ordinary
enc=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()

def baseline(q):
    bad={'kind':'refusal','reason':'invalid-request'}
    if type(q)is not dict or set(q)!={'jobs'} or type(q['jobs'])is not list or len(q['jobs'])>8:return bad
    all_jobs=[];open_jobs=[]
    for job in q['jobs']:
        if type(job)is not dict or ('closed' in job and type(job['closed'])is not bool):return bad
        stripped={k:v for k,v in job.items() if k!='closed'};all_jobs.append(stripped)
        if not job.get('closed',False):open_jobs.append(stripped)
    if ordinary({'jobs':all_jobs},1)['kind']=='refusal':return bad
    return ordinary({'jobs':open_jobs},1)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);R=parser.parse_args().output
    assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir()
    manifest=json.loads((D/'manifest.json').read_bytes())['sha256'];assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
    value=json.loads((D/'queue-base.json').read_bytes());change=json.loads((D/'queue-change.patch').read_bytes());program=new.apply_patch(value,change)
    assert enc(new.program_value(program))==enc(json.loads((D/'queue.json').read_bytes()))
    source=new.program_value(program);(R/'source.json').write_bytes(enc(source));(R/'base.json').write_bytes(enc(value));(R/'change.patch').write_bytes(enc(change))
    artifact=backend.compile_program(program);(R/'artifact.json').write_bytes(artifact);verified=backend.verify_artifact(artifact,program);namespace={'__name__':'owned_queue_filter'};exec(compile(verified,'<owned-queue-filter>','exec'),namespace)
    rows=[];cases=json.loads((D/'consumer-cases.json').read_bytes())['cases']
    for c in cases:
        arg=copy.deepcopy(c['input']);before=enc(arg);a=baseline(arg);b=new.evaluate(program,arg);d=namespace['evaluate'](arg)
        assert enc(a)==enc(b)==enc(d)==enc(c['expected']) and enc(arg)==before,(c['id'],a,b,d)
        rows.append({'id':c['id'],'value':b})
    literal=next(c for c in cases if c['id']=='closed-urgent');(R/'input.json').write_bytes(enc(literal['input']))
    for engine in ('reference','cpython'):
        args=[sys.executable,'-B','-S','-m','src.bagaev_filter','run',str(R/'source.json'),'--input',str(R/'input.json')]
        if engine=='cpython':args+=['--artifact',str(R/'artifact.json')]
        q=subprocess.run(args,cwd=T,capture_output=True,timeout=20);(R/(engine+'.stdout')).write_bytes(q.stdout);(R/(engine+'.stderr')).write_bytes(q.stderr)
        assert q.returncode==0 and not q.stderr;wire=json.loads(q.stdout);assert wire['result']['engine']==engine and wire['result']['value']==literal['expected']
    result={'status':'PASSED','cases':len(rows),'new_cases':8,'reused_cases':23,'cli_calls':2,'rows':rows,'scope':'Separate pure /2 queue selection only; validate closedrecords before filtering. No Store, native, model or production acceptance.'}
    (R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))

if __name__=='__main__':main()
