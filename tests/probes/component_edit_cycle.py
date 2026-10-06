"""Actual checked readable edit draft enters the existing simulated change path."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
P=Path(__file__).resolve().parents[2];D=P/'examples/probes/component-edit';sys.path.insert(0,str(P/'src'));import bagaev_component_edit as edit
import component_cycle as component
import component_change_cycle as cycle
def sha(v):return hashlib.sha256(v).hexdigest()
parser=argparse.ArgumentParser(description='Checked edit draft followed by separate source-bound simulated admission.')
parser.add_argument('--reader',required=True,type=Path);parser.add_argument('--reader-sha256',required=True);parser.add_argument('--output',required=True,type=Path);args,remaining=parser.parse_known_args();reader=args.reader;R=args.output
assert reader.is_absolute() and reader.is_file() and not reader.is_symlink();assert re.fullmatch('[0-9a-f]{64}',args.reader_sha256) and sha(reader.read_bytes())==args.reader_sha256
frozen=json.loads((D/'inputs.json').read_bytes())
for n,h in frozen['sha256'].items():assert sha((D/n).read_bytes())==h
assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir();sources=R/'sources';sources.mkdir();calls=[]
def checker(source,policy):
 n=len(calls)+1;s=R/f'{n}.source.json';p=R/f'{n}.policy.json';s.write_bytes(source);p.write_bytes(policy);v=subprocess.run([str(reader),'policy',str(s),str(p)],capture_output=True,timeout=10);(R/f'{n}.stdout').write_bytes(v.stdout);assert v.returncode==0 and not v.stderr and s.read_bytes()==source and p.read_bytes()==policy;calls.append({'source_sha256':sha(source),'output_sha256':sha(v.stdout)});return json.loads(v.stdout)
suite=json.loads((D/'cases.json').read_bytes());expected=json.loads((D/'connected-expectations.json').read_bytes());case=next(x for x in suite['cases'] if x['id']==expected['case']);result=edit.draft(case['original'],case['frame'],edit.canonical(suite['policy']),checker,candidate_map=case['candidate_map']);assert result==case['expected']
assert result['base']==expected['expected_base'] and result['target']==expected['expected_target'] and result['delta']==expected['expected_delta'] and result['execution_admission'] is False
(R/'draft.json').write_text(json.dumps({'draft':result,'data_checker_calls':calls},indent=2)+'\n');(sources/'S1.json').write_bytes(edit.canonical(edit.form.decode(case['original'])));(sources/'S2.json').write_bytes(edit.canonical(result['component']))
for name in ['policy.json','CONTRACT.json']:(sources/name).write_bytes((P/'examples/probes/component-source'/name).read_bytes())
(sources/'inputs.json').write_text(json.dumps({'sha256':{f.name:sha(f.read_bytes()) for f in sorted(sources.iterdir()) if f.is_file()}},indent=2)+'\n')
assert sha((P/'examples/probes/whole-cycle/cases.json').read_bytes())==expected['world_cases_sha256']
component.D=sources;sys.argv=[sys.argv[0],*remaining,'--reader',str(reader),'--reader-sha256',args.reader_sha256,'--output',str(R/'runtime')];cycle.main()
