from pathlib import Path
import json,hashlib,sys,subprocess,argparse
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/record-capabilities'
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir()
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_capabilities as cap
expected=json.loads((D/'expected.json').read_bytes())
names='list.text list.len list.at list.contains list.increasing list.unique list.push text.bytes text.scalars text.eq text.lt records.list records.len records.at records.push none.int some.int option.is_some option.or json.kind json.len json.int json.is_text json.at json.text_or json.field record.field text.byte_at int.eq int.le bool.not'.split()
for v in ('4','5'):
 x=cap.describe(v);e=expected[v];assert x['form']=='record-form/'+v and x['program_schema']=='bagaev-typed-record/'+str(e['typed_profile']);assert x['reference_bounds']==expected['runtime']|{'record_list_capacity':e['record_list_capacity']};assert x['parser_bounds']==expected['parser'];assert [s['name'] for s in x['intrinsic_spellings']]==sorted(names);assert not x['semantic_check'] and not x['execution_admission'];assert all(y is False for y in x['effects'].values());assert x==cap.describe(v)
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_capabilities.py'),'--form',v],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and json.loads(q.stdout)==x;(R/('form'+v+'.json')).write_bytes(q.stdout)
 x['data_tools']['record_text.py'].append('execute');assert 'execute' not in cap.describe(v)['data_tools']['record_text.py']
for args in [[],['--form','1'],['--form','5','--run']]:
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_capabilities.py'),*args],capture_output=True,timeout=20);assert q.returncode==2 and not q.stderr and json.loads(q.stdout)['error']['code']=='TOOL_USAGE'
for v in ['1',5,None]:
 try:cap.describe(v)
 except cap.narrow.FormError as e:assert e.code=='FORM_VERSION'
 else:raise AssertionError('version accepted')
r={'status':'PASSED','profiles':2,'named_intrinsics':31,'cli_calls':5,'cli_refusals':3,'api_refusals':3,'runtime_calls':0};(R/'result.json').write_text(json.dumps(r)+'\n');print(r)
