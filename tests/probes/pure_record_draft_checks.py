from pathlib import Path
import sys,json,hashlib,subprocess
from outcome_host import configure
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/pure-record-draft'
a=configure(reference=True);R=a.output;ref=a.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_form as form;import bagaev_record_draft as edit
s=json.loads((D/'cases.json').read_bytes());assert form.decode(s['base'])==s['base_program'];assert form.decode(s['helper'])==s['helper_program']
base=edit.digest(s['base_program']);target=edit.digest(s['helper_program']);v=edit.draft(s['base'],s['helper'],base_sha256=base,target_sha256=target)
assert v['delta']=={'add':['plus_one'],'replace':['calc']} and v['program']==s['helper_program'] and not v['semantic_check'] and not v['execution_admission']
v['program']['functions']['calc']['body']=['int',99];assert form.decode(s['helper'])==s['helper_program']
refusals=0
def refuse(candidate,code,b=base,t=None):
 global refusals
 if t is None:t=edit.digest(form.decode(candidate))
 try:edit.draft(s['base'],candidate,base_sha256=b,target_sha256=t)
 except edit.DraftError as e:assert e.code==code,(e.code,code)
 else:raise AssertionError(code)
 refusals+=1
for c in s['refusals']:refuse(c['candidate'],c['code'])
refuse(s['helper'],'DRAFT_BASE','0'*64);refuse(s['helper'],'DRAFT_TARGET',t='0'*64);refuse(s['helper'],'DRAFT_PIN',b='bad')
wrong=edit.draft(s['base'],s['wrong'],base_sha256=base,target_sha256=edit.digest(form.decode(s['wrong'])));assert wrong['delta']=={'add':[],'replace':['calc']}

for name,source,expected in [('base',s['base'],s['expected']),('helper',s['helper'],s['expected']),('wrong',s['wrong'],s['wrong_value'])]:
 f=R/(name+'.json');raw=json.dumps({'schema':'bagaev-typed-record-invocation/10','program':form.decode(source),'arguments':[s['argument']]}).encode();f.write_bytes(raw)
 q=subprocess.run([str(ref),'run','--input',str(f)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and f.read_bytes()==raw;v=json.loads(q.stdout);assert v['status']=='success' and v['value']==expected;(R/(name+'.stdout')).write_bytes(q.stdout)
assert s['wrong_value']!=s['expected']

original=R/'original.bagaev';candidate=R/'candidate.bagaev';original.write_text(s['base']);candidate.write_text(s['helper']);out=R/'draft.json'
def call(output,error=None,base_pin=base):
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_draft.py'),str(original),str(candidate),'--base',base_pin,'--target',target,'--output',str(output)],capture_output=True,timeout=20)
 assert not q.stderr and q.returncode==(2 if error else 0)
 if error:assert json.loads(q.stdout)['error']['code']==error
call(out);assert json.loads(out.read_bytes())['delta']=={'add':['plus_one'],'replace':['calc']}
saved=out.read_bytes();call(out,'RECORD_PATH');assert out.read_bytes()==saved
call(R/'stale.json','DRAFT_BASE','0'*64);assert not (R/'stale.json').exists()
assert original.read_text()==s['base'] and candidate.read_text()==s['helper']

r={'status':'PASSED','drafts':2,'cli_calls':3,'refusals':refusals,'native_invocations':3,'business_wrong_draft_detected':True};(R/'result.json').write_text(json.dumps(r)+'\n');print(r)
