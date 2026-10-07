"""Exact data-form expectations and finite observations through reviewed hosts."""
from pathlib import Path
import copy,hashlib,json,subprocess,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-arithmetic'
sys.path.insert(0,str(T/'src'))
import bagaev_component_arithmetic_form as form
import bagaev_component_outcome_form as prior
from outcome_host import configure
args=configure(reference=True);R=args.output
manifest=json.loads((D/'manifest.json').read_bytes())
for n,h in manifest['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
for n,h in manifest['old_codecs'].items():assert hashlib.sha256((T/'src'/n).read_bytes()).hexdigest()==h
R.mkdir(exist_ok=False);suite=json.loads((D/'cases.json').read_bytes());rows=[]
for c in suite['positive']:
 actual=form.decode(c['text']);assert actual==c['expected_source'],c['id'];before=json.dumps(actual,sort_keys=True);encoded=form.encode(actual);assert json.dumps(actual,sort_keys=True)==before;assert form.decode(encoded)==actual and form.encode(form.decode(encoded))==encoded
 (R/(c['id']+'.bagaev')).write_bytes(encoded);rows.append({'id':c['id'],'exact_source':True,'stable_roundtrip':True})
for c in suite['negative']:
 text=suite['template'].replace('\n}','\n fn bad(state: Stock) -> Int64 = '+c['expression']+';\n}')
 try:form.decode(text)
 except form.FormError as e:assert e.code==c['error'],(c['id'],e.code)
 else:raise AssertionError(c['id'])
 rows.append({'id':c['id'],'error':c['error']})
for codec,text in [(prior,suite['template']),(form,suite['template'].replace('component-form/3','component-form/2'))]:
 try:codec.decode(text)
 except form.FormError as e:assert e.code=='FORM_VERSION'
 else:raise AssertionError('profile fallback')
boundary_rows=[]
for name,body in [('unbound-use',['use','missing']),('bool-as-int',['int',True]),('captured-arg',['let','n',['int',1],['arg','n']])]:
 value=copy.deepcopy(suite['positive'][0]['expected_source']);value['program']['functions']['calc']['body']=body;before=json.dumps(value,sort_keys=True)
 try:form.encode(value)
 except form.FormError as e:assert e.code=='FORM_PROFILE'
 else:raise AssertionError(name)
 assert json.dumps(value,sort_keys=True)==before;boundary_rows.append({'id':name,'error':'FORM_PROFILE'})
for name,expr in [('long-left-chain','+'.join(['1']*300)),('deep-group','('*140+'1'+')'*140),('deep-field','state'+'.key'*140)]:
 text=suite['template'].replace('\n}','\n fn calc(state: Stock) -> Int64 = '+expr+';\n}')
 try:form.decode(text)
 except form.FormError as e:assert e.code=='FORM_BOUNDS'
 else:raise AssertionError(name)
 boundary_rows.append({'id':name,'error':'FORM_BOUNDS'})
observations=[]
def run(program,arguments,label):
 raw=json.dumps({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':arguments},sort_keys=True,separators=(',',':')).encode();f=R/(label+'.json');f.write_bytes(raw)
 q=subprocess.run([str(args.reference),'run','--input',str(f)],capture_output=True,timeout=20);(R/(label+'.stdout')).write_bytes(q.stdout);(R/(label+'.stderr')).write_bytes(q.stderr);assert q.returncode==0 and not q.stderr and f.read_bytes()==raw;v=json.loads(q.stdout);observations.append({'id':label,'observation':v});return v
stock=form.decode((D/'StockAdjustment.bagaev').read_bytes());assert stock==json.loads((D/'source.json').read_bytes())
state={'key':{'code':'sku1'},'note':'kept','quantity':10}
for i,c in enumerate(json.loads((D/'semantic-values.json').read_bytes())):
 v=run(stock['program'],[{**state,'quantity':c['state_quantity']},{'item':state['key'],'expected':{'value':7},'delta':c['delta']}],'stock-'+str(i));w=c['expected'];expected={'case':w['case'],'value':{'reason':w['reason']} if w['case']=='Decline' else {**state,'quantity':w['quantity']}}
 assert v['status']=='success' and v['value_type']=='Variant:StockOutcome' and v['value']==expected
extra=json.loads((D/'core-expectations.json').read_bytes())
for c in extra['calc']:
 source=form.decode(next(x['text'] for x in suite['positive'] if x['id']==c['id']));program=copy.deepcopy(source['program']);program['entry']='calc';v=run(program,[state],c['id']);assert v['status']=='success' and type(v['value'])is type(c['value']) and v['value']==c['value']
c=extra['overflow'];v=run(stock['program'],[{**state,'quantity':c['state_quantity']},{'item':state['key'],'expected':{'value':7},'delta':c['delta']}],'overflow');assert v['status']==c['status'] and v['reason']==c['reason']
for i,c in enumerate(extra['binding_refusals']):
 text=suite['template'].replace('\n}','\n fn calc(state: Stock) -> Int64 = '+c['expression']+';\n}');program=form.decode(text)['program'];program['entry']='calc';v=run(program,[state],'binding-'+str(i));assert v['reason']==c['reason']
q=subprocess.run([str(args.reader),'policy',str(D/'source.json'),str(D/'policy.json')],capture_output=True,timeout=20);(R/'policy.stdout').write_bytes(q.stdout);assert q.returncode==0 and not q.stderr;wire=json.loads(q.stdout);assert wire['status']=='checked' and wire['policy_compatible'] is True and wire['execution_admission'] is False
result={'status':'PASSED','exact_sources':11,'syntax_refusals':8,'version_refusals':2,'native_invocations':len(observations),'source_policy_checks':1,'boundary_refusals':len(boundary_rows),'boundary_rows':boundary_rows,'rows':rows,'observations':observations,'scope':'Existing core; literal values/reasons checked, full work/location wires retained as observations.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('rows','observations')}))
