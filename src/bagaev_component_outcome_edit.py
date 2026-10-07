"""Detached component drafts. No programme evaluation/admission; explicit host checker."""
import copy,hashlib,json,re
import bagaev_component_outcome_form as form
SOURCE_BYTES=1048576
FRAME_BYTES=2097152;FRAME_DEPTH=8;FRAME_VALUES=32
DIGEST=re.compile(r'[0-9a-f]{64}\Z',re.ASCII);ID=re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,63}\Z',re.ASCII)
class EditError(ValueError):
 def __init__(self,code):self.code=code;super().__init__(code)
class CheckerUnavailable(RuntimeError):pass
class ComponentRefused(ValueError):
 def __init__(self,stage,reason):self.stage=stage;self.reason=reason;super().__init__(reason)
def need(ok,code):
 if not ok:raise EditError(code)
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()
def pairs(rows):
 out={}
 for k,v in rows:
  if k in out:raise ValueError('duplicate key')
  out[k]=v
 return out
def no_float(_):raise ValueError('unsupported numeric token')
def frame(source):
 need(type(source) in (str,bytes),'EDIT_SYNTAX')
 try:raw=source.encode('utf8') if type(source)is str else source;text=raw.decode('utf8')
 except UnicodeError:raise EditError('EDIT_SYNTAX') from None
 need(len(raw)<=FRAME_BYTES,'EDIT_BOUNDS');need(not text.startswith('\ufeff'),'EDIT_SYNTAX')
 try:
  # Integers are unsupported in every admitted scalar position. A representative
  # retains their kind for shape refusal without unbounded decimal conversion.
  value=json.loads(text,object_pairs_hook=pairs,parse_float=no_float,parse_constant=no_float,parse_int=lambda _:0)
 except RecursionError:raise EditError('EDIT_BOUNDS') from None
 except (ValueError,UnicodeError):raise EditError('EDIT_SYNTAX') from None
 stack=[(value,1)];count=0
 while stack:
  v,depth=stack.pop();count+=1;need(depth<=FRAME_DEPTH and count<=FRAME_VALUES,'EDIT_BOUNDS')
  if type(v)is dict:stack.extend((x,depth+1) for x in v.values())
  elif type(v)is list:stack.extend((x,depth+1) for x in v)
 need(type(value)is dict and set(value)=={'schema','form','base','target','candidate_id','source'},'EDIT_SHAPE')
 for k in ['schema','form','base','target','source']:
  need(type(value[k])is str and not any(0xd800<=ord(c)<=0xdfff for c in value[k]),'EDIT_SHAPE')
 need(value['schema']=='component-edit/2' and value['form']=='component-form/2','EDIT_VERSION')
 need(DIGEST.fullmatch(value['base']) is not None and DIGEST.fullmatch(value['target']) is not None,'EDIT_SHAPE')
 cid=value['candidate_id'];need(cid is None or type(cid)is str and ID.fullmatch(cid) is not None,'EDIT_SHAPE')
 need(len(value['source'].encode('utf8'))<=SOURCE_BYTES,'EDIT_BOUNDS');return value
def checked(component,policy,checker,stage):
 if not callable(checker):raise CheckerUnavailable('component checker required')
 try:wire=checker(canonical(component),policy)
 except CheckerUnavailable:raise
 except Exception as e:raise CheckerUnavailable('component checker failed') from e
 if type(wire)is not dict or wire.get('schema')!='bagaev-component-check/2' or wire.get('execution_admission') is not False:raise CheckerUnavailable('invalid checker frame')
 status=wire.get('status')
 if type(status)is not str:raise CheckerUnavailable('invalid checker status')
 if status in ('refused','source-checked-policy-refused'):
  if type(wire.get('reason'))is not str:raise CheckerUnavailable('invalid checker refusal')
  raise ComponentRefused(stage,wire['reason'])
 if status!='checked' or wire.get('policy_compatible') is not True:raise CheckerUnavailable('incomplete component check')
 try:
  policy_value=json.loads(policy,object_pairs_hook=pairs,parse_float=no_float,parse_constant=no_float)
  expected={'source_sha256':digest(component),'program_sha256':digest(component['program']),'policy_sha256':digest(policy_value)}
 except (ValueError,TypeError,UnicodeError,RecursionError) as e:raise CheckerUnavailable('invalid checked policy') from e
 if any(type(wire.get(k))is not str or wire[k]!=v for k,v in expected.items()):raise CheckerUnavailable('checker substituted source or policy')
 return expected['source_sha256']
def draft(original,edit_frame,policy,checker,*,candidate_map=None):
 before=form.decode(original);base=checked(before,policy,checker,'base');request=frame(edit_frame);after=form.decode(request['source'])
 need(request['base']==base,'EDIT_BASE');target=digest(after)
 if request['candidate_id'] is not None:
  need(type(candidate_map)is dict and all(type(k)is str for k in candidate_map),'EDIT_CANDIDATE');selected=candidate_map.get(request['candidate_id'])
  need(type(selected)is dict and all(type(k)is str for k in selected) and set(selected)=={'kind','pin'},'EDIT_CANDIDATE')
  need(type(selected['kind'])is str and selected['kind']=='component-source' and type(selected['pin'])is str and selected['pin']==target,'EDIT_CANDIDATE')
 need(before['schema']==after['schema'] and before['component']==after['component'],'EDIT_SCOPE')
 bp,ap=before['program'],after['program'];need({k:v for k,v in bp.items() if k!='functions'}=={k:v for k,v in ap.items() if k!='functions'},'EDIT_SCOPE')
 old,new=bp['functions'],ap['functions'];need(set(old)<=set(new),'EDIT_SCOPE')
 for name in old:need(old[name]['params']==new[name]['params'] and old[name]['result']==new[name]['result'],'EDIT_SIGNATURE')
 delta={'add':sorted(set(new)-set(old)),'replace':sorted(n for n in old if old[n]!=new[n])};need(delta['add'] or delta['replace'],'EDIT_NO_CHANGE')
 checked_target=checked(after,policy,checker,'candidate');need(request['target']==checked_target==target,'EDIT_TARGET')
 return {'schema':'component-draft/2','status':'draft','base':base,'target':target,'component':copy.deepcopy(after),'delta':delta,'execution_admission':False}
