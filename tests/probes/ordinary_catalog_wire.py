"""Data-only ordinary catalogue oracle and source-fault material. Never launches code."""
import argparse,hashlib,json,os,stat,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(path,limit):
    with Path(path).open('rb') as f:
        m=os.fstat(f.fileno())
        if not stat.S_ISREG(m.st_mode) or m.st_size>limit:raise ValueError('file bound')
        raw=f.read(limit+1)
        if len(raw)>limit:raise ValueError('file bound')
        return raw
def pairs(items):
    out={}
    for k,v in items:
        if k in out:raise ValueError('duplicate key')
        out[k]=v
    return out
def invalid_constant(v):raise ValueError('nonfinite number')
def load(raw):return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid_constant)
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['list','request','check','mutant']);p.add_argument('case',nargs='?');p.add_argument('--output');a=p.parse_args()
    oracle=load(read(ROOT/'examples/beta/catalog-cases.json',4*1024*1024));cases={c['id']:c for c in oracle['cases']}
    if oracle['oracle']!='catalog-cases/2.0.0' or oracle['contract']!='catalog-application/2' or len(cases)!=99 or len(oracle['cases'])!=99:raise ValueError('oracle shape')
    source=read(ROOT/'examples/probes/ordinary-catalog/catalog.rs',1048576);faults=load(read(ROOT/'examples/probes/ordinary-catalog/mutations.json',1048576))
    if faults['schema']!='ordinary-catalog-mutations/1' or hashlib.sha256(source).hexdigest()!=faults['source_sha256']:raise ValueError('source identity')
    if a.action=='list':
        if a.case is not None or a.output is not None:raise ValueError('unexpected argument')
        print(json.dumps({'cases':list(cases),'mutants':[m['id'] for m in faults['mutants']]}));return
    if a.action=='mutant':
        if a.output is not None:raise ValueError('unexpected output')
        selected=[m for m in faults['mutants'] if m['id']==a.case]
        if len(selected)!=1:raise ValueError('unknown mutant')
        m=selected[0];text=source.decode()
        if text.count(m['old'])!=m['occurrences']:raise ValueError('patch mismatch')
        raw=text.replace(m['old'],m['new']).encode()
        if hashlib.sha256(raw).hexdigest()!=m['source_sha256']:raise ValueError('mutant identity')
        sys.stdout.buffer.write(raw);return
    if a.case not in cases:raise ValueError('unknown case')
    c=cases[a.case]
    if a.action=='request':
        if a.output is not None:raise ValueError('unexpected output')
        sys.stdout.buffer.write(canonical(oracle['requests'][c['request']]).encode());return
    if a.output is None:raise ValueError('output required')
    actual=load(read(a.output,1048576));expected=oracle['responses'][c['expect']]
    if canonical(actual)!=canonical(expected):raise ValueError('complete application mismatch')
    print(json.dumps({'case':a.case,'complete_application_match':True}))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError,RecursionError) as e:print(str(e),file=sys.stderr);raise SystemExit(2)
