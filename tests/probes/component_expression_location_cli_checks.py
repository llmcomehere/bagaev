"""Bounded location tool: success/null, stale pins and transport refusals."""
from pathlib import Path
import json,sys,hashlib,subprocess
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-expression-locations'
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists()
R.mkdir(exist_ok=False)
c=json.loads((D/'cases.json').read_bytes())['cases'][0];raw=c['source'].encode();f=R/'source.bagaev';f.write_bytes(raw);a=hashlib.sha256(raw).hexdigest();b=hashlib.sha256(json.dumps(c['component'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest();rows=[]
def call(name,path,pointer,sourcepin=a,componentpin=b,error=None):
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/component_locate.py'),str(path),pointer,'--source-sha256',sourcepin,'--component-sha256',componentpin],capture_output=True,timeout=20);(R/(name+'.stdout')).write_bytes(q.stdout);assert q.returncode==(2 if error else 0) and not q.stderr;v=json.loads(q.stdout);assert v['semantic_check'] is False and v['execution_admission'] is False
 if error:assert v['error']['code']==error,v
 rows.append(name);return v
assert call('located',f,c['pointer'])['span']==c['expected_span'];assert call('unmapped',f,'/component/name')['span'] is None
call('stale-source',f,c['pointer'],sourcepin='0'*64,error='LOCATION_SOURCE');call('stale-component',f,c['pointer'],componentpin='0'*64,error='LOCATION_COMPONENT');call('pointer',f,'/~2',error='LOCATION_POINTER');call('directory',R,c['pointer'],error='COMPONENT_PATH');link=R/'link.bagaev';link.symlink_to(f);call('symlink',link,c['pointer'],error='COMPONENT_PATH');assert f.read_bytes()==raw
(R/'result.json').write_text(json.dumps({'status':'PASSED','calls':len(rows),'rows':rows})+'\n');print(json.dumps({'status':'PASSED','calls':len(rows)}))
