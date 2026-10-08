from pathlib import Path
import json,subprocess,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/pure-record-form'
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir(exist_ok=False);rows=[]
def call(args,error=None):
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_text.py'),*map(str,args)],capture_output=True,timeout=20);(R/f'{len(rows):02d}.stdout').write_bytes(q.stdout);assert not q.stderr and q.returncode==(2 if error else 0);v=json.loads(q.stdout);assert v['schema']=='bagaev-record-text/1'
 if error:assert v['error']['code']==error,(error,v)
 else:assert v['result']['source_schema']=='bagaev-typed-record/10' and v['result']['semantic_check'] is False and v['result']['execution_admission'] is False
 rows.append({'error':error})
s=json.loads((D/'cases.json').read_bytes());inp=R/'input.bagaev';inp.write_text(s['positive'][2]['source']);out=R/'program.json';back=R/'canonical.bagaev';again=R/'again.json';call(['decode',inp,'--output',out]);assert json.loads(out.read_bytes())==s['positive'][2]['expected'];call(['encode',out,'--output',back]);call(['decode',back,'--output',again]);assert again.read_bytes()==out.read_bytes();saved=out.read_bytes();call(['decode',inp,'--output',out],'RECORD_PATH');assert out.read_bytes()==saved
bad=R/'bad.json';bad.write_text('{"schema":1,"schema":2}');call(['encode',bad,'--output',R/'bad-out'],'RECORD_JSON');assert not (R/'bad-out').exists()
link=R/'link';link.symlink_to(inp);call(['decode',link,'--output',R/'link-out'],'RECORD_PATH');call(['decode',R,'--output',R/'dir-out'],'RECORD_PATH')
big=R/'big';big.write_bytes(b' '*1048577);call(['decode',big,'--output',R/'big-out'],'RECORD_BOUNDS');call(['decode',inp,'--form','7','--output',R/'selector-out'],'TOOL_USAGE')
old=T/'examples/probes/tag-box/TagBox.bagaev';call(['decode',old,'--output',R/'component-out'],'FORM_SYNTAX')
wrong=R/'wrong.bagaev';wrong.write_text(s['type_refusal']['source']);call(['decode',wrong,'--output',R/'unchecked.json']);assert json.loads((R/'unchecked.json').read_bytes())==s['type_refusal']['expected']
assert inp.read_text()==s['positive'][2]['source'];result={'status':'PASSED','calls':len(rows),'refusals':sum(x['error']is not None for x in rows),'input_and_existing_output_preserved':True};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
