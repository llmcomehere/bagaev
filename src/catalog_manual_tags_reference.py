"""Pure catalog-manual-tags/1; canonicalize only selected replacement tags."""
import catalog_wide_reference as catalog
def evaluate(request):
    refuse=lambda reason:{'kind':'refusal','reason':reason}
    if not catalog._object(request,{'interface','state','entry_id','tags'}):return refuse('invalid-request')
    if request['interface']!='catalog-manual-tags/1' or not catalog._identifier(request['entry_id']) or not catalog._tags(request['tags']):
        return refuse('invalid-request')
    adapted={'interface':'catalog-application/3','behavior_revision':3,'state':request['state'],'reindex':None}
    if not catalog._shape(adapted):return refuse('invalid-request')
    entries=request['state']['entries']
    if any('date' in e and (type(e['date']) is not int or not 0<=e['date']<=31) for e in entries):return refuse('invalid-date')
    ids=[e['id'] for e in entries]
    if len(set(ids))!=len(ids):return refuse('duplicate-entry-id')
    if ids!=sorted(ids):return refuse('entry-order')
    if any(set(e['manual_tags']).intersection(e['indexed_tags']) for e in entries):return refuse('origin-collision')
    if request['entry_id'] not in ids:return refuse('entry-not-found')
    selected=entries[ids.index(request['entry_id'])]
    if set(request['tags']).intersection(selected['indexed_tags']):return refuse('origin-collision')
    result=[]
    for e in entries:
        out={'id':e['id'],'title':e['title'],'indexed_tags':list(e['indexed_tags']),
             'manual_tags':sorted(set(request['tags'])) if e['id']==request['entry_id'] else list(e['manual_tags'])}
        if 'date' in e:out['date']=e['date']
        result.append(out)
    order=lambda e:(0,e['date'],e['id']) if 'date' in e else (1,0,e['id'])
    return {'kind':'success','state':{'entries':result},'entry_ids':[e['id'] for e in sorted(result,key=order)]}
