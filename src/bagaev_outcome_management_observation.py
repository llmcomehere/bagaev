"""Separate read-only management observation under current host permission."""
import copy
import bagaev_owner_image_store as storage
import bagaev_outcome_programme_image as envelope
from bagaev_outcome_programme_image import need
class ManagementUnavailable(RuntimeError):pass
def _allowed(observer):
 if not callable(observer):raise ManagementUnavailable('explicit host observer required')
 try:return observer() is True
 except Exception as e:raise ManagementUnavailable('management observation unavailable') from e
def observe_management(manager,path,kind,identifier,*,observer):
 need(type(kind)is str and kind in ('run','admission') and envelope.ident(identifier),'MANAGEMENT_QUERY')
 if not _allowed(observer):return {'status':'AccessDenied'}
 config,before,value,owner=manager._load(path)
 if kind=='run':
  row=next((r for r in value['runs'] if r['id']==identifier),None)
  answer={'status':'Known','binding':copy.deepcopy(row)} if row is not None else {'status':'Unknown'}
 else:
  row=next((r for r in value['admissions'] if r['id']==identifier),None)
  answer={'status':'Known','receipt':copy.deepcopy(row['receipt'])} if row is not None else {'status':'Unknown'}
 if not _allowed(observer):return {'status':'AccessDenied'}
 after=storage.read(path)
 need(after['generation']==before['generation'] and after['digest']==before['digest'],'MANAGEMENT_STALE_IMAGE')
 return answer
