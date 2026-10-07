"""Frozen literal spans and pin/pointer boundaries for optional location lookup."""
from pathlib import Path
import json,hashlib,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-expression-locations'
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists()
sys.path.insert(0,str(T/'src'));import bagaev_component_expression_locations as loc
import bagaev_component_match_form as form
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
R.mkdir(exist_ok=False);s=json.loads((D/'cases.json').read_bytes());rows=[]
s['cases']+=json.loads((D/'supplemental.json').read_bytes())['cases']
canonical=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
for c in s['cases']:
 raw=c['source'].encode();source_pin=hashlib.sha256(raw).hexdigest();component_pin=hashlib.sha256(canonical(c['component'])).hexdigest()
 assert form.decode(raw)==c['component'];assert loc.Reader(raw).read()==c['component']
 result=loc.locate(raw,c['pointer'],source_sha256=source_pin,component_sha256=component_pin)
 expected={'schema':loc.SCHEMA,'form':'component-form/4','source_sha256':source_pin,'component_sha256':component_pin,'pointer':c['pointer'],'span':c['expected_span'],'semantic_check':False,'execution_admission':False};assert result==expected,(c['id'],result,expected);rows.append({'id':c['id'],'result':result})
c=s['cases'][0];raw=c['source'].encode();a=hashlib.sha256(raw).hexdigest();b=hashlib.sha256(canonical(c['component'])).hexdigest();refusals=[]
for name,pointer,x,y,wanted in [('source',c['pointer'],'0'*64,b,'LOCATION_SOURCE'),('component',c['pointer'],a,'0'*64,'LOCATION_COMPONENT'),('pin',c['pointer'],'BAD',b,'LOCATION_PIN'),('pointer','bad',a,b,'LOCATION_POINTER'),('escape','/~2',a,b,'LOCATION_POINTER'),('pointer-bound','/'+('a'*4096),a,b,'LOCATION_POINTER'),('pointer-kind',None,a,b,'LOCATION_POINTER')]:
 try:loc.locate(raw,pointer,source_sha256=x,component_sha256=y)
 except loc.LocationError as e:assert e.code==wanted;refusals.append(name)
 else:raise AssertionError(name)
result={'status':'PASSED','exact_locations':len(rows),'refusals':len(refusals),'rows':rows,'scope':'Source-bound expression contexts only; no typechecking or execution.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
