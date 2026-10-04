"""Compare an explicitly supplied source-check CLI with pre-implementation cases.
Run only in an independently authorized bounded execution profile. This script
neither compiles a candidate nor executes any lowered language program.
"""
from pathlib import Path
import argparse,base64,hashlib,json,subprocess

PINS={
    'typed-scalar-literals.json':'ddce2932ebb57508ea8754bb26c368bb1a6871cb28291742ce61f60bf4461c41',
    'typed-scalar-boundaries.json':'224010f1c45a1ea442969d6abc1c1697d86c773a96e21a5e0d5b165ab1603960',
}
def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--binary',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);args=ap.parse_args()
    binary=args.binary.resolve(strict=True)
    if not binary.is_file():raise ValueError('explicit regular binary required')
    root=Path(__file__).resolve().parents[2];cases=[]
    for name,pin in PINS.items():
        raw=(root/'examples/probes'/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('frozen fixture identity mismatch')
        data=json.loads(raw)
        for field in ['cases','structural_cases','raw_cases','transport_recipes']:cases.extend(data.get(field,[]))
    assert len(cases)==43 and len({x['id'] for x in cases})==43
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False);rows=[]
    for case in cases:
        ident=case['id'];assert ident and all(c.isascii() and (c.isalnum() or c=='-') for c in ident)
        if 'source' in case:data=canonical(case['source'])
        elif 'utf8_or_raw_base64' in case:data=base64.b64decode(case['utf8_or_raw_base64'],validate=True)
        else:
            recipe=case['recipe']
            if 'ascii_repeat' in recipe:
                assert recipe['ascii_repeat']==' ' and recipe['count']==1048577
                data=b' '*recipe['count']
            else:
                data=canonical(recipe['canonical_source']);n=recipe['append_ascii_space_to_total_bytes']
                assert n==1048576 and len(data)<=n;data+=b' '*(n-len(data))
        assert len(data)<=1048577
        path=output/(ident+'.input');path.write_bytes(data)
        try:
            result=subprocess.run([str(binary),'check-source','--input',str(path)],capture_output=True,timeout=15)
            actual=result.stdout;exit_code=result.returncode;stderr=result.stderr.decode('utf-8','replace')
        except subprocess.TimeoutExpired:
            actual=b'';exit_code=None;stderr='source-check process timeout'
        expected=canonical(case['expected'])+b'\n';matched=exit_code==0 and actual==expected
        rows.append({'id':ident,'exit':exit_code,'exact_wire_match':matched,'input_sha256':hashlib.sha256(data).hexdigest(),'expected_sha256':hashlib.sha256(expected).hexdigest(),'actual_sha256':hashlib.sha256(actual).hexdigest(),'stderr':stderr})
        (output/(ident+'.stdout')).write_bytes(actual)
        print(ident,'PASS' if matched else 'FAIL',flush=True)
    report={'status':'PASS' if all(r['exact_wire_match'] for r in rows) else 'FAILED','fixture_sha256':PINS,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'observations':rows,'scope':'Source check and detached lowering only; no lowered program execution'}
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
