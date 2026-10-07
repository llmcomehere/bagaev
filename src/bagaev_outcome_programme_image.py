"""Bounded programme history codec. Historical shape is not authorization proof."""
import copy,json,re
import bagaev_owner_image_store as storage
import bagaev_outcome_image as image_codec

class ProgrammeError(ValueError):
 def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
 if not ok:raise ProgrammeError(code)
def ident(v):return type(v)is str and re.fullmatch('[A-Za-z][A-Za-z0-9_.-]{0,63}',v)is not None
def digest(v):return type(v)is str and re.fullmatch('[0-9a-f]{64}',v)is not None
def head(v):return type(v)is dict and set(v)=={'generation','source'} and type(v['generation'])is int and 0<=v['generation']<=64 and digest(v['source'])
def intent(v,*,policy,sources):
 need(type(v)is dict and set(v)=={'expected','target','policy','assertions','producer','qualification'},'PROGRAMME_INTENT')
 need(head(v['expected']) and all(digest(v[k]) for k in ('target','policy','assertions','producer','qualification')),'PROGRAMME_INTENT')
 need(v['target'] in sources and v['policy']==policy,'PROGRAMME_INTENT')
 return copy.deepcopy(v)
def validate(value,*,bootstrap,policy,sources):
 need(type(value)is dict and set(value)=={'schema','bootstrap','receiver','head','runs','admissions'} and value['schema']=='owned-programmes-image/1','PROGRAMME_SHAPE')
 need(digest(bootstrap) and bootstrap in sources and value['bootstrap']==bootstrap,'PROGRAMME_BOOTSTRAP')
 need(head(value['head']),'PROGRAMME_HEAD')
 history=value['admissions'];need(type(history)is list and len(history)<=64,'PROGRAMME_HISTORY')
 heads=[{'generation':0,'source':bootstrap}];ids=set()
 for row in history:
  need(type(row)is dict and set(row)=={'id','intent','receipt'} and ident(row['id']) and row['id'] not in ids,'PROGRAMME_HISTORY');ids.add(row['id'])
  proposal=intent(row['intent'],policy=policy,sources=sources)
  need(proposal['expected']==heads[-1],'PROGRAMME_HISTORY')
  next_head={'generation':len(heads),'source':proposal['target']}
  expected={'kind':'Admitted','head':next_head}
  # Canonical equality avoids True equalling generation 1.
  need(image_codec.pin(row['receipt'])==image_codec.pin(expected),'PROGRAMME_HISTORY');heads.append(next_head)
 need(value['head']==heads[-1],'PROGRAMME_HISTORY')
 runs=value['runs'];need(type(runs)is list and len(runs)<=64,'PROGRAMME_RUN');previous=None;run_sources=set()
 for row in runs:
  need(type(row)is dict and set(row)=={'id','head'} and ident(row['id']) and (previous is None or previous<row['id']) and head(row['head']),'PROGRAMME_RUN')
  previous=row['id'];h=row['head'];need(h['generation']<len(heads) and h==heads[h['generation']],'PROGRAMME_RUN');run_sources.add(h['source'])
 receiver=value['receiver'];need(type(receiver)is dict and type(receiver.get('terminal'))is list,'PROGRAMME_SHAPE')
 # Full receiver validation follows in restore; this association is additional.
 for row in receiver['terminal']:
  need(type(row)is dict and type(row.get('intent'))is dict and row['intent'].get('source') in run_sources,'PROGRAMME_TERMINAL_SOURCE')
 return copy.deepcopy(value)
def encode(value):
 raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode();storage.validate(raw);return raw
def restore(raw,*,selected_digest,bootstrap,config,checker,evaluator,conditions):
 storage.validate(raw);need(storage.digest(raw)==selected_digest,'PROGRAMME_PIN')
 value=validate(json.loads(raw),bootstrap=bootstrap,policy=image_codec.pin(config['policy']),sources={image_codec.pin(s) for s in config['sources']})
 receiver=encode(value['receiver'])
 owner=image_codec.restore(receiver,selected_digest=storage.digest(receiver),**config,checker=checker,evaluator=evaluator,conditions=conditions)
 return value,owner
