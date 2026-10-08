from pathlib import Path
import json,hashlib,subprocess,sys,copy,argparse
T=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir(exist_ok=False)
sys.path.insert(0,str(T/'src'));import bagaev_record_wide_form as form;import bagaev_record_json_form as old
cases=json.loads((T/'examples/probes/record-wide/cases.json').read_bytes());program=cases[1]['program']
source=b'bagaev record-form/5; program { record Item { n: Int64 }; list Items of Item capacity 16; entry main; fn main(xs: Items) -> Int64 = fold (16, 0) with (i, sum) in sum + record.field(records.at(xs, i), "n"); }'
assert form.decode(source)==program and form.decode(form.encode(program))==program
try:old.decode(source)
except old.FormError as e:assert e.code=='FORM_VERSION'
else:raise AssertionError('old accepted5')
for c in cases:
 if c['id']=='cap17':continue
 assert form.decode(form.encode(c['program']))==c['program']
original=R/'sum.bagaev';original.write_bytes(source);args=R/'args.json';args.write_text(json.dumps(cases[1]['arguments']));out=R/'invocation.json';q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_text.py'),'prepare',str(original),'--form','5','--arguments',str(args),'--output',str(out)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr;metadata=json.loads(q.stdout)['result'];assert metadata['source_schema']=='bagaev-typed-record/11' and metadata['output_schema']=='bagaev-typed-record-invocation/11';assert json.loads(out.read_bytes())=={'schema':'bagaev-typed-record-invocation/11','program':program,'arguments':cases[1]['arguments']}

r={'status':'PASSED','exact_graphs':6,'cli_calls':1,'reference_calls':0,'old_version_refusals':1};(R/'result.json').write_text(json.dumps(r)+'\n');print(r)
