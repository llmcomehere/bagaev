"""Pure observation of selected argument dimensions; never program or execution admission."""
import hashlib
import json
from bagaev_record_work import analyze


def observe(bounds, arguments):
    """Compare actual supported values with declarations, without running a program."""
    base={'schema':'bagaev-record-argument-dimensions/1',
          'semantic_check':False,'execution_admission':False,'requires_checked_program':True}
    def stop(status,reason,name=None):
        return dict(base,status=status,reason=reason,argument=name,within_declared_bounds=None)
    if (type(bounds) is not dict or type(arguments) is not dict or
        len(bounds)>8 or set(bounds)!=set(arguments) or
        any(type(n) is not str for n in bounds)):
        return stop('UNKNOWN','argument-map')
    for name in sorted(bounds):
        shape=bounds[name]
        if type(shape) is not dict or shape.get('type') not in ('Int64','Bool','Text','TextList'):
            return stop('UNKNOWN','argument-shape',name)
        if analyze(['arg',name],{name:shape})['status']!='SUPPORTED':
            return stop('UNKNOWN','argument-shape',name)
    def text_size(value):
        if type(value) is not str or len(value)>256:
            raise ValueError('text-value')
        try:count=len(value.encode('utf-8'))
        except UnicodeError:raise ValueError('text-value') from None
        if count>1024:raise ValueError('text-value')
        return count
    rows=[];within=True
    for name in sorted(bounds):
        shape=bounds[name];value=arguments[name];kind=shape['type']
        row={'name':name,'type':kind}
        try:
            if kind=='Int64':
                if type(value) is not int or not -(2**63)<=value<2**63:raise ValueError('integer-value')
                fits=True
            elif kind=='Bool':
                if type(value) is not bool:raise ValueError('boolean-value')
                fits=True
            elif kind=='Text':
                row.update(bytes=text_size(value),scalars=len(value));fits=row['bytes']<=shape['bytes']
            else:
                if type(value) is not list or len(value)>64:raise ValueError('list-value')
                total=sum(text_size(x) for x in value)
                if total>4096:raise ValueError('list-value')
                row.update(items=len(value),bytes=total)
                fits=len(value)<=shape['items'] and total<=shape['bytes']
        except ValueError as e:
            return stop('INVALID_ARGUMENT',str(e),name)
        row['within_declared_bounds']=fits;within=within and fits;rows.append(row)
    def pin(value):
        raw=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
        return hashlib.sha256(raw).hexdigest()
    try:
        bp,ap=pin(bounds),pin(arguments)
    except (ValueError,TypeError,UnicodeError,RecursionError):
        return stop('UNKNOWN','argument-identity')
    return dict(base,status='WITHIN' if within else 'EXCEEDS',within_declared_bounds=within,
                argument_bounds_sha256=bp,arguments_sha256=ap,dimensions=rows)
