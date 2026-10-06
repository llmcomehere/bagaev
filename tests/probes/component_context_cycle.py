"""Source-bound component context inserted at the existing WC17 resume boundary."""
from pathlib import Path
import argparse,copy,hashlib,json,re,subprocess,sys
P=Path(__file__).resolve().parents[2];T=P;D=P/'examples/probes/component-context'
sys.path.insert(0,str(T/'src'));import bagaev_component_context as context;import bagaev_component_edit as edit
sys.path.insert(0,str(T/'tests/probes'));import component_change_cycle as cycle;import component_cycle as component
def sha(b):return hashlib.sha256(b).hexdigest()
frozen=json.loads((D/'inputs.json').read_bytes())
for n,h in frozen['sha256'].items():assert sha((D/n).read_bytes())==h
suite=json.loads((D/'cases.json').read_bytes());case=next(c for c in suite['cases'] if c['id']=='VALID');expected=suite['connected_expected'];policy=edit.canonical(suite['policy']);
parser=argparse.ArgumentParser(description='Explicit component context with separately reviewed host executables.')
parser.add_argument('--reader',required=True,type=Path);parser.add_argument('--reader-sha256',required=True);parser.add_argument('--output',required=True,type=Path)
parser.add_argument('--matcher',required=True);parser.add_argument('--matcher-sha256',required=True);parser.add_argument('--reference',required=True);parser.add_argument('--reference-sha256',required=True)
args=parser.parse_args();reader=args.reader;R=args.output
assert reader.is_absolute() and reader.is_file() and not reader.is_symlink();assert re.fullmatch('[0-9a-f]{64}',args.reader_sha256) and sha(reader.read_bytes())==args.reader_sha256
assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir();calls=[];observations=[]
def wire_checker(source,policy_bytes):
 n=len(calls)+1;f=R/f'{n}.source.json';p=R/f'{n}.policy.json';f.write_bytes(source);p.write_bytes(policy_bytes);q=subprocess.run([str(reader),'policy',str(f),str(p)],capture_output=True,timeout=10);(R/f'{n}.stdout').write_bytes(q.stdout);(R/f'{n}.stderr').write_bytes(q.stderr);assert q.returncode==0 and not q.stderr and f.read_bytes()==source and p.read_bytes()==policy_bytes;calls.append({'source_sha256':sha(source),'output_sha256':sha(q.stdout)});return json.loads(q.stdout)
def checker(programme):
 try:edit.checked(programme,policy,wire_checker,'context')
 except edit.ComponentRefused as e:raise context.ComponentRefusal(e.reason,'') from None
 except edit.CheckerUnavailable as e:raise context.ContextUnavailable(str(e)) from None
 return edit.canonical(programme)
def hook(receiver,event):
 if receiver.current_case!='WC17':return
 if event['command']=='Resume':
  state_before=copy.deepcopy((receiver.state,receiver.ledger,receiver.runs,receiver.default));old_checkpoint=receiver.checkpoint
  result=context.inspect(edit.canonical(case['context']),edit.canonical(case['expectation']),component_checker=checker);assert result==case['expected']
  assert result['snapshot']=='sha256:'+component.digest(json.loads(receiver.engine.frozen_sources[receiver.default]))
  sources={x['id']:x for x in case['context']['sources']};pending=json.loads(sources['pending-operation']['text']);assert set(pending)=={'schema','programme_source','programme_pin','continuation'} and pending['schema']=='component-pending-operation/1'
  binding=next(x for x in result['programme_sources'] if x['id']==pending['programme_source']);assert binding['role']=='dependency' and binding['pin']==pending['programme_pin']
  retained=receiver.runs['original'];assert pending['continuation']['programme']==retained and binding['pin']=='sha256:'+component.digest(json.loads(receiver.engine.frozen_sources[retained]))
  restored=component.b.encoded(pending['continuation']);assert restored==old_checkpoint
  # Replace only explicit checkpoint data after every check. No capability or live
  # state is restored; a failed reconstruction would leave the original intact.
  receiver.checkpoint=restored
  assert (receiver.state,receiver.ledger,receiver.runs,receiver.default)==state_before
  observations.append({'kind':'restored-context','current':receiver.default,'old_programme':retained,'inspection':result,'checkpoint_sha256':sha(restored),'authority_restored':False})
 elif event['command']=='Observe':
  shadow=copy.deepcopy(receiver);denied=copy.deepcopy(event);denied['permissions']['observe']=False;shadow.execute(denied);projection=shadow.projection()
  for k,v in expected['denied_observation'].items():assert projection[k]==v
  assert shadow.state==receiver.state and shadow.ledger==receiver.ledger and shadow.engine.count==receiver.engine.count
  observations.append({'kind':'current-observation-denied','matched':True,'state_unchanged':True,'application_reinvoked':False})
assert sha((T/'examples/probes/whole-cycle/cases.json').read_bytes())==expected['world_cases_sha256']
sys.argv=['context-connected','--matcher',args.matcher,'--matcher-sha256',args.matcher_sha256,'--reader',str(reader),'--reader-sha256',args.reader_sha256,'--reference',args.reference,'--reference-sha256',args.reference_sha256,'--output',str(R/'runtime')];cycle.main(before_event=hook)
assert len(observations)==2
(R/'context-result.json').write_text(json.dumps({'status':'PASSED','observations':observations,'data_checker_calls':calls,'scope':'Explicit data reconstruction at WC17, current S2 and old pending S1; separate current observation denial. No crash/durability/authentication or restored rights.'},indent=2)+'\n')
