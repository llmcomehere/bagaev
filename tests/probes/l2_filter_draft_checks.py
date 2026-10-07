"""Own explicit authoring checks against pre-implementation literal outputs."""
from pathlib import Path
import argparse,copy,hashlib,json,subprocess,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/l2-filter'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists()
sys.path.insert(0,str(T))
from src import bagaev_l2_filter as L
enc=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
f=json.loads((D/'draft-manifest.json').read_bytes());assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==h for n,h in f['sha256'].items());cases=json.loads((D/'draft-cases.json').read_bytes());R.mkdir(exist_ok=False)
for c in cases['valid']:
 draft=copy.deepcopy(c['draft']);before=enc(draft)
 for value in (draft,enc(draft),enc(draft).decode()):
  got=L.prepare_program(value);assert got.canonical==enc(c['expected']) and got.digest==c['expected_digest'];assert L.check_program(got).canonical==got.canonical
 assert enc(draft)==before
 draft['definitions'].clear();assert got.canonical==enc(c['expected'])
for c in cases['refusals']:
 try:L.prepare_program(c['draft'])
 except L.L2Error as e:assert e.code==c['error'],(c['id'],e.code)
 else:raise AssertionError(c['id'])
for bad,code in [(b'{','L2_JSON'),(b'{"schema":0,"schema":1}','L2_JSON'),(b' '*1048577,'L2_BOUNDS')]:
 try:L.prepare_program(bad)
 except L.L2Error as e:assert e.code==code
 else:raise AssertionError('text admitted')
plain=cases['valid'][0]['expected'];bad={**plain,'pins':{}}
try:L.check_program(bad)
except L.L2Error as e:assert e.code=='L2_PIN'
else:raise AssertionError('check repaired pins')
rows=[]
def cli(args,error=None,tree=T):
 q=subprocess.run([sys.executable,'-B','-S','-m','src.bagaev_filter',*map(str,args)],cwd=tree,capture_output=True,timeout=20);i=len(rows);(R/f'{i:02}.stdout').write_bytes(q.stdout);(R/f'{i:02}.stderr').write_bytes(q.stderr);assert q.returncode==(2 if error else 0) and not q.stderr,(args,q.stdout,q.stderr);v=json.loads(q.stdout);assert v['ok'] is (error is None)
 if error:assert v['error']['code']==error,(v,error)
 rows.append({'args':list(map(str,args)),'expected_error':error});return v
src=R/'draft.json';src.write_bytes(enc(cases['valid'][1]['draft']));output=R/'program.json';cli(['prepare',src,'--output',output]);assert output.read_bytes()==enc(cases['valid'][1]['expected']);cli(['check',output]);inp=R/'input.json';inp.write_text('[1,2]');assert cli(['run',output,'--input',inp])['result']['value']==[1,2]
cli(['prepare',src,'--output',output],'TOOL_OUTPUT');assert output.read_bytes()==enc(cases['valid'][1]['expected']);cli(['check',src],'L2_PROGRAM');fresh=R/'refused.json';cli(['prepare',output,'--output',fresh],'L2_PROGRAM');assert not fresh.exists()
for c in cases['refusals']:
 srcbad=R/(c['id']+'.json');srcbad.write_bytes(enc(c['draft']));cli(['prepare',srcbad,'--output',fresh],c['error']);assert not fresh.exists()
link=R/'draft-link.json';link.symlink_to(src);cli(['prepare',link,'--output',fresh],'TOOL_INPUT');assert not fresh.exists()
q=D/'queue.json';b=R/'queue-artifact.json';cli(['compile',q,'--output',b]);assert hashlib.sha256(b.read_bytes()).hexdigest()==f['previous_queue_artifact_sha256']
queue_prepared=R/'queue-prepared.json';cli(['prepare',D/'queue-draft.json','--output',queue_prepared]);assert queue_prepared.read_bytes()==L.check_program(q.read_bytes()).canonical
result={'status':'PASSED','valid_literal_programs':4,'input_forms_each':3,'refusal_drafts':9,'text_refusals':3,'check_still_rejects_unpinned':True,'cli_calls':len(rows),'cli_refusals':sum(x['expected_error']is not None for x in rows),'existing_queue_artifact_unchanged':True,'rows':rows};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
