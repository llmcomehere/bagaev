"""Reviewed test-only native callbacks; raw artifacts retained before commit cuts."""
from pathlib import Path
import hashlib,json,subprocess
import bagaev_component_edit as edit
HOST=None
def select(args):
 global HOST
 HOST={k:str(getattr(args,k)) for k in ('reader','reference','reader_sha256','reference_sha256')}
def explicit(value):
 global HOST
 assert type(value)is dict and set(value)=={'reader','reference','reader_sha256','reference_sha256'}
 HOST=dict(value)
sha=lambda b:hashlib.sha256(b).hexdigest()
class Native:
 def __init__(self,out):
  self.out=Path(out);self.out.mkdir(exist_ok=False);assert HOST is not None
  self.reader=Path(HOST['reader']);self.reference=Path(HOST['reference']);self.calls=[];self.apps=0;self.on_application=None
  assert sha(self.reader.read_bytes())==HOST['reader_sha256']
  assert sha(self.reference.read_bytes())==HOST['reference_sha256']
 def save(self):
  (self.out/'calls.json').write_text(json.dumps({'calls':self.calls,'application_evaluations':self.apps},indent=2)+'\n')
 def invoke(self,binary,args,inputs):
  n=len(self.calls)+1;paths=[]
  for name,data in inputs:
   p=self.out/f'{n:03d}.{name}';p.write_bytes(data);paths.append(p)
  q=subprocess.run([str(binary),*args,*map(str,paths)],capture_output=True,timeout=20)
  (self.out/f'{n:03d}.stdout').write_bytes(q.stdout);(self.out/f'{n:03d}.stderr').write_bytes(q.stderr)
  assert q.returncode==0 and not q.stderr and all(p.read_bytes()==d for p,(_,d) in zip(paths,inputs))
  self.calls.append({'binary':binary.name,'inputs':[sha(d) for _,d in inputs],'output':sha(q.stdout)});self.save();return json.loads(q.stdout)
 def checker(self,source,policy):return self.invoke(self.reader,['policy'],[('source.json',source),('policy.json',policy)])
 def evaluator(self,program,arguments):
  wire=self.invoke(self.reference,['run','--input'],[('invocation.json',edit.canonical({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':arguments}))])
  if program['functions'][program['entry']]['body'][0]!='arg':
   self.apps+=1;callback=self.on_application;self.on_application=None;self.save()
   if callback:callback()
  return wire
