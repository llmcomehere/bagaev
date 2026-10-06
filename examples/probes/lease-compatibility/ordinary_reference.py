"""Pure descriptive lease predicate; no clock read or authority/effect."""
MAX=2147483647

def integer(v, high=MAX):
    return type(v) is int and 0 <= v <= high

def lease(v):
    return (type(v) is dict and set(v)=={'clock','origin','expires','cap'}
            and integer(v['clock'],3)
            and all(integer(v[k]) for k in ('origin','expires','cap'))
            and v['origin'] < v['expires'] <= v['cap'])

def evaluate(parent,child,previous,time):
    for label,value in [('parent',parent),('child',child),('previous',previous)]:
        if label=='previous' and value is None: continue
        if not lease(value): return {'decision':'invalid','reason':label}
    if (type(time) is not dict or set(time)!={'clock','tick'}
        or not integer(time['clock'],3) or not integer(time['tick'])):
        return {'decision':'invalid','reason':'time'}
    clocks=[parent['clock'],child['clock'],time['clock']]
    if previous is not None:clocks.append(previous['clock'])
    if len(set(clocks))!=1:reason='clock-mismatch'
    elif previous is not None and child['origin']!=previous['origin']:reason='origin-changed'
    elif previous is not None and child['cap']!=previous['cap']:reason='cap-changed'
    elif previous is not None and child['expires']<previous['expires']:reason='expiry-shortened'
    elif previous is not None and time['tick']>=previous['expires']:reason='previous-ended'
    elif child['origin']<parent['origin'] or child['expires']>parent['expires'] or child['cap']>parent['cap']:reason='outside-parent'
    elif time['tick']<child['origin']:reason='not-started'
    elif time['tick']>=child['expires']:reason='ended'
    else:return {'decision':'compatible','reason':'initial' if previous is None else 'renewal'}
    return {'decision':'pending','reason':reason}
