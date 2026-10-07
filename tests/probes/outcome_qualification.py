"""Validate exact retained fresh qualification; no executable imports from artifacts."""
from pathlib import Path
import copy,hashlib,json,sys
P=Path(__file__).resolve().parents[2]
enc=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
sha=lambda b:hashlib.sha256(b).hexdigest();pin=lambda v:sha(enc(v))
def load(directory,expected_hashes,executables):
 D=P/'examples/probes/component-outcomes/admission';R=directory
 for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
 inputs=json.loads((D/'inputs.json').read_bytes());producer=json.loads((R/'producer-before.json').read_bytes());result=json.loads((R/'result.json').read_bytes())
 for name,h in expected_hashes.items():assert sha((R/name).read_bytes())==h
 assert result['status']=='PASSED' and result['producer_sha256']==pin(producer)
 assert sha(Path(sys.executable).read_bytes())==producer['python_sha256'] and sys.version==producer['python_version']
 expected_fixed={str(p.resolve()) for p in [D/'inputs.json',D/'contract.md',P/'examples/probes/component-outcomes/pure/corrected-cases.json',P/'examples/probes/component-outcomes/owner/cases.json',P/'examples/probes/evidence-obligations/program.json',*executables]}
 assert set(producer['fixed'])==expected_fixed
 for name,h in producer['own_python'].items():
  path=Path(name);assert path.resolve().is_relative_to(P) and sha(path.read_bytes())==h
 for name,h in producer['fixed'].items():assert sha(Path(name).read_bytes())==h
 qualifications={label:json.loads((R/(label+'-qualification.json')).read_bytes()) for label in ('good','bad')}
 index=0
 for label in ('good','bad'):
  raw=qualifications[label];assert raw['candidate']==pin(inputs[label]);assert raw['business_refuted']==(label=='bad')
  for call in raw['calls']:
   index+=1;prefix=f'{index:03d}';names=['source.json','policy.json'] if call['binary']=='reader' else ['invocation.json']
   assert [sha((R/(prefix+'.'+n)).read_bytes()) for n in names]==call['inputs']
   assert sha((R/(prefix+'.stdout')).read_bytes())==call['output'] and (R/(prefix+'.stderr')).read_bytes()==b''
 assert index==result['reader_reference_calls']==42
 good=qualifications['good'];assert all(v['matched'] for v in good['values']) and len(good['values'])==5
 assert good['frame_guard']=='OWNER_FRAME without mutation'
 graph=inputs['graph'];candidate=inputs['good']
 assert good['source_association']==[pin(inputs['source1']['program']),pin(candidate['program'])]
 assert good['trace']['application_evaluations']==2 and good['trace']['revision']==8 and good['trace']['mutations']==1
 binding={'component':pin(candidate),'program':pin(candidate['program']),'policy':pin(inputs['policy']),'assertions':pin(graph),'profile':graph['profile'],'producer':pin(producer),'qualification':pin(good)}
 obs=[{'obligation':o['id'],'applicability':copy.deepcopy(binding),'receipt':{**o['requirement'],'outcome':'pass','selected':0 if o['requirement']['method']=='static' else 1}} for o in graph['obligations']]
 return inputs,graph,binding,obs,{'producer':pin(producer),'qualification':pin(good),'verified_prior_calls':42,'qualification_reexecuted':False}
