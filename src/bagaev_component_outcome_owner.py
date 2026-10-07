"""Explicit /2 typed application outcome model; unchanged /1 stays separate."""
import copy
import bagaev_component_owner as base
import bagaev_component_edit as edit
class OutcomeOwner(base.Owner):
 def __init__(self,*,policy,sources,state,revision,resource,checker,evaluator,conditions):
  base.need(type(policy)is dict and policy.get('schema')=='bagaev-component-policy/2','OWNER_POLICY_VERSION')
  base.need(type(sources)is list and all(type(s)is dict and s.get('schema')=='bagaev-component-source/2' for s in sources),'OWNER_SOURCE_VERSION')
  def checked(source,pol):
   if not callable(checker):raise edit.CheckerUnavailable('outcome checker required')
   wire=checker(source,pol)
   if type(wire)is not dict or wire.get('schema')!='bagaev-component-check/2':raise edit.CheckerUnavailable('wrong outcome checker profile')
   return wire
  super().__init__(policy=policy,sources=sources,state=state,revision=revision,resource=resource,checker=checked,evaluator=evaluator,conditions=conditions)
 def _validate_value(self,pin,typename,value,code):
  core=self._sources[pin]['program'];validator={'schema':'bagaev-typed-record/10','records':copy.deepcopy(core['records']),'lists':{},'variants':copy.deepcopy(core['variants']),'entry':'main','functions':{'main':{'params':[['value',typename]],'result':typename,'body':['arg','value']}}}
  result=self._call(validator,[value],code);kind='Variant:' if typename in core['variants'] else 'Record:'
  if result['value_type']!=kind+typename or edit.canonical(result['value'])!=base.bounded(value):raise base.OwnerEvaluationError(code)
 def submit(self,raw):
  p,key,intent=self._packet(raw);c=self._guard()
  if not c['submit']:return {'status':'AccessDenied'}
  if key in self._ledger:return self._existing(key,intent,c)
  if not c['write']:return {'status':'AccessDenied'}
  expected=self._request(p);c=self._guard()
  if not c['submit'] or not c['write']:return {'status':'AccessDenied'}
  if key in self._ledger:return self._existing(key,intent,c)
  if len(self._ledger)>=64:return {'status':'CapacityExceeded'}
  reason=self._refusal(p,expected,c)
  if reason:return self._refuse(reason,key,intent,c)
  old=copy.deepcopy(self._state);revision=self._revision;m=self._bindings[p['source']]
  wire=self._call(self._sources[p['source']]['program'],[old,p['request']],'OWNER_EVALUATION')
  if wire['value_type']!='Variant:'+m['outcome_type']:raise base.OwnerEvaluationError('OWNER_RESULT_TYPE')
  outcome=wire['value'];self._validate_value(p['source'],m['outcome_type'],outcome,'OWNER_RESULT_TYPE')
  # The actual checked variant fixes both tags and payload types.
  if outcome['case']=='Propose':
   value=outcome['value']
   if any(edit.canonical(value[k])!=edit.canonical(old[k]) for k in old if k not in m['replace_fields']):raise base.OwnerEvaluationError('OWNER_FRAME')
  elif outcome['case']!='Decline':raise base.OwnerEvaluationError('OWNER_RESULT_TYPE')
  c=self._guard()
  if not c['submit'] or not c['write']:return {'status':'AccessDenied'}
  if key in self._ledger:return self._existing(key,intent,c)
  if len(self._ledger)>=64:return {'status':'CapacityExceeded'}
  reason=self._refusal(p,expected,c)
  if reason:return self._refuse(reason,key,intent,c)
  base.need(self._revision==revision and edit.canonical(self._state)==edit.canonical(old),'OWNER_INTEGRITY')
  if outcome['case']=='Decline':
   return self._bind(key,intent,{'kind':'Declined','key':copy.deepcopy(p['key']),'intent':copy.deepcopy(intent),'revision':revision,'error':copy.deepcopy(outcome['value'])},c)
  receipt={'kind':'Applied','key':copy.deepcopy(p['key']),'intent':copy.deepcopy(intent),'revision':revision+1,'state':copy.deepcopy(value)}
  row={'intent':copy.deepcopy(intent),'receipt':copy.deepcopy(receipt)};answer=copy.deepcopy(receipt) if c['observe'] else {'status':'OutcomeUnknown'};next_state=copy.deepcopy(value)
  self._state=next_state;self._revision=revision+1;self._ledger[key]=row;self._mutations+=1
  return answer
