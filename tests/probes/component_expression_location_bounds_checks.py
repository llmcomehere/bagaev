"""Supplemental review controls for unqueryable paths and unchanged syntax bounds."""
from pathlib import Path
import sys,json,hashlib
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-expression-locations'
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists()
R.mkdir(exist_ok=False)
sys.path.insert(0,str(T/'src'));import bagaev_component_expression_locations as loc
import bagaev_component_match_form as form
c=json.loads((D/'cases.json').read_bytes())['cases'][0];canonical=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode();pin=lambda x:hashlib.sha256(x).hexdigest();rows=[]
long=c['source'].replace('fn quantity(', 'fn '+('a'*5000)+'(');a=loc.Reader(long);value=a.read();assert value==form.decode(long);assert all(len(p)<=4096 for p in a.locations);assert not any('/'+'a'*5000+'/' in p for p in a.locations);assert loc.locate(long,'/component',source_sha256=pin(long.encode()),component_sha256=pin(canonical(value)))['span'] is None;rows.append('long-identifier-unqueryable')
try:loc.locate('\n'+c['source'],c['pointer'],source_sha256=pin(c['source'].encode()),component_sha256=pin(canonical(c['component'])))
except loc.LocationError as e:assert e.code=='LOCATION_SOURCE';rows.append('shifted-source-pin')
else:raise AssertionError('stale source accepted')
for name,text in [('bytes',' '*1048577),('tokens','bagaev component-form/4; '+'x '*32769)]:
 codes=[]
 for call in [lambda:form.decode(text),lambda:loc.Reader(text).read()]:
  try:call()
  except form.FormError as e:codes.append(e.code)
  else:raise AssertionError(name)
 assert codes==['FORM_BOUNDS','FORM_BOUNDS'];rows.append(name)
old=json.loads((T/'examples/probes/component-match/cases.json').read_bytes())
for c in old['positive']:assert loc.Reader(c['source']).read()==c['expected'];rows.append('prior-'+c['id'])
for c in old['syntax']:
 try:loc.Reader(c['source']).read()
 except form.FormError as e:assert e.code==c['code'];rows.append('prior-'+c['id'])
 else:raise AssertionError(c['id'])
(R/'result.json').write_text(json.dumps({'status':'PASSED','controls':rows},indent=2)+'\n');print(json.dumps({'status':'PASSED','controls':len(rows)}))
