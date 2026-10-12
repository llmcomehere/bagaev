"""Verify that a completed provisional evaluation is not a committed receipt."""
from pathlib import Path
import hashlib,json,subprocess,sys
T=Path(__file__).resolve().parents[2];O=Path(__file__).parent
sys.path[:0]=[str(T/'src'),str(O)]
import bagaev_owner_image_store as storage
from outcome_host import configure
args=configure(reference=True);R=args.output;R.mkdir(exist_ok=False)
db=R/'stock.sqlite';selection=R/'executables.json'
selection.write_text(json.dumps({k:str(getattr(args,k)) for k in ('reader','reference','reader_sha256','reference_sha256')})+'\n')
selected_bytes=selection.read_bytes();child=O/'stock_adjustment_rollback_child.py';child_bytes=child.read_bytes();rows=[];snapshots={}
for stage in ('cut','retry','verify'):
 q=subprocess.run([sys.executable,'-B',str(child),stage,str(db),str(selection),str(R/stage)],capture_output=True,timeout=60)
 (R/(stage+'.stdout')).write_bytes(q.stdout);(R/(stage+'.stderr')).write_bytes(q.stderr)
 assert not q.stdout and not q.stderr and q.returncode==(88 if stage=='cut' else 0),(stage,q.returncode,q.stderr)
 assert selection.read_bytes()==selected_bytes and child.read_bytes()==child_bytes
 row=storage.read(db);image=json.loads(row['image']);snapshots[stage]=row
 calls=json.loads((R/stage/'native/calls.json').read_bytes())
 if stage=='cut':
  assert not (R/stage/'result.json').exists()
  assert row['image']==(R/stage/'before-E.image').read_bytes()
  assert row['generation']==4 and image['revision']==9 and image['state']['quantity']==0 and image['mutations']==2
  assert calls['application_evaluations']==5
  result={'stage':stage,'exit':88,'G':4,'R':9,'quantity':0,'mutations':2,'application_evaluations':5,'typed_calls':len(calls['calls'])}
 else:
  result=json.loads((R/stage/'result.json').read_bytes());assert result['status']=='PASSED'
  assert result['typed_calls']==len(calls['calls']) and result['application_evaluations']==calls['application_evaluations']==(1 if stage=='retry' else 0)
  assert result['initial_digest']==snapshots['cut' if stage=='retry' else 'retry']['digest']
  assert result['final_digest']==row['digest'] and row['generation']==5
 rows.append(result)
assert snapshots['verify']==snapshots['retry']
result={'status':'PASSED','stages':rows,'serial_processes':3,'application_evaluations':6,
 'child_sha256':hashlib.sha256(child_bytes).hexdigest(),
 'scope':'Selected process exit after UPDATE before COMMIT. Explicit retry can reevaluate pure application code; no exactly-once physical evaluation, external-effect safety or power-loss claim.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
