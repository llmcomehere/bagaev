"""Reviewed pure frame boundary witnesses; no source checking or execution."""
from pathlib import Path
import argparse,hashlib,json,sys
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'src'));import bagaev_component_edit as edit
D=P/'examples/probes/component-edit';frozen=json.loads((D/'inputs.json').read_bytes())
for n,h in frozen['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
parser=argparse.ArgumentParser(description='Pure edit-frame boundary guards; no checker or programme execution.');parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();R=args.output;assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir()
suite=json.loads((D/'cases.json').read_bytes());raw=suite['cases'][0]['frame'];normal=json.loads(raw);depth=0
for _ in range(9):depth=[depth]
values={
 'UTF8':b'\xff','BOM':'\ufeff'+raw,'FRAME-BYTES':'x'*(edit.FRAME_BYTES+1),
 'DEPTH':json.dumps({**normal,'extra':depth}),'VALUES':json.dumps({**normal,'extra':[0]*33}),
 'SOURCE-BYTES':json.dumps({**normal,'source':'x'*(edit.form.BYTE_LIMIT+1)}),
 'FLOAT':json.dumps({**normal,'extra':1.5}),
 'LONG-INTEGER-KIND':raw.replace('"base": "'+normal['base']+'"','"base": '+'9'*5000),
 'DICT-INPUT':normal}
rows=[]
for case in json.loads((D/'guard-expectations.json').read_bytes())['guards']:
 try:edit.frame(values[case['id']]);actual=None
 except edit.EditError as e:actual=e.code
 rows.append({**case,'actual':actual,'matched':actual==case['expected']})
assert all(x['matched'] for x in rows),rows
(R/'result.json').write_text(json.dumps({'status':'PASSED','rows':rows,'checker_calls':0},indent=2)+'\n');print({'guards':len(rows),'matched':len(rows),'checker_calls':0})
