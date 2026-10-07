"""Read retained terminal facts; no live owner port or clock conversion is exposed."""
import copy
import bagaev_owner_image_store as storage
import bagaev_outcome_programme_image as envelope
import bagaev_outcome_image as image_codec
from bagaev_outcome_programme_image import need
from bagaev_outcome_management_observation import _allowed,ManagementUnavailable
def _no_live_conditions():raise ManagementUnavailable('live activation is outside retained view')
def observe_retained(path,config,*,bootstrap,run_id,packet,checker,evaluator,observer):
 need(envelope.ident(run_id),'VIEW_RUN_SOURCE')
 if not _allowed(observer):return {'status':'AccessDenied'}
 original=copy.deepcopy(config);before=storage.read(path)
 value,owner=envelope.restore(before['image'],selected_digest=before['digest'],bootstrap=bootstrap,config=original,checker=checker,evaluator=evaluator,conditions=_no_live_conditions)
 request,key,intent=owner._packet(packet)
 run=next((r for r in value['runs'] if r['id']==run_id),None)
 need(run is not None and run['head']['source']==request['source'],'VIEW_RUN_SOURCE')
 owner._request(request)  # Nominal request/identity validation, not a write guard.
 row=owner._ledger.get(key)
 if row is None:answer={'status':'Unknown'}
 elif image_codec.pin(row['intent'])!=image_codec.pin(intent):answer={'status':'IntentConflict'}
 else:answer=copy.deepcopy(row['receipt'])
 if not _allowed(observer):return {'status':'AccessDenied'}
 after=storage.read(path)
 need(after['generation']==before['generation'] and after['digest']==before['digest'],'VIEW_STALE_IMAGE')
 return answer
