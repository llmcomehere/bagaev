"""Private serial programme dispatcher over one receiver-owned atomic envelope."""
import copy,json
import bagaev_owner_image_store as storage
import bagaev_outcome_image as image_codec
import bagaev_outcome_programme_image as envelope
from bagaev_component_outcome_owner import OutcomeOwner
from bagaev_outcome_programme_image import ProgrammeError,need

class DurableProgrammes:
 def __init__(self,config,*,bootstrap,checker,evaluator,conditions,authority,qualifier):
  need(type(config)is dict and set(config)=={'policy','sources','origin','resource','clock_domain'},'PROGRAMME_CONFIG')
  self._config=copy.deepcopy(config);self._pin=image_codec.pin(config);self.bootstrap=bootstrap
  need(bootstrap in {image_codec.pin(s) for s in config['sources']},'PROGRAMME_BOOTSTRAP')
  self.checker=checker;self.evaluator=evaluator;self.conditions=conditions;self.authority=authority;self.qualifier=qualifier
 def _settings(self):
  need(image_codec.pin(self._config)==self._pin,'PROGRAMME_CONFIG');return copy.deepcopy(self._config)
 def _load(self,path):
  c=self._settings();before=storage.read(path)
  v,o=envelope.restore(before['image'],selected_digest=before['digest'],bootstrap=self.bootstrap,config=c,checker=self.checker,evaluator=self.evaluator,conditions=self.conditions)
  return c,before,v,o
 def create(self,path):
  c=self._settings();o=OutcomeOwner(policy=c['policy'],sources=c['sources'],state=c['origin']['state'],revision=c['origin']['revision'],resource=c['resource'],checker=self.checker,evaluator=self.evaluator,conditions=self.conditions)
  raw=image_codec.capture(o,policy=c['policy'],origin=c['origin'],clock_domain=c['clock_domain'])
  v={'schema':'owned-programmes-image/1','bootstrap':self.bootstrap,'receiver':json.loads(raw),'head':{'generation':0,'source':self.bootstrap},'runs':[],'admissions':[]}
  need(self.authority() is True,'PROGRAMME_AUTHORITY');return storage.create(path,envelope.encode(v))
 def start(self,path,run_id):
  need(envelope.ident(run_id),'PROGRAMME_RUN_ID');c,before,v,o=self._load(path)
  need(all(r['id']!=run_id for r in v['runs']),'PROGRAMME_RUN_DUPLICATE');need(len(v['runs'])<64,'PROGRAMME_RUN_CAPACITY')
  result=copy.deepcopy(v['head']);v['runs'].append({'id':run_id,'head':result});v['runs'].sort(key=lambda r:r['id']);raw=envelope.encode(v)
  need(self.authority() is True,'PROGRAMME_AUTHORITY')
  storage.compare_and_swap(path,before['generation'],before['digest'],raw);return copy.deepcopy(result)
 def admit(self,path,operation_id,proposal):
  need(envelope.ident(operation_id),'PROGRAMME_ADMISSION_ID');c,before,v,o=self._load(path)
  p=envelope.intent(proposal,policy=image_codec.pin(c['policy']),sources={image_codec.pin(s) for s in c['sources']})
  old=next((r for r in v['admissions'] if r['id']==operation_id),None)
  if old is not None:
   need(image_codec.pin(old['intent'])==image_codec.pin(p),'PROGRAMME_INTENT_CONFLICT');return copy.deepcopy(old['receipt'])
  need(p['expected']==v['head'],'PROGRAMME_STALE_HEAD');need(len(v['admissions'])<64,'PROGRAMME_ADMISSION_CAPACITY')
  source=next(copy.deepcopy(s) for s in c['sources'] if image_codec.pin(s)==p['target'])
  binding={k:p[k] for k in ('target','policy','assertions','producer','qualification')}
  qualified=self.qualifier(copy.deepcopy(p),copy.deepcopy(source))
  need(type(qualified)is dict and image_codec.pin(qualified)==image_codec.pin({'decision':'accepted','binding':binding}),'PROGRAMME_QUALIFICATION')
  # Check source again after qualification. The fixed trusted callback cannot be
  # selected by caller bytes; its result and source metadata use the owner checker.
  OutcomeOwner(policy=c['policy'],sources=[source],state=o._state,revision=o._revision,resource=c['resource'],checker=self.checker,evaluator=self.evaluator,conditions=self.conditions)
  new_head={'generation':v['head']['generation']+1,'source':p['target']};receipt={'kind':'Admitted','head':new_head}
  v['head']=new_head;v['admissions'].append({'id':operation_id,'intent':p,'receipt':receipt});raw=envelope.encode(v)
  need(self.authority() is True,'PROGRAMME_AUTHORITY')
  # This final CAS rechecks the whole image after every callback, including a
  # nested head change or application Decline with unchanged H and R.
  storage.compare_and_swap(path,before['generation'],before['digest'],raw);return copy.deepcopy(receipt)
 def call(self,path,run_id,command,packet):
  need(type(command)is str and command in ('submit','observe','cancel'),'PROGRAMME_COMMAND')
  c,before,v,o=self._load(path);value,_,_=o._packet(packet)
  run=next((r for r in v['runs'] if r['id']==run_id),None)
  need(envelope.ident(run_id) and run is not None and run['head']['source']==value['source'],'PROGRAMME_RUN_SOURCE')
  result=getattr(o,command)(packet)
  receiver=json.loads(image_codec.capture(o,policy=c['policy'],origin=c['origin'],clock_domain=c['clock_domain']))
  old=copy.deepcopy(v['receiver']);new=copy.deepcopy(receiver);old.pop('clock_floor');new.pop('clock_floor')
  if image_codec.pin(old)!=image_codec.pin(new):
   v['receiver']=receiver;raw=envelope.encode(v);storage.compare_and_swap(path,before['generation'],before['digest'],raw)
  return copy.deepcopy(result)
