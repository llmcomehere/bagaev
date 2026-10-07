from pathlib import Path
import json,hashlib,copy,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/tag-box-budget'
from outcome_host import configure
args=configure(reference=True);R=args.output
sys.path[:0]=[str(T/'src'),str(T/'tests/probes')]
import bagaev_component_fold_form as form
import bagaev_component_edit as edit
import bagaev_owner_image_store as storage
import bagaev_component_owner as owner
from bagaev_outcome_storage import Bridge
from persistence_host import Native,explicit
for name,pin in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==pin
s=json.loads((D/'cases.json').read_bytes());raw=(D/'TagBoxBudget.bagaev').read_bytes();assert form.decode(raw)==s['source'];assert form.decode(form.encode(s['source']))==s['source']
explicit({k:str(getattr(args,k)) for k in ('reader','reference','reader_sha256','reference_sha256')})
R.mkdir(exist_ok=False);conditions=copy.deepcopy(s['conditions']);rows=[]
for case in s['cases']:
 n=Native(R/(case['id']+'-native'));db=R/(case['id']+'.sqlite')
 def bridge():return Bridge(case['config'],checker=n.checker,evaluator=n.evaluator,conditions=lambda:copy.deepcopy(conditions))
 m=bridge();m.create(db);packet=edit.canonical(case['packet']);before=storage.read(db)
 if case['core_reason']:
  try:m.call(db,'submit',packet)
  except owner.OwnerEvaluationError as error:assert error.code=='OWNER_EVALUATION'
  else:raise AssertionError('computation refusal became terminal receipt')
  wire=json.loads((n.out/f'{len(n.calls):03d}.stdout').read_bytes());assert wire['reason']==case['core_reason'];assert storage.read(db)==before and n.apps==1
  rows.append({'id':case['id'],'core_reason':wire['reason'],'generation':0,'business_evaluations':n.apps,'native_calls':len(n.calls)});continue
 actual=m.call(db,'submit',packet);assert actual==case['receipt'],(case['id'],actual);saved=storage.read(db);image=json.loads(saved['image']);assert saved['generation']==case['generation'] and image['revision']==case['revision'] and image['state']==case['state'] and image['mutations']==case['mutations'] and n.apps==1
 m=bridge();assert m.call(db,'observe',packet)==case['receipt'];assert storage.read(db)==saved and n.apps==1
 rows.append({'id':case['id'],'receipt':actual,'generation':saved['generation'],'business_evaluations':n.apps,'native_calls':len(n.calls)})
assert (D/'TagBoxBudget.bagaev').read_bytes()==raw
result={'status':'PASSED','cases':rows,'business_evaluations':sum(x['business_evaluations'] for x in rows),'native_calls':sum(x['native_calls'] for x in rows),'replay_new_evaluations':0,'scope':'Nine frozen boundary cases; unchanged runtime and serial SQLite profile; fresh object, not process-crash test.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='cases'})
