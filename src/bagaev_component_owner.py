"""Owned-record/1 serial simulation. Host callbacks are trusted, never source data.
No durable storage, network, credentials, concurrency or authenticated authority.
"""
import copy,json,re
import bagaev_component_edit as edit
MAX=(1<<63)-1
class OwnerInputError(ValueError):
 def __init__(self,code):self.code=code;super().__init__(code)
class OwnerUnavailable(RuntimeError):pass
class OwnerEvaluationError(ValueError):
 def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
 if not ok:raise OwnerInputError(code)
def clone(v):return copy.deepcopy(v)
def integer(v):return type(v)is int and 0<=v<=MAX
def bounded(v):
 stack=[(v,1)];count=0
 while stack:
  x,d=stack.pop();count+=1;need(d<=128 and count<=10000,'OWNER_BOUNDS')
  if type(x)is dict:
   need(all(type(k)is str for k in x),'OWNER_SHAPE');stack.extend((y,d+1) for y in x.values())
  elif type(x)is list:stack.extend((y,d+1) for y in x)
  else:need(type(x) in (str,int,bool,type(None)),'OWNER_SHAPE');need(type(x)is not int or -(1<<63)<=x<=MAX,'OWNER_BOUNDS')
 try:raw=edit.canonical(v)
 except (ValueError,UnicodeError,RecursionError):raise OwnerInputError('OWNER_SHAPE') from None
 need(len(raw)<=1048576,'OWNER_BOUNDS');return raw
