"""Conditional profile11 work bounds for a small straight-line IR subset.

This pure analysis neither checks a complete program nor admits execution.
Its bounds apply only to separately checked expressions and valid arguments
within the supplied maxima. An excessive upper bound is not certain failure.
"""

class Unknown(ValueError):
    pass


def analyze(expression, arguments):
    """Return SUPPORTED with an upper bound, or UNKNOWN without one.

    Argument shapes: {'type': 'Int64'|'Bool'} or
    {'type': 'TextList', 'items': maximum_count, 'bytes': maximum_utf8_bytes}.
    Only the documented expression subset is supported; no evaluation occurs.
    """
    base = {'schema': 'bagaev-record-work-bound/1',
            'semantic_check': False, 'execution_admission': False,
            'requires_checked_program': True}
    count = 0

    def shape(s):
        if type(s) is not dict:
            raise Unknown('argument-shape')
        if s in ({'type': 'Int64'}, {'type': 'Bool'}):
            return (s['type'], 0, 0)
        if set(s) != {'type', 'items', 'bytes'} or s['type'] != 'TextList':
            raise Unknown('argument-shape')
        n, b = s['items'], s['bytes']
        if type(n) is not int or type(b) is not int or not 0 <= n <= 64 or not 0 <= b <= min(4096, 1024*n):
            raise Unknown('argument-bounds')
        return ('TextList', n, b)

    def visit(x, scope, depth):
        nonlocal count
        count += 1
        if count > 2048 or depth > 32:
            raise Unknown('analysis-bounds')
        if type(x) is not list or not x or type(x[0]) is not str:
            raise Unknown('expression-shape')
        op = x[0]
        if op in ('arg', 'use') and len(x) == 2 and type(x[1]) is str:
            env = args if op == 'arg' else scope
            if x[1] not in env:
                raise Unknown('reference')
            return 1, env[x[1]]
        if op == 'int' and len(x) == 2 and type(x[1]) is int and -(2**63) <= x[1] < 2**63:
            return 1, ('Int64', 0, 0)
        if op == 'bool' and len(x) == 2 and type(x[1]) is bool:
            return 1, ('Bool', 0, 0)
        if op == 'text' and len(x) == 2 and type(x[1]) is str:
            if len(x[1]) > 256:
                raise Unknown('text-bounds')
            b = len(x[1].encode('utf-8'))
            if b > 1024:
                raise Unknown('text-bounds')
            return 1+b, ('Text', 0, b)
        if op == 'let' and len(x) == 4 and type(x[1]) is str:
            cost, value = visit(x[2], scope, depth+1)
            nested = dict(scope)
            nested[x[1]] = value
            tail, result = visit(x[3], nested, depth+1)
            return 1+cost+tail, result
        if op == 'record' and 2 <= len(x) <= 10 and type(x[1]) is str:
            return 1+sum(visit(v, scope, depth+1)[0] for v in x[2:]), ('Record', 0, 0)
        if op in ('list.len', 'list.unique', 'list.increasing') and len(x) == 2:
            cost, value = visit(x[1], scope, depth+1)
            if value[0] != 'TextList':
                raise Unknown('operand-type')
            _, n, b = value
            if op == 'list.len':
                return 1+cost, ('Int64', 0, 0)
            if op == 'list.increasing':
                return 1+cost+n+2*b, ('Bool', 0, 0)
            return 1+cost+n*n+2*n*b, value
        if op in ('eq', 'lt', 'le') and len(x) == 3:
            a, av = visit(x[1], scope, depth+1)
            b, bv = visit(x[2], scope, depth+1)
            if av[0] != bv[0] or av[0] not in (('Int64', 'Bool') if op == 'eq' else ('Int64',)):
                raise Unknown('operand-type')
            return 1+a+b, ('Bool', 0, 0)
        if op == 'not' and len(x) == 2:
            cost, value = visit(x[1], scope, depth+1)
            if value[0] != 'Bool':
                raise Unknown('operand-type')
            return 1+cost, value
        raise Unknown('unsupported-expression')

    try:
        if type(arguments) is not dict or len(arguments) > 8 or any(type(k) is not str for k in arguments):
            raise Unknown('arguments-shape')
        args = {k: shape(v) for k, v in arguments.items()}
        work, _ = visit(expression, {}, 1)
        return dict(base, status='SUPPORTED', upper_work=work,
                    fits_work_budget=work <= 65536, work_limit=65536)
    except (Unknown, UnicodeError, RecursionError) as e:
        return dict(base, status='UNKNOWN', reason=str(e))
