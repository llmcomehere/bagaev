"""Data-only material for a fixed equal application-byte boundary. Never launches code."""
import argparse,hashlib,json,sys
from pathlib import Path
from ordinary_catalog_wire import read,load,canonical
ROOT=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['list','request','expected','native-wire','reference-wire','check']);p.add_argument('case',nargs='?');p.add_argument('--output');a=p.parse_args()
    data=load(read(ROOT/'examples/probes/prepared-json10/catalog-cases.json',4*1024*1024));source=read(ROOT/'examples/probes/record-list-push/catalog-program.json',1048576)
    if data['schema']!='prepared10-catalog-replay/1' or hashlib.sha256(source).hexdigest()!=data['source_sha256']:raise ValueError('source identity')
    rows={c['id']:c for c in data['cases']}
    if len(rows)!=103 or len(data['cases'])!=103:raise ValueError('fixture shape')
    if a.action=='list':
        if a.case is not None or a.output is not None:raise ValueError('unexpected argument')
        print(json.dumps(list(rows)));return
    if a.case not in rows:raise ValueError('unknown case')
    c=rows[a.case];result=load(bytes.fromhex(c['reference_hex']))
    if result['schema']!='bagaev-typed-record-result/10' or result['status']!='success' or result['value']['case'] not in ['Ok','Error']:raise ValueError('fixture outcome')
    expected=(canonical(result['value']['value'])+'\n').encode()
    if a.action=='check':
        if a.output is None:raise ValueError('output required')
        if read(a.output,1048576)!=expected:raise ValueError('complete canonical boundary mismatch')
        print(json.dumps({'case':a.case,'complete_boundary_bytes_match':True}));return
    if a.output is not None:raise ValueError('unexpected output')
    if a.action=='request':
        raw=bytes.fromhex(c['arguments_hex']).strip()
        if not raw.startswith(b'[') or not raw.endswith(b']') or len(load(raw))!=1:raise ValueError('arguments')
        out=raw[1:-1]
    elif a.action=='expected':out=expected
    else:out=bytes.fromhex(c['native_hex' if a.action=='native-wire' else 'reference_hex'])
    sys.stdout.buffer.write(out)
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError,RecursionError) as e:print(str(e),file=sys.stderr);raise SystemExit(2)
