"""Finite data-only discovery checks; never executes a language programme."""
from pathlib import Path
import json,sys,subprocess,argparse,copy
T=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
R=p.parse_args().output;assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir()
sys.path.insert(0,str(T/'src'));import bagaev_record_capabilities as cap
expected=json.loads((T/'examples/probes/record-capabilities-r2/expected-additions.json').read_bytes())
calls=0
def cli(args,ok=True):
 global calls
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_capabilities.py'),*args],capture_output=True,timeout=20);calls+=1
 (R/(str(calls)+'.stdout')).write_bytes(q.stdout);assert not q.stderr and q.returncode==(0 if ok else 2)
 return q.stdout
for form in ('4','5'):
 old=cap.describe(form);new=cap.describe_v2(form)
 for key,value in expected[form].items():assert new[key]==value,(form,key)
 legacy=copy.deepcopy(new)
 for key in ('argument_routes','native_preparation'):del legacy[key]
 del legacy['data_tools']['record_json_prepare.py'];legacy['schema']='bagaev-record-capabilities/1'
 assert legacy==old
 assert cli(['--form',form])==cli(['--form',form,'--revision','1'])
 result=cli(['--form',form,'--revision','2']);assert json.loads(result)==new
 assert result==cli(['--form',form,'--revision','2'])
 assert all(v is False for v in new['effects'].values())
 assert not new['semantic_check'] and not new['execution_admission']
 assert (T/new['native_preparation']['emitter_source']).is_file()
 assert (T/'tools/record_json_prepare.py').is_file()
 new['argument_routes']['record_json_prepare.py']['execution_admission']=True
 assert cap.describe_v2(form)['argument_routes']['record_json_prepare.py']['execution_admission'] is False
for args in [[],['--form','5','--revision','3'],['--form','5','--revision','2','--run'],
             ['--form','1','--revision','2']]:
 assert json.loads(cli(args,False))['error']['code']=='TOOL_USAGE'
for form in (None,5,'1'):
 try:cap.describe_v2(form)
 except cap.narrow.FormError as e:assert e.code=='FORM_VERSION'
 else:raise AssertionError('invalid profile')
result={'status':'PASSED','profiles':2,'data_cli_calls':calls,'api_refusals':3,
        'cli_refusals':4,'default_v1_equals_explicit_v1':True,'detached_results':True,
        'runtime_calls':0}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
