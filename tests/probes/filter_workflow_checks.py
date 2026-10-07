"""Own fixed complete CLI path; every call is a fresh bounded subprocess."""
from pathlib import Path
import argparse,json,subprocess,sys,hashlib
T=Path(__file__).resolve().parents[2];D=T/'examples/l2-filter/store'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists()
sys.path.insert(0,str(T))
from src import bagaev_filter_store as S
f=json.loads((D/'manifest.json').read_bytes());assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==h for n,h in f['sha256'].items());assert hashlib.sha256((T/'examples/l2-filter/queue.json').read_bytes()).hexdigest()==f['original_queue_sha256']
R.mkdir(exist_ok=False);rows=[];policy=json.loads((D/'policy.json').read_bytes());expected=json.loads((D/'expectations.json').read_bytes());path=R/'store'
def cli(args,error=None,module='src.bagaev_filter_workflow'):
 q=subprocess.run([sys.executable,'-B','-S','-m',module,*map(str,args)],cwd=T,capture_output=True,timeout=30);i=len(rows);(R/f'{i:02}.stdout').write_bytes(q.stdout);(R/f'{i:02}.stderr').write_bytes(q.stderr);assert q.returncode==(2 if error else 0) and not q.stderr,(args,q.returncode,q.stdout,q.stderr);v=json.loads(q.stdout);assert v['ok'] is (error is None)
 if module=='src.bagaev_filter_workflow':assert v['schema']=='bagaev-filter-workflow/1'
 if error:assert v['error']['code']==error,(v,error)
 rows.append({'args':list(map(str,args)),'module':module,'expected_error':error});return v.get('result')
def continuation(name,target,base,changes,evidence,intent='Preserve open queue'):
 v={'schema':S.CONTINUATION,'task':'open-queue','intent':intent,'base':base,'target':target,'changes':changes,'contract':S.digest(policy['contract']),'required':sorted(c['id'] for c in policy['contract']['cases']),'evidence':evidence,'unresolved':[],'effects':[],'hypotheses':[]};p=R/(name+'.json');p.write_bytes(S.canonical(v));return cli(['store','put',path,'continuation',p])['object']
cli(['store','init',path,'--policy',D/'policy.json']);a=cli(['store','put',path,'source',T/'examples/l2-filter/queue.json'])['object'];b=cli(['store','put',path,'source',D/'queue-refactor.json'])['object'];change=cli(['store','put',path,'change',D/'queue-refactor.patch'])['object'];assert a==expected['first_head']['source'] and b==expected['second_head']['source']
missing=continuation('missing',a,expected['initial_head'],[],[]);cli(['store','admit',path,'missing',missing],'STORE_CHECK');assert cli(['store','inspect',path])['head']==expected['initial_head']
e0=cli(['store','check',path,a])['evidence'];assert len(e0)==31;record=cli(['store','inspect',path,'--object',e0[0]]);assert record['kind']=='evidence' and record['value']['result']['status']=='passed'
c0=continuation('first',a,expected['initial_head'],[],e0);r0=cli(['store','admit',path,'first',c0]);assert r0['head']==expected['first_head']
e1=cli(['store','check',path,b])['evidence'];assert len(e1)==31;c1=continuation('second',b,expected['first_head'],[change],e1);stale=continuation('stale',b,expected['first_head'],[change],e1,'Stale alternative');r1=cli(['store','admit',path,'second',c1]);assert r1['head']==expected['second_head'];cli(['store','admit',path,'stale',stale],'STORE_STALE');cli(['store','admit',path,'second',stale],'STORE_OPERATION');assert cli(['store','admit',path,'first',c0])==r0;assert cli(['store','inspect',path])['head']==expected['second_head']
backup=R/'backup.json';exported=cli(['store','export',path,'--output',backup]);saved=backup.read_bytes();cli(['store','export',path,'--output',backup],'STORE_PATH');assert backup.read_bytes()==saved
cli(['store','import',R/'imported','--policy',D/'policy.json','--package',backup]);view=cli(['store','inspect',R/'imported','--operation','first']);assert view['status']=='absent' and view['head']==expected['initial_head']
cli(['store','restore',R/'restored','--policy',D/'policy.json','--package',backup,'--snapshot',exported['snapshot']]);view=cli(['store','inspect',R/'restored','--operation','second']);assert view['receipt']==r1 and view['head']==expected['second_head'];roundtrip=R/'restored-backup.json';cli(['store','export',R/'restored','--output',roundtrip]);assert roundtrip.read_bytes()==saved
cli(['store','inspect',path],'STORE_FORMAT',module='src.bagaev');cli(['store','inspect',path],'TOOL_USAGE',module='src.bagaev_filter')
final=cli(['store','inspect',path]);assert final['snapshot']==exported['snapshot']
result={'status':'PASSED','cli_calls':len(rows),'intentional_refusals':sum(r['expected_error']is not None for r in rows),'policy_cases':31,'head':final['head'],'old_receipt_is_not_current_head':True,'import_inactive':True,'restore_exact':True,'rows':rows};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
