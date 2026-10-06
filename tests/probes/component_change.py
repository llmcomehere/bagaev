"""Owned source-bound observation reuse and finite change applicability experiment."""
from pathlib import Path
import argparse,copy,datetime,hashlib,json,re,subprocess,sys
P=Path(__file__).resolve().parents[2];T=P;D=P/'examples/probes/component-change';R=None;MATCHER=None;MATCHER_SHA=None
def enc(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def sha(v):return hashlib.sha256(v).hexdigest()
def need(ok,message):
 if not ok:raise ValueError(message)
def read(p):return json.loads(p.read_bytes())
def verify_cache():
 frozen=read(D/'inputs.json')
 for n,h in frozen['sha256'].items():need(sha((D/n).read_bytes())==h,'changed frozen contract '+n)
 for n,h in frozen['repository_sha256'].items():need(sha((T/n).read_bytes())==h,'changed source/assertion '+n)
 bundle=read(D/'qualification.json');artifacts=bundle['artifacts']
 for name,entry in artifacts.items():need(sha(entry['utf8'].encode())==entry['sha256'],'changed observation '+name)
 for name,h in bundle['producer_source_sha256'].items():need(sha((T/name).read_bytes())==h,'producer source changed '+name)
 def artifact(name):return json.loads(artifacts[name]['utf8'])
 r=artifact('result.json');cases=read(T/'examples/probes/whole-cycle/cases.json')
 need(r['status']=='PASSED' and len(r['rows'])==len(cases['cases']),'prior run incomplete')
 for expected,actual in zip(cases['cases'],r['rows']):
  need(expected['id']==actual['id'],'case ordering')
  for k,v in expected['expected'].items():need(actual['actual'].get(k)==v,'prior literal trace mismatch')
 for call in r['reference_calls']:
  prefix=f"{call['n']:03d}";need(artifacts[prefix+'.input.json']['sha256']==call['input_sha256'],'input observation binding');need(artifacts[prefix+'.stdout']['sha256']==call['output_sha256'],'result observation binding')
 graph=read(D/'receiving-obligations.json');static=artifact('S2.check.stdout')
 need(static['status']=='checked' and static['policy_compatible'] is True and static['execution_admission'] is False,'source ground')
 for wire,key in [('source_sha256','candidate_component_sha256'),('program_sha256','candidate_program_sha256'),('policy_sha256','policy_sha256')]:need(static[wire]==graph[key],'static ground identity')
 wc=next(x for x in r['rows'] if x['id']=='WC17');bindings=wc['bindings'];pure=[x for x in bindings if x['label'].startswith('admission-S2-')]
 pure_cases=read(T/'examples/probes/whole-cycle/pure/cases.json')['cases'];need(len(pure)==len(pure_cases)==4,'pure witness set')
 for expected,binding in zip(pure_cases,pure):
  need(binding['label']=='admission-S2-'+expected['id'],'pure assertion identity')
  need(binding['result_sha256']==sha(enc(expected['value'])),'pure literal value binding')
 need(any(g['fault']=='manual' and g['observed']=='declared component frame' and g['committed'] is False for g in r['guards']),'preservation guard ground')
 effects=[x for x in bindings if x['operation_key'] is not None]
 need([x['source'] for x in effects]==['S1','S2'] and [x['operation_key']['id'] for x in effects]==['A','B'],'actual consumer/old run witness')
 need(effects[1]['component_sha256']==graph['candidate_component_sha256'] and effects[1]['program_sha256']==graph['candidate_program_sha256'],'actual candidate dispatch')
 # Source bindings and full literal WC17 projections above include R8/R9 and no replay call.
 binding={'component':graph['candidate_component_sha256'],'program':graph['candidate_program_sha256'],'policy':graph['policy_sha256'],'assertions':sha(enc(graph)),'profile':graph['profile']}
 observations=[]
 for o in graph['obligations']:
  receipt={**o['requirement'],'outcome':'pass','selected':0 if o['requirement']['method']=='static' else 1}
  observations.append({'obligation':o['id'],'applicability':copy.deepcopy(binding),'receipt':receipt})
 return graph,binding,observations,{'original_execution_at':r['at'],'qualified_result_sha256':artifacts['result.json']['sha256'],'prior_artifacts_verified':len(artifacts),'qualification_reexecuted':False}
class Matcher:
 def __init__(self,binary,binary_sha):
  self.binary=binary;self.calls=[];need(sha(binary.read_bytes())==binary_sha,'matcher executable identity')
  self.program=read(T/'examples/probes/evidence-obligations/program.json')
 def group(self,requirements,receipts):
  n=len(self.calls)+1;f=R/f'match-{n:03d}.json';data=enc({'schema':'bagaev-typed-record-invocation/8','program':self.program,'arguments':[requirements,receipts]});f.write_bytes(data)
  q=subprocess.run([str(self.binary),str(f)],capture_output=True,timeout=20);(R/f'match-{n:03d}.stdout').write_bytes(q.stdout);(R/f'match-{n:03d}.stderr').write_bytes(q.stderr)
  need(q.returncode==0 and not q.stderr and f.read_bytes()==data,'matcher environment');out=json.loads(q.stdout)
  need(out['status']=='success' and out['value_type']=='Record:Admission','matcher refused')
  self.calls.append({'input_sha256':sha(data),'output_sha256':sha(q.stdout),'value':out['value']});return out['value']
def decide(graph,trusted,binding,observations,matcher,base,authority):
 def out(d,r):return {'decision':d,'reason':r}
 if enc(graph)!=enc(trusted):return out('invalid','requirements')
 if type(observations)is not list or len(observations)>10:return out('invalid','receipts')
 ids={o['id'] for o in trusted['obligations']};dims={'domain':{'artifact','request'},'subject':{'A','B'},'method':{'bytes','static','runtime'},'binding':{'fixture','consumer','detached'},'scope':{'partial','complete'}}
 for o in observations:
  if type(o)is not dict or set(o)!={'obligation','applicability','receipt'} or type(o['obligation'])is not str or o['obligation'] not in ids:return out('invalid','receipts')
  a=o['applicability'];v=o['receipt']
  if type(a)is not dict or set(a)!=set(binding) or any(type(x)is not str for x in a.values()):return out('invalid','receipts')
  if type(v)is not dict or set(v)!=set(dims)|{'revision','outcome','selected'}:return out('invalid','receipts')
  if any(type(v[k])is not str or v[k]not in values for k,values in dims.items()):return out('invalid','receipts')
  if type(v['revision'])is not int or not 0<=v['revision']<=2 or type(v['selected'])is not int or not 0<=v['selected']<=2:return out('invalid','receipts')
  if type(v['outcome'])is not str or v['outcome']not in {'pass','unknown','refuted','withdrawn'} or (v['method']!='runtime' and v['selected']!=0):return out('invalid','receipts')
 by_id={o['id']:o['requirement'] for o in trusted['obligations']}
 applicable=[o for o in observations if o['applicability']==binding and all(o['receipt'][k]==v for k,v in by_id[o['obligation']].items())];groups=[]
 for ids_in_group in trusted['groups']:
  req=[o['requirement'] for o in trusted['obligations'] if o['id'] in ids_in_group];receipts=[o['receipt'] for o in applicable if o['obligation'] in ids_in_group]
  if len(receipts)>4:return out('invalid','receipts')
  groups.append((req,receipts))
 # All wrappers/groups validated before any accepted group can matter.
 results=[matcher.group(q,r) for q,r in groups]
 if any(x['reason']=='conflicting-evidence' for x in results):return out('pending','conflicting-evidence')
 if any(x['decision']!='accepted' for x in results):return out('pending','missing-obligation')
 if base!=trusted['base_component_sha256']:return out('stale','base-changed')
 if authority is not True:return out('denied','admission-authority')
 return out('accepted','all-obligations')
def main():
 graph,binding,positive,cache=verify_cache()
 matcher=Matcher(MATCHER,MATCHER_SHA);rows=[]
 for case in read(D/'decision-cases.json')['cases']:
  g=copy.deepcopy(graph);obs=copy.deepcopy(positive);base=graph['base_component_sha256'];authority=True;v=case['variation']
  if v=='omit-consumer-duplicate-pure':obs=[o for o in obs if o['obligation']!='actual-entry-consumer'];obs.append(copy.deepcopy(obs[1]))
  elif v=='other-source':
   for o in obs:o['applicability']['component']='0'*64
  elif v=='other-expectation':
   for o in obs:o['applicability']['assertions']='0'*64
  elif v=='bytes-only':
   for o in obs:
    if o['receipt']['method']=='runtime':o['receipt'].update(method='bytes',selected=0)
  elif v=='negative-zero-selection-and-missing':
   obs=[o for o in obs if o['obligation']!='actual-entry-consumer'];negative=copy.deepcopy(obs[1]);negative['receipt'].update(outcome='refuted',selected=0);obs.append(negative)
  elif v=='stale-base':base='0'*64
  elif v=='no-authority':authority=False
  elif v=='unrelated-negative':
   negative=copy.deepcopy(obs[1]);negative['applicability']['component']='0'*64;negative['receipt'].update(outcome='withdrawn',selected=0);obs.append(negative)
  elif v=='malformed-last-receipt':obs[-1]['receipt']['selected']=True
  elif v=='remove-required-consumer':g['obligations']=[o for o in g['obligations'] if o['id']!='actual-entry-consumer']
  else:need(v=='none','unknown case variation')
  actual=decide(g,graph,binding,obs,matcher,base,authority);rows.append({'id':case['id'],'actual':actual,'expected':case['expected'],'matched':actual==case['expected']})
 swapped=copy.deepcopy(positive);swapped[0]['obligation'],swapped[1]['obligation']=swapped[1]['obligation'],swapped[0]['obligation']
 actual=decide(graph,graph,binding,swapped,matcher,graph['base_component_sha256'],True);expected=read(D/'obligation-binding-control.json')['expected'];rows.append({'id':'MISLABELLED-OBLIGATION','actual':actual,'expected':expected,'matched':actual==expected})
 result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(x['matched'] for x in rows) else 'FAILED','rows':rows,'prior_qualification':cache,'new_matcher_calls':matcher.calls,'scope':'New applicability decisions using exactly verified prior owned observations; no new component qualification, production authority or durability'}
 (R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'matched':sum(x['matched'] for x in rows),'requested':len(rows),'new_matcher_calls':len(matcher.calls),'prior_qualification_reexecuted':False}));need(result['status']=='PASSED','decision mismatch')
def configure(args=None):
 global R,MATCHER,MATCHER_SHA
 parser=argparse.ArgumentParser(description='Finite source-bound applicability of retained synthetic observations; no execution authority.')
 parser.add_argument('--matcher',required=True,type=Path);parser.add_argument('--matcher-sha256',required=True);parser.add_argument('--output',required=True,type=Path)
 ns=parser.parse_args(args)
 need(ns.matcher.is_absolute() and ns.matcher.is_file() and not ns.matcher.is_symlink(),'matcher regular absolute file')
 need(re.fullmatch('[0-9a-f]{64}',ns.matcher_sha256) is not None and sha(ns.matcher.read_bytes())==ns.matcher_sha256,'matcher identity')
 need(ns.output.is_absolute() and ns.output.parent.is_dir() and not ns.output.exists(),'fresh absolute output with existing parent')
 ns.output.mkdir();R=ns.output;MATCHER=ns.matcher;MATCHER_SHA=ns.matcher_sha256
if __name__=='__main__':configure();main()
