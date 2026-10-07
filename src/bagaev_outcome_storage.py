"""Isolated receiver execution followed by whole-image CAS, before response exposure."""
import copy,json
import bagaev_owner_image_store as storage
import bagaev_outcome_image as image_codec
from bagaev_component_outcome_owner import OutcomeOwner
class BridgeError(ValueError):
 def __init__(self,code):self.code=code;super().__init__(code)
class Bridge:
 def __init__(self,config,*,checker,evaluator,conditions):
  if type(config)is not dict or set(config)!={'policy','sources','origin','resource','clock_domain'}:raise BridgeError('BRIDGE_CONFIG')
  self._config=copy.deepcopy(config);self._pin=image_codec.pin(config)
  self.checker=checker;self.evaluator=evaluator;self.conditions=conditions
 def _settings(self):
  if image_codec.pin(self._config)!=self._pin:raise BridgeError('BRIDGE_CONFIG')
  return copy.deepcopy(self._config)
 def create(self,path):
  c=self._settings();owner=OutcomeOwner(policy=c['policy'],sources=c['sources'],state=c['origin']['state'],revision=c['origin']['revision'],resource=c['resource'],checker=self.checker,evaluator=self.evaluator,conditions=self.conditions)
  raw=image_codec.capture(owner,policy=c['policy'],origin=c['origin'],clock_domain=c['clock_domain'])
  return storage.create(path,raw)
 def call(self,path,command,packet):
  if type(command)is not str or command not in ('submit','observe','cancel'):raise BridgeError('BRIDGE_COMMAND')
  c=self._settings();before=storage.read(path)
  owner=image_codec.restore(before['image'],selected_digest=before['digest'],**c,checker=self.checker,evaluator=self.evaluator,conditions=self.conditions)
  result=getattr(owner,command)(packet)
  raw=image_codec.capture(owner,policy=c['policy'],origin=c['origin'],clock_domain=c['clock_domain'])
  old=json.loads(before['image']);new=json.loads(raw);old.pop('clock_floor');new.pop('clock_floor')
  if image_codec.pin(old)!=image_codec.pin(new):
   # No observable changed result before the complete state/ledger CAS commits.
   storage.compare_and_swap(path,before['generation'],before['digest'],raw)
  return copy.deepcopy(result)
