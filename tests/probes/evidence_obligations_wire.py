"""Data-only fixed-obligation compatibility replay helper. Does not compile or launch code."""
import argparse,hashlib,json,os,stat,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def bounded(path,limit):
    with Path(path).open('rb') as f:
        m=os.fstat(f.fileno())
        if not stat.S_ISREG(m.st_mode) or m.st_size>limit:raise ValueError('file bound')
        raw=f.read(limit+1)
        if len(raw)>limit:raise ValueError('file bound')
        return raw
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['list','request','check']);p.add_argument('case',nargs='?');p.add_argument('--mode',choices=['reference','native'],default='reference');p.add_argument('--output');a=p.parse_args()
    d=ROOT/'examples/probes/evidence-obligations';source=bounded(d/'program.json',1048576);data=json.loads(bounded(d/'cases.json',4*1024*1024))
    if data['schema']!='evidence-obligations-replay/1' or hashlib.sha256(source).hexdigest()!=data['source_sha256']:raise ValueError('source identity')
    rows={c['id']:c for c in data['cases']}
    if len(rows)!=48 or len(data['cases'])!=48:raise ValueError('fixture count')
    if a.action=='list':
        if a.case is not None or a.output is not None:raise ValueError('unexpected argument')
        print(json.dumps([{'id':c['id'],'work':c['work']} for c in data['cases']]));return
    if a.case not in rows:raise ValueError('unknown case')
    c=rows[a.case]
    if a.action=='request':
        if a.output is not None:raise ValueError('unexpected output')
        sys.stdout.buffer.write(b'{"schema":"bagaev-typed-record-invocation/8","program":'+source+b',"arguments":'+c['arguments_raw'].encode()+b'}');return
    if a.output is None:raise ValueError('output required')
    if bounded(a.output,4325440)!=bytes.fromhex(c[a.mode+'_hex']):raise ValueError('complete output mismatch')
    print(json.dumps({'case':a.case,'mode':a.mode,'complete_output_match':True}))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError) as e:print(str(e),file=sys.stderr);raise SystemExit(2)
