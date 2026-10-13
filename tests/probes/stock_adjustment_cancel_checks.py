"""Two selected commit sides, each using three strictly serial own processes."""
from pathlib import Path
import json,subprocess,sys
T=Path(__file__).resolve().parents[2];O=Path(__file__).parent
sys.path[:0]=[str(T/'src'),str(O)]
import bagaev_owner_image_store as storage
from outcome_host import configure
args=configure(reference=True);R=args.output;R.mkdir(exist_ok=False)
selection=R/'executables.json';selection.write_text(json.dumps({k:str(getattr(args,k)) for k in ('reader','reference','reader_sha256','reference_sha256')})+'\n')
selected=selection.read_bytes();results=[]
for point,cut,exit_code in [('before','stock_adjustment_rollback_child.py',88),('after','stock_adjustment_restart_child.py',87)]:
 folder=R/point;folder.mkdir();db=folder/'stock.sqlite';stages=[];snapshots={}
 sources={n:(O/n).read_bytes() for n in (cut,'stock_adjustment_cancel_child.py')}
 for stage in ('cut','cancel','verify'):
  command=[sys.executable,'-B',str(O/cut),'cut',str(db),str(selection),str(folder/stage)] if stage=='cut' else [sys.executable,'-B',str(O/'stock_adjustment_cancel_child.py'),point,stage,str(db),str(selection),str(folder/stage)]
  q=subprocess.run(command,capture_output=True,timeout=60)
  (folder/(stage+'.stdout')).write_bytes(q.stdout);(folder/(stage+'.stderr')).write_bytes(q.stderr)
  assert not q.stdout and not q.stderr and q.returncode==(exit_code if stage=='cut' else 0),(point,stage,q.returncode,q.stderr)
  assert selection.read_bytes()==selected and all((O/n).read_bytes()==raw for n,raw in sources.items())
  row=storage.read(db);snapshots[stage]=row;value=json.loads(row['image'])
  calls=json.loads((folder/stage/'native/calls.json').read_bytes())
  assert calls['application_evaluations']==(5 if stage=='cut' else 0)
  if stage=='cut':
   assert not (folder/stage/'result.json').exists()
   assert row['generation']==(4 if point=='before' else 5)
   assert value['revision']==(9 if point=='before' else 10) and value['state']['quantity']==(0 if point=='before' else 7) and value['mutations']==(2 if point=='before' else 3)
   if point=='before':assert row['image']==(folder/stage/'before-E.image').read_bytes()
   result={'point':point,'stage':stage,'exit':exit_code,'typed_calls':len(calls['calls']),'application_evaluations':5}
  else:
   result=json.loads((folder/stage/'result.json').read_bytes());assert result['status']=='PASSED'
   assert result['point']==point and result['stage']==stage and result['application_evaluations']==0 and result['typed_calls']==len(calls['calls'])
   assert result['initial_digest']==snapshots['cut' if stage=='cancel' else 'cancel']['digest']
   assert result['final_digest']==row['digest'] and row['generation']==5
  stages.append(result)
 assert snapshots['verify']==snapshots['cancel']
 if point=='after':assert snapshots['cancel']==snapshots['cut']
 results.append({'point':point,'stages':stages})
result={'status':'PASSED','cases':results,'serial_processes':6,'scope':'Cancellation binds an uncommitted intent but cannot undo committed stock. Selected own process exits only; no power-loss or external-effect guarantee.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
