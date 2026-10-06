"""Frozen manager decisions with actual reader/reference and unchanged /8 matcher."""
from pathlib import Path
import argparse,copy,hashlib,json,re,sys,subprocess
P=Path(__file__).resolve().parents[2];T=P;D=P/'examples/probes/component-programmes'
sys.path.insert(0,str(T/'src'));sys.path.insert(0,str(T/'tests/probes'))
import bagaev_component_owner as owner;import bagaev_component_edit as edit;import component_change as q
from bagaev_component_programmes import ProgrammeManager,RunError
sha=lambda b:hashlib.sha256(b).hexdigest();clone=copy.deepcopy
for n,h in json.loads((D/'inputs.json').read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
parser=argparse.ArgumentParser(description='Source admission and pinned-run simulation with separately reviewed binaries.')
for n in ['reader','reference','matcher']:
 parser.add_argument('--'+n,required=True,type=Path);parser.add_argument('--'+n+'-sha256',required=True)
parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();reader=args.reader;reference=args.reference;matcher=args.matcher;R=args.output
for f,h in [(reader,args.reader_sha256),(reference,args.reference_sha256),(matcher,args.matcher_sha256)]:assert f.is_absolute() and f.is_file() and not f.is_symlink() and re.fullmatch('[0-9a-f]{64}',h) and sha(f.read_bytes())==h
assert R.is_absolute() and R.parent.is_dir()
assert not R.exists();R.mkdir();q.R=R;calls=[];conditions={'tick':1,'epoch':1,'submit':True,'write':True,'observe':True,'cancel':True};permission=True;late=None;active=False
sources=[json.loads((T/f'examples/probes/component-source/{n}.json').read_bytes()) for n in ('S1','S2')];policy=json.loads((T/'examples/probes/component-source/policy.json').read_bytes());graph=json.loads((D/'receiving-obligations.json').read_bytes());base=edit.digest(sources[0]);target=edit.digest(sources[1]);state={'id':{'value':'e1'},'manual':['family'],'indexed':['old']}
binding={'component':target,'program':edit.digest(sources[1]['program']),'policy':edit.digest(policy),'assertions':edit.digest(graph),'profile':graph['profile'],'receiver':sha((T/'src/bagaev_component_owner.py').read_bytes()),'manager':sha((T/'src/bagaev_component_programmes.py').read_bytes())}
positive=[{'obligation':o['id'],'applicability':clone(binding),'receipt':{**o['requirement'],'outcome':'pass','selected':0 if o['requirement']['method']=='static' else 1}} for o in graph['obligations']]
def invoke(binary,args,inputs):
 n=len(calls)+1;paths=[]
 for suffix,data in inputs:
  f=R/f'{n:03d}.{suffix}';f.write_bytes(data);paths.append(f)
 r=subprocess.run([str(binary),*args,*map(str,paths)],capture_output=True,timeout=20);(R/f'{n:03d}.stdout').write_bytes(r.stdout);(R/f'{n:03d}.stderr').write_bytes(r.stderr);assert r.returncode==0 and not r.stderr and all(f.read_bytes()==d for f,(_,d) in zip(paths,inputs));calls.append({'input_sha256':[sha(d) for _,d in inputs],'output_sha256':sha(r.stdout)});return json.loads(r.stdout)
def checker(source,pol):
 global permission
 value=invoke(reader,['policy'],[('source.json',source),('policy.json',pol)])
 if active:
  if late=='late-base':manager.head='0'*64
  if late=='late-denied':permission=False
 return value
def evaluator(program,args):return invoke(reference,['run','--input'],[('input.json',edit.canonical({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':args}))])
match=q.Matcher(matcher,args.matcher_sha256);rows=[]
for case in json.loads((D/'manager-cases.json').read_bytes())['cases']:
 permission=True;late=None;active=False;instance=owner.Owner(policy=policy,sources=[sources[0]],state=state,revision=7,resource='catalogue/g1',checker=checker,evaluator=evaluator,conditions=lambda:clone(conditions));manager=ProgrammeManager(instance,initial=base,policy=policy,checker=checker,graph=graph,binding=binding,matcher=match,authority=lambda:permission);manager.start('original');before=(instance.snapshot(),clone(instance._ledger),clone(manager.runs));obs=clone(positive);candidate=clone(sources[1]);expected_base=base;variation=case['variation']
 if variation=='missing-consumer':obs=[x for x in obs if x['obligation']!='actual-entry-consumer']
 elif variation=='conflict-missing':
  obs=[x for x in obs if x['obligation']!='actual-entry-consumer'];negative=clone(obs[1]);negative['receipt'].update(outcome='refuted',selected=0);obs.append(negative)
 elif variation=='malformed':obs[-1]['receipt']['selected']=True
 elif variation in ('old-profile','wrong-producer'):
  for o in obs:o['applicability']['profile' if variation=='old-profile' else 'receiver']='old-catalogue-profile'
 elif variation=='stale-base':manager.head='0'*64
 elif variation=='denied':permission=False
 elif variation in ('late-base','late-denied'):late=variation
 elif variation=='wrong-candidate':candidate=clone(sources[0])
 active=True;actual=manager.admit(candidate,expected_base=expected_base,observations=obs);active=False
 unchanged=(instance.snapshot(),instance._ledger,manager.runs)==before;added=target in instance._sources
 matched=actual==case['expected'] and unchanged and added==case['candidate_added'];rows.append({'id':case['id'],'matched':matched,'actual':actual,'state_ledger_runs_unchanged':unchanged,'candidate_added':added})
result={'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'reader_reference_calls':calls,'matcher_calls':match.calls,'qualification_premise':'Complete pass receipt fixtures are controlled inputs, not newly qualified runtime observations. This checks manager/applicability behavior only.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({'status':result['status'],'cases':len(rows),'data_calls':len(calls),'matcher_calls':len(match.calls),'failures':[r for r in rows if not r['matched']]});assert result['status']=='PASSED'
