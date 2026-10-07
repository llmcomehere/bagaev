"""Ordinary Python comparator for the same bounded queue task."""
import re

def ordinary(q,revision):
    bad={'kind':'refusal','reason':'invalid-request'}
    if type(q)is not dict or set(q)!={'jobs'} or type(q['jobs'])is not list or len(q['jobs'])>8:return bad
    seen=set()
    for j in q['jobs']:
        if type(j)is not dict or not {'id','urgent'}<=set(j)<= {'id','urgent','priority'}:return bad
        if type(j['id'])is not str or not re.fullmatch('[a-z][a-z0-9-]{0,7}',j['id']) or j['id'] in seen or type(j['urgent'])is not bool:return bad
        if 'priority' in j and (type(j['priority'])is not int or not 0<=j['priority']<=9):return bad
        seen.add(j['id'])
    def key(j):return (not j['urgent'], ('priority' not in j) if revision else False,j.get('priority',0),j['id'])
    return {'kind':'ok','order':[j['id'] for j in sorted(q['jobs'],key=key)]}
