"""Conditional profile11 work bounds for a small pure IR subset.

This pure analysis neither checks a complete program nor admits execution.
Its bounds apply only to separately checked expressions and valid arguments
within the supplied maxima. An excessive upper bound is not certain failure.
"""

class Unknown(ValueError):
    pass


def analyze(expression, arguments, functions=None):
    """Return SUPPORTED with an upper bound, or UNKNOWN without one.

    Argument shapes: {'type': 'Int64'|'Bool'} or
    {'type': 'TextList', 'items': maximum_count, 'bytes': maximum_utf8_bytes}.
    Only the documented expression subset is supported; no evaluation occurs.
    Optional definitions permit bounded primitive-signature helper calls.
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

    def visit(x, scope, depth, arg_scope, stack):
        nonlocal count
        count += 1
        if count > 2048 or depth > 32:
            raise Unknown('analysis-bounds')
        if type(x) is not list or not x or type(x[0]) is not str:
            raise Unknown('expression-shape')
        op = x[0]
        if op in ('arg', 'use') and len(x) == 2 and type(x[1]) is str:
            env = arg_scope if op == 'arg' else scope
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
            cost, value = visit(x[2], scope, depth+1, arg_scope, stack)
            nested = dict(scope)
            nested[x[1]] = value
            tail, result = visit(x[3], nested, depth+1, arg_scope, stack)
            return 1+cost+tail, result
        if op == 'if' and len(x) == 4:
            condition, cv = visit(x[1], scope, depth+1, arg_scope, stack)
            yes, yv = visit(x[2], scope, depth+1, arg_scope, stack)
            no, nv = visit(x[3], scope, depth+1, arg_scope, stack)
            if cv[0] != 'Bool' or yv[0] != nv[0]:
                raise Unknown('operand-type')
            joined = (yv[0], max(yv[1], nv[1]), max(yv[2], nv[2]))
            return 1+condition+max(yes, no), joined
        if op == 'record' and 2 <= len(x) <= 10 and type(x[1]) is str:
            return 1+sum(visit(v, scope, depth+1, arg_scope, stack)[0] for v in x[2:]), ('Record', 0, 0)
        if op == 'call' and 2 <= len(x) <= 10 and type(x[1]) is str:
            name = x[1]
            if name in stack:
                raise Unknown('call-cycle')
            if name not in definitions:
                raise Unknown('call-reference')
            function = definitions[name]
            if type(function) is not dict or set(function) != {'params', 'result', 'body'}:
                raise Unknown('function-shape')
            params = function['params']
            primitive = ('Int64', 'Bool', 'Text', 'TextList')
            if type(params) is not list or len(params) > 8 or function['result'] not in primitive:
                raise Unknown('function-signature')
            if any(type(p) is not list or len(p) != 2 or type(p[0]) is not str or p[1] not in primitive for p in params):
                raise Unknown('function-signature')
            if len({p[0] for p in params}) != len(params) or len(x)-2 != len(params):
                raise Unknown('call-arity')
            cost = 1
            bindings = {}
            for actual, (parameter, kind) in zip(x[2:], params):
                charged, value = visit(actual, scope, depth+1, arg_scope, stack)
                if value[0] != kind:
                    raise Unknown('operand-type')
                cost += charged
                bindings[parameter] = value
            charged, result = visit(function['body'], {}, depth+1, bindings, stack+(name,))
            if result[0] != function['result']:
                raise Unknown('operand-type')
            return cost+charged, result
        if op in ('list.len', 'list.unique', 'list.increasing') and len(x) == 2:
            cost, value = visit(x[1], scope, depth+1, arg_scope, stack)
            if value[0] != 'TextList':
                raise Unknown('operand-type')
            _, n, b = value
            if op == 'list.len':
                return 1+cost, ('Int64', 0, 0)
            if op == 'list.increasing':
                return 1+cost+n+2*b, ('Bool', 0, 0)
            return 1+cost+n*n+2*n*b, value
        if op in ('eq', 'lt', 'le') and len(x) == 3:
            a, av = visit(x[1], scope, depth+1, arg_scope, stack)
            b, bv = visit(x[2], scope, depth+1, arg_scope, stack)
            if av[0] != bv[0] or av[0] not in (('Int64', 'Bool') if op == 'eq' else ('Int64',)):
                raise Unknown('operand-type')
            return 1+a+b, ('Bool', 0, 0)
        if op == 'not' and len(x) == 2:
            cost, value = visit(x[1], scope, depth+1, arg_scope, stack)
            if value[0] != 'Bool':
                raise Unknown('operand-type')
            return 1+cost, value
        raise Unknown('unsupported-expression')

    try:
        if type(arguments) is not dict or len(arguments) > 8 or any(type(k) is not str for k in arguments):
            raise Unknown('arguments-shape')
        args = {k: shape(v) for k, v in arguments.items()}
        definitions = {} if functions is None else functions
        if type(definitions) is not dict or len(definitions) > 32 or any(type(k) is not str for k in definitions):
            raise Unknown('functions-shape')
        work, _ = visit(expression, {}, 1, args, ())
        return dict(base, status='SUPPORTED', upper_work=work,
                    fits_work_budget=work <= 65536, work_limit=65536)
    except (Unknown, UnicodeError, RecursionError) as e:
        return dict(base, status='UNKNOWN', reason=str(e))
