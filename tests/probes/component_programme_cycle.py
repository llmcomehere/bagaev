"""Two distinct serial runs: controlled qualification, then owner-bound live composition."""
from pathlib import Path
import argparse,copy,datetime,hashlib,json,re,subprocess,sys
P=Path(__file__).resolve().parents[2];T=P;D=P/'examples/probes/component-programmes'
sys.path.insert(0,str(T/'src'));sys.path.insert(0,str(T/'tests/probes'))
import bagaev_component_owner as owner;import bagaev_component_edit as edit;import bagaev_component_context as context;import component_change as q
from bagaev_component_programmes import ProgrammeManager,RunError,restore_pending
sha=lambda b:hashlib.sha256(b).hexdigest();clone=copy.deepcopy
for manifest in ['inputs.json']:
 for n,h in json.loads((D/manifest).read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
E=json.loads((D/'connected.json').read_bytes());graph=json.loads((D/'receiving-obligations.json').read_bytes());source_dir=T/'examples/probes/component-source';sources=[json.loads((source_dir/f'{n}.json').read_bytes()) for n in ('S1','S2')];policy=json.loads((source_dir/'policy.json').read_bytes());base=edit.digest(sources[0]);target=edit.digest(sources[1]);assert base==graph['base_component_sha256'] and target==graph['candidate_component_sha256']
parser=argparse.ArgumentParser(description='Source admission and pinned-run simulation with separately reviewed binaries.')
for n in ['reader','reference','matcher']:
 parser.add_argument('--'+n,required=True,type=Path);parser.add_argument('--'+n+'-sha256',required=True)
parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();reader=args.reader;reference=args.reference;matcher=args.matcher;R=args.output
for f,h in [(reader,args.reader_sha256),(reference,args.reference_sha256),(matcher,args.matcher_sha256)]:assert f.is_absolute() and f.is_file() and not f.is_symlink() and re.fullmatch('[0-9a-f]{64}',h) and sha(f.read_bytes())==h
assert R.is_absolute() and R.parent.is_dir()
assert not R.exists();R.mkdir();(R/'matcher').mkdir();q.R=R/'matcher';calls=[];apps=[];phase='draft';conditions={'tick':1,'epoch':1,'submit':True,'write':True,'observe':True,'cancel':True};fault=False
producer_paths={'admission_decider':T/'src/bagaev_component_admission.py','owner':T/'src/bagaev_component_owner.py','manager':T/'src/bagaev_component_programmes.py','adapter':Path(__file__),'component_checker_source':T/'examples/probes/backend/rust/component_source.rs','typed_reference_source':T/'examples/probes/backend/rust/typed_record.rs'}
producers={n:sha(p.read_bytes()) for n,p in producer_paths.items()};profile=edit.digest({'profile':graph['profile'],'producers':producers,'expectations':sha((D/'connected.json').read_bytes())})
binding={'component':target,'program':edit.digest(sources[1]['program']),'policy':edit.digest(policy),'assertions':edit.digest(graph),'profile':graph['profile'],'receiver_profile':profile}
controlled=[{'obligation':o['id'],'applicability':clone(binding),'receipt':{**o['requirement'],'outcome':'pass','selected':0 if o['requirement']['method']=='static' else 1}} for o in graph['obligations']]
def invoke(binary,args,inputs):
 n=len(calls)+1;paths=[]
 for suffix,data in inputs:
  f=R/f'{n:03d}.{suffix}';f.write_bytes(data);paths.append(f)
 r=subprocess.run([str(binary),*args,*map(str,paths)],capture_output=True,timeout=20);(R/f'{n:03d}.stdout').write_bytes(r.stdout);(R/f'{n:03d}.stderr').write_bytes(r.stderr);assert r.returncode==0 and not r.stderr and all(f.read_bytes()==d for f,(_,d) in zip(paths,inputs));calls.append({'n':n,'phase':phase,'binary':binary.name,'input_sha256':[sha(d) for _,d in inputs],'input_names':[name for name,_ in inputs],'output_sha256':sha(r.stdout)});return json.loads(r.stdout)
def checker(source,pol):return invoke(reader,['policy'],[('source.json',source),('policy.json',pol)])
def evaluator(program,args):
 wire=invoke(reference,['run','--input'],[('input.json',edit.canonical({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':args}))])
 if program['functions'][program['entry']]['body'][0]!='arg':
  apps.append({'phase':phase,'program':edit.digest(program),'arguments':clone(args),'value':clone(wire['value']),'call':len(calls)})
  if fault:wire['value']['manual']=['corrupted']
 return wire
def context_checker(program):
 try:edit.checked(program,edit.canonical(policy),checker,'context')
 except edit.ComponentRefused as e:raise context.ComponentRefusal(e.reason,'') from None
 except edit.CheckerUnavailable as e:raise context.ContextUnavailable(str(e)) from None
 return edit.canonical(program)
match=q.Matcher(matcher,args.matcher_sha256)
# Obtain a real checked readable draft, not an alias-selected replacement.
edit_dir=T/'examples/probes/component-edit';inputs=json.loads((edit_dir/'inputs.json').read_bytes())
for n,h in inputs['sha256'].items():assert sha((edit_dir/n).read_bytes())==h
spec=next(c for c in json.loads((edit_dir/'cases.json').read_bytes())['cases'] if c['id']=='BOUND-CANDIDATE');draft=edit.draft(spec['original'],spec['frame'],edit.canonical(policy),checker,candidate_map=spec['candidate_map']);assert draft==spec['expected'] and draft['component']==sources[1]
def trace(observations):
 global conditions
 conditions={'tick':1,'epoch':1,'submit':True,'write':True,'observe':True,'cancel':True};start=len(apps)
 obj=owner.Owner(policy=policy,sources=[sources[0]],state=E['initial'],revision=7,resource='catalogue/g1',checker=checker,evaluator=evaluator,conditions=lambda:clone(conditions));m=ProgrammeManager(obj,initial=base,policy=policy,checker=checker,graph=graph,binding=binding,matcher=match,authority=lambda:True);m.start('original')
 # Before admission S2 is not in the live source registry.
 try:obj.submit(edit.canonical(E['b']));raise AssertionError('unknown candidate executed')
 except owner.OwnerInputError as e:assert e.code=='OWNER_SOURCE'
 a=m.submit('original',edit.canonical(E['a']));assert a==E['a_receipt'];pending=clone(E['pending']);assert pending['packet']==E['a'];a=None # explicit dropped caller reply; receiver keeps receipt
 before=(obj.snapshot(),clone(obj._ledger),clone(m.runs));decision=m.admit(draft['component'],expected_base=base,observations=observations);assert decision=={'decision':'accepted','reason':'all-obligations'};assert (obj.snapshot(),obj._ledger,m.runs)==before and obj.snapshot()==E['after_admission'];m.start('new')
 b=m.submit('new',edit.canonical(E['b']));assert b==E['b_receipt'] and m.runs==E['run_pins']
 before_restore=(obj.snapshot(),clone(obj._ledger),m.head,clone(m.runs),len(apps))
 restored=restore_pending(m,edit.canonical(E['context']),edit.canonical(E['expectation']),pending_sha256=E['pending_sha256'],component_checker=context_checker);inspection=restored['inspection'];data=restored
 assert inspection==E['inspection'] and (obj.snapshot(),obj._ledger,m.head,m.runs,len(apps))==before_restore
 controls=[]
 for rc in json.loads((D/'restore-cases.json').read_bytes())['cases'][1:]:
  saved_head=m.head;saved_runs=clone(m.runs);anchor=E['pending_sha256']
  if rc['variation']=='pending-pin':anchor='0'*64
  elif rc['variation']=='head':m.head=base
  elif rc['variation']=='run':m.runs['original']=target
  before=(obj.snapshot(),clone(obj._ledger),m.head,clone(m.runs),len(apps))
  try:restore_pending(m,edit.canonical(E['context']),edit.canonical(E['expectation']),pending_sha256=anchor,component_checker=context_checker);raise AssertionError('bad continuation accepted')
  except RunError as error:assert error.code==rc['expected']
  assert (obj.snapshot(),obj._ledger,m.head,m.runs,len(apps))==before
  m.head=saved_head;m.runs=saved_runs;controls.append(rc['id'])
 try:m.start('original');raise AssertionError('run repinned')
 except RunError as error:assert error.code=='RUN_DUPLICATE'
 try:m.submit('original',edit.canonical(E['b']));raise AssertionError('wrong source dispatched')
 except RunError as error:assert error.code=='RUN_SOURCE'
 before_observe=len(apps);conditions['observe']=False;assert m.observe(data['run_id'],edit.canonical(data['packet']))==E['denied_observation'];conditions['observe']=True;old=m.observe(data['run_id'],edit.canonical(data['packet']));assert old==E['a_receipt'] and len(apps)==before_observe and obj.snapshot()==E['final']
 selected=apps[start:];assert len(selected)==2 and [x['program'] for x in selected]==[edit.digest(s['program']) for s in sources]
 return {'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'snapshot':obj.snapshot(),'old_receipt':old,'new_receipt':b,'runs':clone(m.runs),'application_calls':clone(selected),'inspection':inspection,'restore_controls':controls,'observation_reinvoked_application':False}
phase='qualification';qualified_trace=trace(controlled)
# Additional actual S2 values and an S2 declared-frame violation.
pure_path=T/'examples/probes/whole-cycle/pure/cases.json';assert sha(pure_path.read_bytes())=='4172d1f7a01aa64a7d8f858f09067d6f003a5f422032491f060570544e796cad';pure_rows=[]
for spec in json.loads(pure_path.read_bytes())['cases']:
 obj=owner.Owner(policy=policy,sources=[sources[1]],state=spec['entry'],revision=7,resource='catalogue/g1',checker=checker,evaluator=evaluator,conditions=lambda:clone(conditions));p=clone(E['a']);p['source']=target;p['request']={'id':clone(spec['entry']['id']),'base':{'value':7},'tags':clone(spec['tags'])};r=obj.submit(edit.canonical(p));assert r['kind']=='Applied' and r['state']==spec['value'];pure_rows.append({'id':spec['id'],'result':r['state'],'matched':True})
obj=owner.Owner(policy=policy,sources=[sources[1]],state=E['initial'],revision=7,resource='catalogue/g1',checker=checker,evaluator=evaluator,conditions=lambda:clone(conditions));fault=True;p=clone(E['a']);p['source']=target
try:obj.submit(edit.canonical(p));raise AssertionError('frame violation committed')
except owner.OwnerEvaluationError as e:assert e.code=='OWNER_FRAME'
fault=False;assert obj.snapshot()=={'state':E['initial'],'revision':7,'mutations':0,'terminal_rows':0}
qualification={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED','profile':profile,'producers':producers,'trace':qualified_trace,'pure_values':pure_rows,'S2_frame_guard':{'code':'OWNER_FRAME','committed':False},'premise':'Isolated qualification trace used controlled pass receipts to exercise run/default behavior, not to establish its own admission precondition.','calls':[clone(c) for c in calls if c['phase']=='qualification']}
raw=edit.canonical(qualification);(R/'qualification.json').write_bytes(raw)
# Verify raw owned observations and immutable producers before deriving receipts.
for n,p in producer_paths.items():assert sha(p.read_bytes())==producers[n]
for c in qualification['calls']:
 assert sha((R/f"{c['n']:03d}.stdout").read_bytes())==c['output_sha256']
 for name,h in zip(c['input_names'],c['input_sha256']):assert sha((R/f"{c['n']:03d}.{name}").read_bytes())==h
assert json.loads(raw)==qualification and qualification['status']=='PASSED' and len(pure_rows)==4 and qualification['trace']['snapshot']==E['final'] and qualification['trace']['old_receipt']==E['a_receipt']
qualified=clone(controlled) # derivable only after the complete checks above, with exact profile binding
phase='live';live=trace(qualified)
result={'status':'PASSED','qualification_sha256':sha(raw),'qualification_at':qualification['at'],'live':live,'calls':calls,'matcher_calls':match.calls,'profile':profile,'scope':'Fresh qualified owner-profile observations followed by separate live simulation. Actual readable edit, pure source and matcher; host authority and in-memory atomicity are premises, not production proof.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({'status':'PASSED','reader_reference_calls':len(calls),'matcher_calls':len(match.calls),'application_calls_by_phase':{p:sum(x['phase']==p for x in apps) for p in ('draft','qualification','live')}})
