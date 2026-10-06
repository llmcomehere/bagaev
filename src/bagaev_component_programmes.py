"""Serial host composition for an unchanged generic Owner; no production authority."""
import copy,re
import bagaev_component_edit as edit
import bagaev_component_admission as changes
class RunError(ValueError):
 def __init__(self,code):self.code=code;super().__init__(code)
class ProgrammeManager:
 def __init__(self,owner,*,initial,policy,checker,graph,binding,matcher,authority):
  if initial not in owner._sources:raise RunError('RUN_SOURCE')
  self.owner=owner;self.head=initial;self.runs={};self.policy=edit.canonical(policy);self.checker=checker;self.graph=copy.deepcopy(graph);self.binding=copy.deepcopy(binding);self.matcher=matcher;self.authority=authority
 def start(self,run_id):
  if type(run_id)is not str or re.fullmatch('[A-Za-z][A-Za-z0-9_.-]{0,63}',run_id)is None:raise RunError('RUN_ID')
  if run_id in self.runs:raise RunError('RUN_DUPLICATE')
  if len(self.runs)>=64:raise RunError('RUN_CAPACITY')
  self.runs[run_id]=self.head;return self.head
 def submit(self,run_id,packet):
  value,_,_=self.owner._packet(packet)
  if type(run_id)is not str or self.runs.get(run_id)!=value['source']:raise RunError('RUN_SOURCE')
  return self.owner.submit(packet)
 def observe(self,run_id,packet):
  value,_,_=self.owner._packet(packet)
  if type(run_id)is not str or self.runs.get(run_id)!=value['source']:raise RunError('RUN_SOURCE')
  return self.owner.observe(packet)
 def admit(self,candidate,*,expected_base,observations):
  def result(d,r):return {'decision':d,'reason':r}
  if expected_base!=self.graph['base_component_sha256']:return result('stale','base-changed')
  if edit.digest(candidate)!=self.graph['candidate_component_sha256']:return result('invalid','candidate-source')
  decision=changes.decide(self.graph,self.graph,self.binding,observations,self.matcher,self.head,self.authority())
  if decision['decision']!='accepted':return decision
  # Source check is a host callback; all live assumptions are checked after it.
  candidate=copy.deepcopy(candidate);pin=edit.checked(candidate,self.policy,self.checker,'admission')
  if pin!=self.graph['candidate_component_sha256']:return result('invalid','candidate-source')
  permission=self.authority()
  if self.head!=expected_base:return result('stale','base-changed')
  if permission is not True:return result('denied','admission-authority')
  if pin not in self.owner._sources and len(self.owner._sources)>=16:return result('denied','source-capacity')
  source=copy.deepcopy(candidate);bindings=copy.deepcopy(candidate['component'])
  # No callback or fallible serialization between these serial publication steps.
  # This is not a durable multi-assignment transaction or security boundary.
  self.owner._sources[pin]=source;self.owner._bindings[pin]=bindings;self.head=pin
  return result('accepted','all-obligations')

def restore_pending(manager,context_bytes,expectation_bytes,*,pending_sha256,component_checker):
 """Inspect pinned caller data; never restore owner state or host permissions."""
 import hashlib,json
 import bagaev_component_context as context
 inspection=context.inspect(context_bytes,expectation_bytes,component_checker=component_checker)
 if inspection['snapshot']!='sha256:'+manager.head:raise RunError('CONTINUATION_HEAD')
 # Parsing follows the strict bounded context parser above; no dynamic discovery.
 value=json.loads(context_bytes);sources={s['id']:s for s in value['sources']}
 if 'pending-operation' not in sources:raise RunError('CONTINUATION_SHAPE')
 try:data=json.loads(sources['pending-operation']['text'],object_pairs_hook=edit.pairs,parse_float=edit.no_float,parse_constant=edit.no_float)
 except (ValueError,UnicodeError,RecursionError):raise RunError('CONTINUATION_SHAPE') from None
 if type(data)is not dict or set(data)!={'schema','run_id','programme_source','programme_pin','packet'} or data['schema']!='owned-record-pending/1':raise RunError('CONTINUATION_SHAPE')
 if type(pending_sha256)is not str or re.fullmatch('[0-9a-f]{64}',pending_sha256)is None or hashlib.sha256(edit.canonical(data)).hexdigest()!=pending_sha256:raise RunError('CONTINUATION_PIN')
 if any(type(data[k])is not str for k in ('run_id','programme_source','programme_pin')):raise RunError('CONTINUATION_SHAPE')
 role=next((r for r in inspection['programme_sources'] if r['id']==data['programme_source']),None)
 pin=manager.runs.get(data['run_id'])
 if role is None or role['role']!='dependency' or pin is None or role['pin']!=data['programme_pin'] or data['programme_pin']!='sha256:'+pin:raise RunError('CONTINUATION_SOURCE')
 packet,_,_=manager.owner._packet(edit.canonical(data['packet']))
 if packet['source']!=pin:raise RunError('CONTINUATION_SOURCE')
 return {'run_id':data['run_id'],'packet':copy.deepcopy(packet),'inspection':inspection}