class Owner:
 def __init__(self,*,policy,sources,state,revision,resource,checker,evaluator,conditions):
  need(integer(revision),'OWNER_REVISION');need(type(resource)is str and re.fullmatch('[A-Za-z][A-Za-z0-9_./-]{0,127}',resource),'OWNER_RESOURCE')
  need(type(sources)is list and 1<=len(sources)<=16,'OWNER_SOURCES')
  if not callable(evaluator) or not callable(conditions):raise OwnerUnavailable('explicit host dependencies required')
  self._evaluate=evaluator;self._conditions=conditions;self.resource=resource;self._sources={};self._bindings={};self._tick=0;self._ledger={};self._mutations=0
  for source in sources:
   bounded(source)
   try:pin=edit.checked(source,bounded(policy),checker,'owner')
   except edit.CheckerUnavailable as e:raise OwnerUnavailable(str(e)) from None
   need(pin not in self._sources,'OWNER_SOURCES');self._sources[pin]=clone(source);self._bindings[pin]=clone(source['component'])
  self._state=clone(state);self._revision=revision
  # All sources are checked against one independently supplied state policy.
  for pin in self._sources:self._validate_value(pin,self._bindings[pin]['state_type'],state,'OWNER_STATE_TYPE')
 def snapshot(self):return {'state':clone(self._state),'revision':self._revision,'mutations':self._mutations,'terminal_rows':len(self._ledger)}
 def _guard(self):
  try:c=clone(self._conditions())
  except Exception as e:raise OwnerUnavailable('current conditions unavailable') from e
  if type(c)is not dict or set(c)!={'tick','epoch','submit','write','observe','cancel'} or not integer(c['tick']) or not integer(c['epoch']) or any(type(c[k])is not bool for k in ('submit','write','observe','cancel')) or c['tick']<self._tick:raise OwnerUnavailable('invalid current conditions')
  self._tick=c['tick'];return c
 def _packet(self,raw):
  need(type(raw)is bytes and len(raw)<=1048576,'OWNER_BOUNDS')
  try:p=json.loads(raw.decode('utf8'),object_pairs_hook=edit.pairs,parse_float=edit.no_float,parse_constant=edit.no_float)
  except (ValueError,UnicodeError,RecursionError):raise OwnerInputError('OWNER_SYNTAX') from None
  bounded(p);need(type(p)is dict and set(p)=={'key','source','request','epoch','deadline'},'OWNER_SHAPE')
  k=p['key'];need(type(k)is dict and set(k)=={'resource','domain','id'},'OWNER_SHAPE')
  for n in k:need(type(k[n])is str and re.fullmatch('[A-Za-z][A-Za-z0-9_./-]{0,127}',k[n]),'OWNER_SHAPE')
  need(k['resource']==self.resource,'OWNER_RESOURCE');need(type(p['source'])is str and p['source'] in self._sources,'OWNER_SOURCE');need(integer(p['epoch']) and integer(p['deadline']),'OWNER_SHAPE')
  return p,edit.canonical(k),{n:clone(p[n]) for n in ('source','request','epoch','deadline')}
 def _call(self,program,arguments,code):
  bounded(program);bounded(arguments)
  try:wire=self._evaluate(clone(program),clone(arguments))
  except Exception as e:raise OwnerUnavailable('typed evaluator unavailable') from e
  if type(wire)is not dict or set(wire)!={'schema','status','reason','location','value_type','value','work'} or wire['schema']!='bagaev-typed-record-result/10' or type(wire['work'])is not int or not 0<=wire['work']<=65536:raise OwnerUnavailable('invalid typed result frame')
  refusals={'invalid-ir','record-list-bound','list-bound','list-index','work-limit','integer-overflow'}
  if type(wire['status'])is str and wire['status'] in refusals:
   if type(wire['reason'])is not str or not wire['reason'].startswith('RR_') or type(wire['location'])is not str or wire['value'] is not None or wire['value_type'] is not None:raise OwnerUnavailable('invalid refusal frame')
   raise OwnerEvaluationError(code)
  if wire['status']!='success' or wire['reason'] is not None or wire['location'] is not None:raise OwnerUnavailable('invalid typed result status')
  bounded(wire['value']);return clone(wire)
 def _validate_value(self,pin,typename,value,code):
  core=self._sources[pin]['program'];validator={'schema':'bagaev-typed-record/10','records':clone(core['records']),'lists':{},'variants':{},'entry':'main','functions':{'main':{'params':[['value',typename]],'result':typename,'body':['arg','value']}}}
  result=self._call(validator,[value],code)
  if result['value_type']!='Record:'+typename or edit.canonical(result['value'])!=bounded(value):raise OwnerEvaluationError(code)
 def _request(self,p):
  m=self._bindings[p['source']];r=p['request']
  try:self._validate_value(p['source'],m['request_type'],r,'OWNER_REQUEST_TYPE')
  except OwnerEvaluationError:raise OwnerInputError('OWNER_REQUEST_TYPE') from None
  need(r[m['identity_binding']['request']]==self._state[m['identity_binding']['state']],'OWNER_IDENTITY')
  revision=r[m['revision_binding']]['value'];need(integer(revision),'OWNER_REVISION');return revision
 def _existing(self,key,intent,c,*,cancel=False):
  if not c['observe']:return {'status':'AccessDenied'}
  row=self._ledger[key]
  if edit.canonical(row['intent'])!=edit.canonical(intent):return {'status':'IntentConflict'}
  receipt=clone(row['receipt'])
  return {'kind':'AlreadyApplied','receipt':receipt} if cancel and receipt['kind']=='Applied' else receipt
 def _bind(self,key,intent,receipt,c):
  need(key not in self._ledger and len(self._ledger)<64,'OWNER_INTEGRITY');self._ledger[key]={'intent':clone(intent),'receipt':clone(receipt)}
  return clone(receipt) if c['observe'] else {'status':'OutcomeUnknown'}
 def _refusal(self,p,expected,c):
  if c['tick']>p['deadline']:return 'DeadlineExpired'
  if c['epoch']!=p['epoch']:return 'EpochMismatch'
  if self._revision!=expected:return 'RevisionMismatch'
  if self._revision==MAX:return 'RevisionExhausted'
  return None
 def _refuse(self,reason,key,intent,c):return self._bind(key,intent,{'kind':'Refused','reason':reason,'revision':self._revision},c)
 def submit(self,raw):
  p,key,intent=self._packet(raw);c=self._guard()
  if not c['submit']:return {'status':'AccessDenied'}
  if key in self._ledger:return self._existing(key,intent,c)
  if not c['write']:return {'status':'AccessDenied'}
  expected=self._request(p)
  c=self._guard()
  if not c['submit'] or not c['write']:return {'status':'AccessDenied'}
  if key in self._ledger:return self._existing(key,intent,c)
  if len(self._ledger)>=64:return {'status':'CapacityExceeded'}
  reason=self._refusal(p,expected,c)
  if reason:return self._refuse(reason,key,intent,c)
  old=clone(self._state);revision=self._revision;m=self._bindings[p['source']]
  wire=self._call(self._sources[p['source']]['program'],[old,p['request']],'OWNER_EVALUATION')
  if wire['value_type']!='Record:'+m['state_type']:raise OwnerEvaluationError('OWNER_RESULT_TYPE')
  value=wire['value'];self._validate_value(p['source'],m['state_type'],value,'OWNER_RESULT_TYPE')
  if any(edit.canonical(value[k])!=edit.canonical(old[k]) for k in old if k not in m['replace_fields']):raise OwnerEvaluationError('OWNER_FRAME')
  c=self._guard()
  if not c['submit'] or not c['write']:return {'status':'AccessDenied'}
  if key in self._ledger:return self._existing(key,intent,c)
  if len(self._ledger)>=64:return {'status':'CapacityExceeded'}
  reason=self._refusal(p,expected,c)
  if reason:return self._refuse(reason,key,intent,c)
  need(self._revision==revision and edit.canonical(self._state)==edit.canonical(old),'OWNER_INTEGRITY')
  # All deep copies/serialization/callbacks finish before the serial publication.
  receipt={'kind':'Applied','key':clone(p['key']),'intent':clone(intent),'revision':revision+1,'state':clone(value)}
  row={'intent':clone(intent),'receipt':clone(receipt)};answer=clone(receipt) if c['observe'] else {'status':'OutcomeUnknown'};next_state=clone(value)
  self._state=next_state;self._revision=revision+1;self._ledger[key]=row;self._mutations+=1
  return answer
 def observe(self,raw):
  p,key,intent=self._packet(raw);c=self._guard()
  if not c['observe']:return {'status':'AccessDenied'}
  return self._existing(key,intent,c) if key in self._ledger else {'status':'Unknown'}
 def cancel(self,raw):
  p,key,intent=self._packet(raw);c=self._guard()
  if not c['cancel']:return {'status':'AccessDenied'}
  if key in self._ledger:return self._existing(key,intent,c,cancel=True)
  self._request(p)
  if len(self._ledger)>=64:return {'status':'CapacityExceeded'}
  # Request checking is a host callback: recheck current conditions and ledger.
  c=self._guard()
  if not c['cancel']:return {'status':'AccessDenied'}
  if key in self._ledger:return self._existing(key,intent,c,cancel=True)
  if len(self._ledger)>=64:return {'status':'CapacityExceeded'}
  return self._bind(key,intent,{'kind':'Cancelled','key':clone(p['key']),'intent':clone(intent),'revision':self._revision},c)
