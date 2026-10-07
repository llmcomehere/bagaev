"""Fresh isolated qualification and finite applicability decisions; no live registration."""
from pathlib import Path
import copy,datetime,hashlib,json,subprocess,sys
P=Path(__file__).resolve().parents[2];T=P;D=P/'examples/probes/component-outcomes/admission'
sys.path.insert(0,str(P/'src'))
import bagaev_component_owner as base
import bagaev_component_edit as edit
import component_change as q
from bagaev_component_outcome_owner import OutcomeOwner
enc=edit.canonical;sha=lambda b:hashlib.sha256(b).hexdigest();pin=lambda v:sha(enc(v));clone=copy.deepcopy
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
s=json.loads((D/'inputs.json').read_bytes());pure_path=P/'examples/probes/component-outcomes/pure/corrected-cases.json';owner_path=P/'examples/probes/component-outcomes/owner/cases.json'
pure=json.loads(pure_path.read_bytes())['cases'];owner_cases=json.loads(owner_path.read_bytes());trace_template=next(c for c in owner_cases['cases'] if c['id']=='DECLINE-AFTER-B')
from outcome_host import configure
args=configure(reference=True,matcher=True);R=args.output;reader=args.reader;ref=args.reference;matcher_file=args.matcher
R.mkdir(exist_ok=False);q.R=R;matcher=q.Matcher(matcher_file,sha(matcher_file.read_bytes()))
def closure():return {str(Path(m.__file__).resolve()):sha(Path(m.__file__).read_bytes()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(P)}
sources=closure();sources[str(Path(__file__).resolve())]=sha(Path(__file__).read_bytes())
fixed={str(p):sha(p.read_bytes()) for p in [D/'inputs.json',D/'contract.md',pure_path,owner_path,T/'examples/probes/evidence-obligations/program.json',reader,ref,matcher_file]}
producer={'own_python':sources,'fixed':fixed,'python_sha256':sha(Path(sys.executable).read_bytes()),'python_version':sys.version,'environment_premise':'OS/stdlib and trusted host callbacks not authenticated by these hashes'}
(R/'producer-before.json').write_bytes(enc(producer));calls=[];qualifications={}
def invoke(binary,args,inputs):
 n=len(calls)+1;paths=[]
 for suffix,data in inputs:
  p=R/f'{n:03d}.{suffix}';p.write_bytes(data);paths.append(p)
 z=subprocess.run([str(binary),*args,*map(str,paths)],capture_output=True,timeout=20)
 (R/f'{n:03d}.stdout').write_bytes(z.stdout);(R/f'{n:03d}.stderr').write_bytes(z.stderr)
 assert z.returncode==0 and not z.stderr and all(p.read_bytes()==d for p,(_,d) in zip(paths,inputs))
 calls.append({'binary':'reader' if binary==reader else 'reference','inputs':[sha(d) for _,d in inputs],'output':sha(z.stdout)})
 return json.loads(z.stdout)
def checker(source,policy):return invoke(reader,['policy'],[('source.json',source),('policy.json',policy)])
def evaluate(program,args):return invoke(ref,['run','--input'],[('invocation.json',enc({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':args}))])
for label in ('good','bad'):
 candidate=s[label];start=len(calls);checked=checker(enc(candidate),enc(s['policy']))
 assert checked['status']=='checked' and checked['source_sha256']==pin(candidate) and checked['policy_compatible'] is True
 values=[]
 for c in pure:
  wire=evaluate(candidate['program'],c['arguments']);actual={k:v for k,v in wire.items() if k!='work'};expected={k:v for k,v in c['expected'].items() if k!='work'}
  assert type(wire['work'])is int and 0<=wire['work']<=65536
  values.append({'id':c['id'],'matched':actual==expected,'actual':wire,'expected_without_work':expected})
 failures=[v['id'] for v in values if not v['matched']];assert failures==([] if label=='good' else ['ZERO']),failures
 conditions=clone(owner_cases['conditions']);apps=[];corrupt=False
 def evaluator(program,args):
  wire=evaluate(program,args)
  if program['functions'][program['entry']]['body'][0]!='arg':
   apps.append(pin(program))
   if corrupt:wire['value']['value']['note']='corrupt'
  return wire
 obj=OutcomeOwner(policy=s['policy'],sources=[s['source1'],candidate],state=owner_cases['initial'],revision=7,resource='stock/g1',checker=checker,evaluator=evaluator,conditions=lambda:clone(conditions))
 trace=clone(trace_template);trace['actions'][1]['packet']['source']=pin(candidate);trace['expected']['outputs'][1]['intent']['source']=pin(candidate)
 outputs=[getattr(obj,a['command'])(enc(a['packet'])) for a in trace['actions']]
 actual={'outputs':outputs,**obj.snapshot(),'application_evaluations':len(apps)};assert actual==trace['expected']
 assert apps==[pin(s['source1']['program']),pin(candidate['program'])]
 guard=OutcomeOwner(policy=s['policy'],sources=[candidate],state=owner_cases['initial'],revision=7,resource='stock/g1',checker=checker,evaluator=evaluator,conditions=lambda:clone(conditions))
 before=guard.snapshot();corrupt=True
 try:guard.submit(enc(trace['actions'][1]['packet']));raise AssertionError('corrupt frame accepted')
 except base.OwnerEvaluationError as e:assert e.code=='OWNER_FRAME'
 assert guard.snapshot()==before;corrupt=False
 raw={'candidate':pin(candidate),'static':checked,'values':values,'business_refuted':bool(failures),'trace':actual,'source_association':apps[:2],'frame_guard':'OWNER_FRAME without mutation','calls':calls[start:]}
 qualifications[label]=raw;(R/(label+'-qualification.json')).write_bytes(enc(raw))
# Receipts are derived only after checking that the pre-bound producers stayed fixed.
assert closure()=={k:v for k,v in sources.items() if k!=str(Path(__file__).resolve())} or closure()==sources
for path,h in {**sources,**fixed}.items():assert sha(Path(path).read_bytes())==h,path
def bundle(label):
 graph=clone(s['graph']);candidate=s[label];graph.update(candidate_component_sha256=pin(candidate),candidate_program_sha256=pin(candidate['program']))
 binding={'component':pin(candidate),'program':pin(candidate['program']),'policy':pin(s['policy']),'assertions':pin(graph),'profile':graph['profile'],'producer':pin(producer),'qualification':pin(qualifications[label])}
 observations=[]
 for o in graph['obligations']:
  receipt={**o['requirement'],'outcome':'refuted' if label=='bad' and o['id']=='application-outcomes' else 'pass','selected':0 if o['requirement']['method']=='static' else 1}
  observations.append({'obligation':o['id'],'applicability':clone(binding),'receipt':receipt})
 return graph,binding,observations
rows=[]
for c in s['cases']:
 label='bad' if c['id'].startswith('BAD-') else 'good';graph,binding,obs=bundle(label);current=graph['base_component_sha256'];authority=True
 if c['id']=='MISSING':obs=[x for x in obs if x['obligation']!='state-frame']
 elif c['id']=='OTHER-PROFILE':
  for x in obs:x['applicability']['profile']='other'
 elif c['id']=='RELABEL':
  obs=[x for x in obs if x['obligation']!='source-association'];x=clone(next(x for x in obs if x['obligation']=='state-frame'));x['obligation']='source-association';obs.append(x)
 elif c['id']=='BAD-CONFLICT':
  x=clone(next(x for x in obs if x['obligation']=='application-outcomes'));x['receipt']['outcome']='pass';obs.append(x)
 elif c['id']=='STALE':current='0'*64
 elif c['id']=='DENIED':authority=False
 elif c['id']=='MALFORMED':obs[-1]['receipt']['selected']=True
 actual=q.decide(graph,graph,binding,obs,matcher,current,authority);rows.append({'id':c['id'],'actual':actual,'expected':c['expected'],'matched':actual==c['expected']})
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(x['matched'] for x in rows) else 'FAILED','rows':rows,'reader_reference_calls':len(calls),'matcher_calls':matcher.calls,'business_refuted':{'good':False,'bad':True},'producer_sha256':pin(producer),'scope':'Isolated finite qualification and applicability only. No live registry/default change, authority authentication, durable recovery or production proof.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'decisions':len(rows),'reader_reference_calls':len(calls),'matcher_calls':len(matcher.calls)}));assert result['status']=='PASSED'
