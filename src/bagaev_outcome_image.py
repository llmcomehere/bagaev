"""Receiver-owned data reconstruction; no caller-context authority or executable import."""
import copy,hashlib,json,re
import bagaev_owner_image_store as storage
import bagaev_component_owner as base
import bagaev_component_edit as edit
from bagaev_component_outcome_owner import OutcomeOwner
FIELDS={'schema','resource','policy','sources','origin','clock_domain','clock_floor','state','revision','mutations','terminal'}
class ImageError(ValueError):
 def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
 if not ok:raise ImageError(code)
def pin(value):return hashlib.sha256(edit.canonical(value)).hexdigest()
def capture(owner,*,policy,origin,clock_domain,clock_floor=None):
 floor=owner._tick if clock_floor is None else clock_floor
 need(base.integer(floor) and type(clock_domain)is str and re.fullmatch('[A-Za-z][A-Za-z0-9_.-]{0,63}',clock_domain),'IMAGE_CLOCK')
 rows=[{'key':json.loads(key),'intent':copy.deepcopy(row['intent']),'receipt':copy.deepcopy(row['receipt'])} for key,row in sorted(owner._ledger.items())]
 value={'schema':'owned-outcome-image/1','resource':owner.resource,'policy':pin(policy),'sources':sorted(owner._sources),'origin':pin(origin),'clock_domain':clock_domain,'clock_floor':floor,'state':copy.deepcopy(owner._state),'revision':owner._revision,'mutations':owner._mutations,'terminal':rows}
 raw=edit.canonical(value);storage.validate(raw);return raw
def restore(raw,*,selected_digest,policy,sources,origin,resource,clock_domain,checker,evaluator,conditions):
 try:storage.validate(raw)
 except storage.StorageError:raise ImageError('IMAGE_BYTES') from None
 need(type(selected_digest)is str and selected_digest==hashlib.sha256(raw).hexdigest(),'IMAGE_PIN')
 value=json.loads(raw)
 need(set(value)==FIELDS and value['schema']=='owned-outcome-image/1','IMAGE_SHAPE')
 need(value['resource']==resource,'IMAGE_RESOURCE');need(value['policy']==pin(policy),'IMAGE_POLICY')
 need(value['sources']==sorted(pin(s) for s in sources),'IMAGE_SOURCES');need(value['origin']==pin(origin),'IMAGE_ORIGIN')
 need(type(clock_domain)is str and re.fullmatch('[A-Za-z][A-Za-z0-9_.-]{0,63}',clock_domain) and value['clock_domain']==clock_domain and base.integer(value['clock_floor']),'IMAGE_CLOCK')
 need(base.integer(value['revision']) and base.integer(origin['revision']) and value['revision']>=origin['revision'],'IMAGE_REVISION')
 need(type(value['mutations'])is int and 0<=value['mutations']<=64 and type(value['terminal'])is list and len(value['terminal'])<=64,'IMAGE_LEDGER')
 try:
  owner=OutcomeOwner(policy=policy,sources=sources,state=value['state'],revision=value['revision'],resource=resource,checker=checker,evaluator=evaluator,conditions=conditions)
  for source in owner._sources:owner._validate_value(source,owner._bindings[source]['state_type'],origin['state'],'OWNER_STATE_TYPE')
 except (base.OwnerInputError,base.OwnerEvaluationError):raise ImageError('IMAGE_VALUE') from None
 ledger={};applied={};previous=None
 for row in value['terminal']:
  need(type(row)is dict and set(row)=={'key','intent','receipt'} and type(row['intent'])is dict and set(row['intent'])=={'source','request','epoch','deadline'},'IMAGE_LEDGER')
  packet={'key':row['key'],**row['intent']}
  try:p,key,intent=owner._packet(edit.canonical(packet));requested=owner._request(p)
  except (base.OwnerInputError,base.OwnerEvaluationError):raise ImageError('IMAGE_REQUEST') from None
  need(previous is None or previous<key,'IMAGE_LEDGER');previous=key
  receipt=row['receipt'];need(type(receipt)is dict and type(receipt.get('kind'))is str,'IMAGE_RECEIPT');kind=receipt['kind']
  fields={'Applied':{'kind','key','intent','revision','state'},'Declined':{'kind','key','intent','revision','error'},'Cancelled':{'kind','key','intent','revision'},'Refused':{'kind','reason','revision'}}
  need(kind in fields and set(receipt)==fields[kind] and base.integer(receipt['revision']) and origin['revision']<=receipt['revision']<=value['revision'],'IMAGE_RECEIPT')
  r=receipt['revision'];m=owner._bindings[p['source']]
  if kind!='Refused':need(edit.canonical(receipt['key'])==edit.canonical(row['key']) and edit.canonical(receipt['intent'])==edit.canonical(intent),'IMAGE_RECEIPT')
  else:need(receipt['reason'] in ('DeadlineExpired','EpochMismatch','RevisionMismatch','RevisionExhausted'),'IMAGE_RECEIPT')
  try:
   if kind=='Applied':
    need(r>origin['revision'] and r not in applied and requested==r-1,'IMAGE_LEDGER')
    owner._validate_value(p['source'],m['state_type'],receipt['state'],'OWNER_STATE_TYPE')
    need(all(edit.canonical(receipt['state'][k])==edit.canonical(origin['state'][k]) for k in origin['state'] if k not in m['replace_fields']),'IMAGE_STATE')
    applied[r]=receipt['state']
   elif kind=='Declined':
    need(requested==r,'IMAGE_RECEIPT');owner._validate_value(p['source'],m['error_type'],receipt['error'],'OWNER_RESULT_TYPE')
  except (base.OwnerInputError,base.OwnerEvaluationError):raise ImageError('IMAGE_VALUE') from None
  ledger[key]={'intent':copy.deepcopy(intent),'receipt':copy.deepcopy(receipt)}
 count=len(applied)
 need(value['mutations']==count and value['revision']==origin['revision']+count and sorted(applied)==[origin['revision']+i+1 for i in range(count)],'IMAGE_LEDGER')
 expected=applied[value['revision']] if count else origin['state']
 need(edit.canonical(value['state'])==edit.canonical(expected),'IMAGE_STATE')
 owner._ledger=ledger;owner._mutations=count;owner._tick=value['clock_floor']
 return owner
