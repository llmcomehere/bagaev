"""Pure catalog-date-edit/1 comparison reference; no tag normalization or effects."""
import catalog_wide_reference as catalog


def evaluate(request):
    refuse=lambda reason:{'kind':'refusal','reason':reason}
    if not catalog._object(request,{'interface','state','entry_id','action'}):
        return refuse('invalid-request')
    if request['interface']!='catalog-date-edit/1' or not catalog._identifier(request['entry_id']):
        return refuse('invalid-request')
    action=request['action']
    if type(action) is not dict or type(action.get('kind')) is not str:
        return refuse('invalid-request')
    kind=action['kind']
    if kind not in ('keep','set','clear') or set(action)!=({'kind','day'} if kind=='set' else {'kind'}):
        return refuse('invalid-request')
    adapted={'interface':'catalog-application/3','behavior_revision':3,'state':request['state'],'reindex':None}
    if not catalog._shape(adapted):
        return refuse('invalid-request')
    entries=request['state']['entries']
    valid_day=lambda day:type(day) is int and 0<=day<=31
    if any('date' in entry and not valid_day(entry['date']) for entry in entries) or (kind=='set' and not valid_day(action['day'])):
        return refuse('invalid-date')
    ids=[entry['id'] for entry in entries]
    if len(set(ids))!=len(ids):return refuse('duplicate-entry-id')
    if ids!=sorted(ids):return refuse('entry-order')
    if any(set(entry['manual_tags']).intersection(entry['indexed_tags']) for entry in entries):
        return refuse('origin-collision')
    if request['entry_id'] not in ids:return refuse('entry-not-found')
    updated=[]
    for entry in entries:
        result={'id':entry['id'],'title':entry['title'],
                'manual_tags':list(entry['manual_tags']),'indexed_tags':list(entry['indexed_tags'])}
        if 'date' in entry:result['date']=entry['date']
        if entry['id']==request['entry_id']:
            if kind=='set':result['date']=action['day']
            elif kind=='clear':result.pop('date',None)
        updated.append(result)
    order=lambda entry:(0,entry['date'],entry['id']) if 'date' in entry else (1,0,entry['id'])
    return {'kind':'success','state':{'entries':updated},'entry_ids':[entry['id'] for entry in sorted(updated,key=order)]}
