from pathlib import Path
import json,hashlib,sys,subprocess,argparse
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/wide-authoring'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_wide_format as formatter
for c in json.loads((D/'format.json').read_bytes()):
 out=formatter.format_source(c['source']);assert out==c['expected'].encode(),(c['id'],out);assert formatter.format_source(out)==out
source=T/'examples/probes/catalog-wide/Catalog.bagaev';raw=source.read_bytes();out=formatter.format_source(raw);assert formatter.format_source(out)==out and formatter.form.decode(out)==formatter.form.decode(raw);assert (D/'Catalog.formatted.bagaev').read_bytes()==out;(R/'Catalog.bagaev').write_bytes(out)
cli_out=R/'cli.bagaev';q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_format.py'),'--form','5',str(source),'--output',str(cli_out)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and cli_out.read_bytes()==out and source.read_bytes()==raw
saved=cli_out.read_bytes();q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_format.py'),'--form','5',str(source),'--output',str(cli_out)],capture_output=True,timeout=20);assert q.returncode==2 and json.loads(q.stdout)['error']['code']=='RECORD_PATH' and cli_out.read_bytes()==saved
try:formatter.format_source(b'bagaev record-form/1; program { entry calc; fn calc() -> Int64 = 1; }')
except formatter.form.FormError as e:assert e.code=='FORM_VERSION'
else:raise AssertionError('old version accepted')
r={'status':'PASSED','exact_format_cases':2,'catalog_graph_preserved':True,'idempotent':True,'cli_calls':2,'refusals':2,'runtime_calls':0,'formatted_bytes':len(out),'lines':len(out.splitlines())};(R/'result.json').write_text(json.dumps(r)+'\n');print(r)
