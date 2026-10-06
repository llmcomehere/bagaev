"""Complete literal checker wires; caller supplies reviewed binary and fresh output."""
import json, subprocess
import component_cycle as c
def main():
 c.verify_component_inputs();b=c.b;rows=[]
 suite=json.loads((c.D/'check-cases.json').read_text());policy=b.R/'policy.json';policy.write_bytes(b.encoded(suite['policy']))
 for case in suite['cases']:
  source=b.R/(case['id']+'.json');source.write_bytes(b.encoded(case['source']))
  args=[str(c.READER),'check' if case['stage']=='source' else 'policy',str(source)]
  if case['stage']=='policy':args.append(str(policy))
  q=subprocess.run(args,capture_output=True,timeout=10)
  (b.R/(case['id']+'.stdout')).write_bytes(q.stdout);(b.R/(case['id']+'.stderr')).write_bytes(q.stderr)
  b.need(q.returncode==0 and not q.stderr,'checker environment')
  actual=json.loads(q.stdout);rows.append({'id':case['id'],'matched':b.encoded(actual)==b.encoded(case['expected']),'actual':actual,'expected':case['expected']})
  b.need(source.read_bytes()==b.encoded(case['source']) and policy.read_bytes()==b.encoded(suite['policy']),'input mutation')
 result={'status':'PASSED' if all(x['matched'] for x in rows) else 'FAILED','rows':rows,'matched':sum(x['matched'] for x in rows),'requested':len(rows),'reader_sha256':c.READER_SHA,'scope':'Data-only source/policy check, no evaluation or admission'}
 (b.R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('status','matched','requested')}));b.need(result['status']=='PASSED','checker wire mismatch')
if __name__=='__main__':c.configure();main()
