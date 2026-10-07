"""Explicit representation selection; no checker/evaluator selected by CLI."""
from pathlib import Path
import subprocess,json,sys,hashlib
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-record-list'
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);R=parser.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists()
R.mkdir(exist_ok=False);rows=[]
def call(args,error=None):
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/component_text.py'),*map(str,args)],capture_output=True,timeout=20);i=len(rows);(R/f'{i}.stdout').write_bytes(q.stdout);assert q.returncode==(2 if error else 0) and not q.stderr;v=json.loads(q.stdout)
 if error:assert v['error']['code']==error,v
 else:assert v['result']['semantic_check'] is False and v['result']['execution_admission'] is False
 rows.append({'args':list(map(str,args)),'error':error})
suite=json.loads((D/'cases.json').read_bytes());inp=R/'input.bagaev';inp.write_text(suite['positive'][0]['source']);out=R/'source.json';back=R/'canonical.bagaev';again=R/'again.json'
call(['decode',inp,'--output',R/'default-refusal'],'FORM_VERSION');assert not (R/'default-refusal').exists()
call(['decode',inp,'--form','7','--output',out]);assert json.loads(out.read_bytes())==suite['positive'][0]['expected']
call(['encode',out,'--form','7','--output',back]);assert back.read_text().startswith('bagaev component-form/7;')
call(['decode',back,'--form','7','--output',again]);assert again.read_bytes()==out.read_bytes()
call(['decode',T/'examples/probes/component-outcomes/form/StockOutcome.bagaev','--form','7','--output',R/'old-refusal'],'FORM_VERSION');assert not (R/'old-refusal').exists()
call(['decode',inp,'--form','99','--output',R/'selector-refusal'],'TOOL_USAGE');assert not (R/'selector-refusal').exists()
result={'status':'PASSED','calls':6,'refusals':3,'exact_source_roundtrip':True,'rows':rows};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
