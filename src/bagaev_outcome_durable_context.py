"""Checked caller data, never owner backup activation or persisted permissions."""
import copy,hashlib,json
import bagaev_component_outcome_context as context2
import bagaev_component_edit as edit
import bagaev_owner_image_store as storage
import bagaev_outcome_programme_image as envelope
from bagaev_outcome_programme_image import need

def inspect_pending(manager,path,context_bytes,expectation_bytes,*,pending_sha256,expected_head,component_checker):
 inspection=context2.inspect(context_bytes,expectation_bytes,component_checker=component_checker)
 # The context parser already bounded and checked these source texts and their
 # independent identities. Pending-object shape and identity are additional.
 value=json.loads(context_bytes);sources={s['id']:s for s in value['sources']}
 need('pending-operation' in sources,'CONTINUATION_SHAPE')
 try:data=json.loads(sources['pending-operation']['text'],object_pairs_hook=edit.pairs,parse_float=edit.no_float,parse_constant=edit.no_float)
 except (ValueError,UnicodeError,RecursionError):raise envelope.ProgrammeError('CONTINUATION_SHAPE') from None
 need(type(data)is dict and set(data)=={'schema','run_id','programme_source','programme_pin','packet'} and data['schema']=='owned-outcome-pending/2','CONTINUATION_SHAPE')
 need(envelope.digest(pending_sha256) and hashlib.sha256(edit.canonical(data)).hexdigest()==pending_sha256,'CONTINUATION_PIN')
 need(all(type(data[k])is str for k in ('run_id','programme_source','programme_pin')),'CONTINUATION_SHAPE')
 config,before,owned,owner=manager._load(path)
 need(envelope.head(expected_head) and owned['head']==expected_head and inspection['snapshot']=='sha256:'+expected_head['source'],'CONTINUATION_HEAD')
 role=next((r for r in inspection['programme_sources'] if r['id']==data['programme_source']),None)
 run=next((r for r in owned['runs'] if r['id']==data['run_id']),None)
 need(role is not None and role['role']=='dependency' and run is not None and role['pin']==data['programme_pin'] and data['programme_pin']=='sha256:'+run['head']['source'],'CONTINUATION_SOURCE')
 packet,_,_=owner._packet(edit.canonical(data['packet']))
 need(packet['source']==run['head']['source'],'CONTINUATION_SOURCE')
 after=storage.read(path)
 need(after['generation']==before['generation'] and after['digest']==before['digest'],'CONTINUATION_STALE_IMAGE')
 return {'run_id':data['run_id'],'packet':copy.deepcopy(packet),'inspection':inspection}
