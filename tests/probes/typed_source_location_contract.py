"""Check a supplied location CLI against frozen cases inside an admitted profile.
No compiler, lowered-program execution, network or evidence authentication.
"""
from pathlib import Path
import argparse,base64,hashlib,json,subprocess
PIN='6a7752d79a03b7e1adce653713b22a0cf105a0284912c829a8d87baddcb46526'
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--binary',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);args=ap.parse_args();binary=args.binary.resolve(strict=True)
    root=Path(__file__).resolve().parents[2]/'examples/probes';raw=(root/'typed-source-location-cases.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN;fixture=json.loads(raw);sources={}
    assert set(fixture['source_fixture_sha256'])=={'typed-scalar-literals.json','typed-scalar-boundaries.json'}
    for name,pin in fixture['source_fixture_sha256'].items():
        raw=(root/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==pin;j=json.loads(raw)
        for field in ['cases','structural_cases','raw_cases','transport_recipes']:
            for row in j.get(field,[]):sources[row['id']]=row
    assert len(fixture['cases'])==589 and len({r['id'] for r in fixture['cases']})==589
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False);paths={};rows=[]
    for name in sorted({r['source_case'] for r in fixture['cases']}):
        assert name and all(c.isascii() and (c.isalnum() or c=='-') for c in name)
        row=sources[name]
        if 'source' in row:data=canonical(row['source'])
        elif 'utf8_or_raw_base64' in row:data=base64.b64decode(row['utf8_or_raw_base64'],validate=True)
        else:
            recipe=row['recipe'];data=canonical(recipe['canonical_source']);n=recipe['append_ascii_space_to_total_bytes'];assert n==1048576 and len(data)<=n;data+=b' '*(n-len(data))
        assert len(data)<=1048577;path=output/(name+'.input');path.write_bytes(data);paths[name]=path
    for case in fixture['cases']:
        ident=case['id'];assert ident and all(c.isascii() and (c.isalnum() or c=='-') for c in ident);assert type(case['node']) is int and 0<=case['node']<=65535
        p=subprocess.run([str(binary),'project-node','--input',str(paths[case['source_case']]),'--lowered-pin',case['expected_lowered_pin'],'--node',str(case['node'])],capture_output=True,timeout=15)
        expected=canonical(case['expected'])+b'\n';matched=p.returncode==0 and p.stdout==expected
        rows.append({'id':ident,'exit':p.returncode,'exact_wire_match':matched,'expected_sha256':hashlib.sha256(expected).hexdigest(),'actual_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr':p.stderr.decode('utf-8','replace')});(output/(ident+'.stdout')).write_bytes(p.stdout)
        if not matched:print(ident,'FAIL',flush=True)
    report={'status':'PASS' if all(r['exact_wire_match'] for r in rows) else 'FAILED','fixture_sha256':PIN,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'observations':rows,'scope':'Rechecked location lookup only; no native result authentication'}
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),flush=True)
    if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
