"""Readable owned component sources feed the existing connected change runner."""
from pathlib import Path
import argparse,hashlib,json,sys
P=Path(__file__).resolve().parents[2];D=P/'examples/probes/component-form'
sys.path.insert(0,str(P/'src'));import bagaev_component_form as codec
import component_cycle as component
import component_change_cycle as cycle
def sha(v):return hashlib.sha256(v).hexdigest()
def enc(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
parser=argparse.ArgumentParser(description='Reconstruct the fixed readable components before connected simulated execution.')
parser.add_argument('--output',required=True,type=Path);args,remaining=parser.parse_known_args();out=args.output
assert out.is_absolute() and out.parent.is_dir() and not out.exists();out.mkdir();sources=out/'sources';sources.mkdir();rows=[]
frozen=json.loads((D/'inputs.json').read_bytes())
for name,h in frozen['sha256'].items():assert sha((D/name).read_bytes())==h
suite=json.loads((D/'cases.json').read_bytes())
for alias in ['S1','S2']:
 raw=(D/(alias+'.bagaev')).read_bytes();value=codec.decode(raw);expected=next(c for c in suite['cases'] if c['id']==alias);assert enc(value)==enc(expected['expected_data']);assert sha(enc(value))==expected['expected_checker']['source_sha256'];(sources/(alias+'.json')).write_bytes(enc(value))
 rows.append({'source':alias,'text_sha256':sha(raw),'canonical_component_sha256':sha(enc(value)),'programme_sha256':sha(enc(value['program']))})
for name in ['policy.json','CONTRACT.json']:(sources/name).write_bytes((P/'examples/probes/component-source'/name).read_bytes())
(sources/'inputs.json').write_text(json.dumps({'sha256':{f.name:sha(f.read_bytes()) for f in sorted(sources.iterdir()) if f.is_file()}},indent=2)+'\n')
component.D=sources;sys.argv=[sys.argv[0],*remaining,'--output',str(out/'runtime')];cycle.main()
(out/'source-reconstruction.json').write_text(json.dumps({'status':'PASSED','sources':rows,'scope':'Readable source reconstructed exact existing component/core identities before connected execution; no new expected runtime outputs'},indent=2)+'\n')
