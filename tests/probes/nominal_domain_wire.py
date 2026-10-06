"""Read-only synthetic nominal-domain vectors. Does not compile or execute code."""
import argparse,json,os,stat,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(path,limit):
    with Path(path).open('rb') as f:
        m=os.fstat(f.fileno())
        if not stat.S_ISREG(m.st_mode) or m.st_size>limit:raise ValueError('file bound')
        out=f.read(limit+1)
        if len(out)>limit:raise ValueError('file bound')
        return out
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['list','request','check']);p.add_argument('case',nargs='?');p.add_argument('--mode',choices=['reference','rust'],default='reference');p.add_argument('--output');a=p.parse_args()
    data=json.loads(read(ROOT/'examples/probes/nominal-domains/cases.json',1048576));rows={c['id']:c for c in data['cases']}
    if data['schema']!='nominal-domain-parity/1' or len(rows)!=7 or len(data['cases'])!=7:raise ValueError('fixture shape')
    if a.action=='list':
        if a.case is not None or a.output is not None:raise ValueError('unexpected argument')
        print(json.dumps([{'id':c['id'],'rust_expected':c['rust_expected']} for c in data['cases']]));return
    if a.case not in rows:raise ValueError('unknown case')
    c=rows[a.case]
    if a.action=='request':
        if a.output is not None:raise ValueError('unexpected output')
        raw=c['rust_source'].encode() if a.mode=='rust' else json.dumps({'schema':'bagaev-typed-record-invocation/8','program':c['program'],'arguments':[]},separators=(',',':')).encode()
        sys.stdout.buffer.write(raw);return
    if a.mode!='reference':raise ValueError('Rust diagnostics require a separately observed compiler result')
    if a.output is None:raise ValueError('output required')
    if read(a.output,1048576)!=bytes.fromhex(c['reference_hex']):raise ValueError('complete output mismatch')
    print(json.dumps({'case':a.case,'complete_output_match':True}))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError) as e:print(str(e),file=sys.stderr);raise SystemExit(2)
