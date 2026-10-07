"""Own exact source-location fixtures; unchanged error-code priority."""
from pathlib import Path
import argparse,copy,hashlib,json,subprocess,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/l2-filter'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists()
sys.path.insert(0,str(T))
from src import bagaev_l2_filter as L
f=json.loads((D/'reference-location-manifest.json').read_bytes());assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==h for n,h in f['sha256'].items());R.mkdir(exist_ok=False);rows=[];enc=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=True,separators=(',',':'))
for c in json.loads((D/'reference-location-cases.json').read_bytes())['cases']:
 draft=copy.deepcopy(c['draft']);before=enc(draft)
 try:L.prepare_program(draft)
 except L.L2Error as e:
  assert e.code==c['error'] and e.location==c['location'] and e.args==(c['error'],),(c['id'],e.code,e.location)
  if e.location is not None:e.location.clear()
 else:raise AssertionError('new accepted')
 assert enc(draft)==before
 src=R/(c['id']+'.json');src.write_text(enc(draft));dest=R/(c['id']+'-output.json');q=subprocess.run([sys.executable,'-B','-S','-m','src.bagaev_filter','prepare',str(src),'--output',str(dest)],cwd=T,capture_output=True,timeout=20);assert q.returncode==2 and not q.stderr and not dest.exists();wire=json.loads(q.stdout);assert wire['error']['code']==c['error'] and wire['error']['location']==c['location'];assert len(q.stdout)<5000;(R/(c['id']+'.stdout')).write_bytes(q.stdout);rows.append({'id':c['id'],'code':c['error'],'location':c['location']})
for c in json.loads((D/'reference-location-cases.json').read_bytes())['cases']:
 source={'schema':'bagaev-l2/2','entry':c['draft']['entry'],'definitions':c['draft']['definitions'],'pins':{}}
 src=R/(c['id']+'-program.json');src.write_text(enc(source))
 q=subprocess.run([sys.executable,'-B','-S','-m','src.bagaev_filter','check',str(src)],cwd=T,capture_output=True,timeout=20)
 assert q.returncode==2 and not q.stderr
 wire=json.loads(q.stdout);assert wire['error']['code']==c['error'] and wire['error']['location']==c['location']
 (R/(c['id']+'.check.stdout')).write_bytes(q.stdout)
valid={'schema':'bagaev-l2-draft/2','entry':'main','definitions':{'main':{'params':['x'],'body':['literal',['var','lost']]}}};assert L.evaluate(L.prepare_program(valid),None)==['var','lost']
boundary_rows=[]
for c in json.loads((D/'reference-location-boundaries.json').read_bytes())['cases']:
 try:L.prepare_program(c['draft'])
 except L.L2Error as e:assert e.code==c['error'] and e.location==c['location']
 else:raise AssertionError(c['id'])
 boundary_rows.append(c['id'])
result={'status':'PASSED','frozen_cases':len(rows),'cli_refusals':2*len(rows),'literal_error_codes_matched':True,'supplementary_boundary_cases':len(boundary_rows),'input_preserved':True,'metadata_detached':True,'literal_data_not_reference':True,'rows':rows};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
