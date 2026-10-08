"""Finite data-only preparation and separately selected reference checks."""
from pathlib import Path
import json, subprocess, sys
from outcome_host import configure
T=Path(__file__).resolve().parents[2]
a=configure(reference=True);R=a.output;R.mkdir();rows=[]
D=T/'examples/probes/pure-reindex-entry'
cases=json.loads((D/'cases.json').read_bytes())
source=D/'ReindexEntry.bagaev';original=source.read_bytes()
def call(extra,error=None):
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_text.py'),*map(str,extra)],capture_output=True,timeout=20)
 (R/f'cli-{len(rows)}.stdout').write_bytes(q.stdout)
 assert not q.stderr and q.returncode==(2 if error else 0)
 result=json.loads(q.stdout)
 if error:assert result['error']['code']==error,result
 else:
  assert result['result']['semantic_check'] is False and result['result']['execution_admission'] is False
  assert result['result']['output_schema']=='bagaev-typed-record-invocation/10'
 rows.append(error)
for c in cases['cases']:
 args=R/(c['id']+'-args.json');raw=json.dumps(c['arguments'],ensure_ascii=False).encode();args.write_bytes(raw)
 out=R/(c['id']+'-invoke.json');call(['prepare',source,'--arguments',args,'--output',out])
 expected={'schema':'bagaev-typed-record-invocation/10','program':cases['program'],'arguments':c['arguments']}
 assert json.loads(out.read_bytes())==expected and args.read_bytes()==raw
 q=subprocess.run([str(a.reference),'run','--input',str(out)],capture_output=True,timeout=20)
 (R/(c['id']+'-reference.stdout')).write_bytes(q.stdout);assert q.returncode==0 and not q.stderr
 v=json.loads(q.stdout)
 if 'reason' in c:assert v['reason']==c['reason'] and v['value'] is None
 else:assert v['status']=='success' and v['value']==c['expected']
wrong=R/'wrong.json';wrong.write_text('{}')
call(['prepare',source,'--arguments',wrong,'--output',R/'nonarray'],'RECORD_ARGUMENTS')
wrong.write_text('[{"x":1,"x":2}]');call(['prepare',source,'--arguments',wrong,'--output',R/'duplicate'],'RECORD_JSON')
wrong.write_text('[1.5]');call(['prepare',source,'--arguments',wrong,'--output',R/'float'],'RECORD_JSON')
wrong.write_text('["\\ud800"]');call(['prepare',source,'--arguments',wrong,'--output',R/'surrogate'],'RECORD_JSON')
call(['prepare',source,'--output',R/'missing'],'TOOL_USAGE')
call(['decode',source,'--arguments',wrong,'--output',R/'unexpected'],'TOOL_USAGE')
link=R/'link';link.symlink_to(wrong);call(['prepare',source,'--arguments',link,'--output',R/'linked'],'RECORD_PATH')
old=R/'replace-invoke.json';saved=old.read_bytes();call(['prepare',source,'--arguments',R/'replace-args.json','--output',old],'RECORD_PATH');assert old.read_bytes()==saved
wrong.write_bytes(b' '*1048577);call(['prepare',source,'--arguments',wrong,'--output',R/'big'],'RECORD_BOUNDS')
oversize_args=R/'combined-args.json';oversize_args.write_text(json.dumps(['a'*1048470]));assert oversize_args.stat().st_size<=1048576
call(['prepare',source,'--arguments',oversize_args,'--output',R/'combined'],'RECORD_BOUNDS')
invalid=json.loads((T/'examples/probes/pure-record-form/cases.json').read_bytes())['type_refusal']
invalid_source=R/'invalid.bagaev';invalid_source.write_text(invalid['source']);empty=R/'empty-args.json';empty.write_text('[]');unchecked=R/'unchecked.json'
call(['prepare',invalid_source,'--arguments',empty,'--output',unchecked])
q=subprocess.run([str(a.reference),'run','--input',str(unchecked)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr
v=json.loads(q.stdout);assert v['reason']==invalid['reason'] and v['status']!='success';(R/'type-refusal.stdout').write_bytes(q.stdout)
for n in ['nonarray','duplicate','float','missing','unexpected','linked','big','surrogate','combined']:assert not (R/n).exists()
assert source.read_bytes()==original
result={'status':'PASSED','cli_calls':len(rows),'refusals':sum(x is not None for x in rows),'native_invocations':6,'successful_values':4,'work_refusals':1,'type_refusals':1}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
