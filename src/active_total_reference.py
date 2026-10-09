"""Ordinary bounded application baseline, not a language evaluator or work model."""
MIN_INT64=-(2**63)
MAX_INT64=2**63-1

def total(items,*,active_only):
    """Validate all input, then checked-add selected amounts in input order."""
    if type(active_only) is not bool or type(items) is not list or len(items)>16:
        raise ValueError('invalid-input')
    for item in items:
        if (type(item) is not dict or set(item)!={'amount','active'} or
            type(item['amount']) is not int or not MIN_INT64<=item['amount']<=MAX_INT64 or
            type(item['active']) is not bool):
            raise ValueError('invalid-input')
    value=0
    for index,item in enumerate(items):
        if active_only and not item['active']:
            continue
        candidate=value+item['amount']
        if not MIN_INT64<=candidate<=MAX_INT64:
            return {'status':'integer-overflow','value':None,'failure_index':index}
        value=candidate
    return {'status':'success','value':value,'failure_index':None}
