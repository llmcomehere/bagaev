"""Conditional profile11 work bounds for a small pure IR subset.

This pure analysis neither checks a complete program nor admits execution.
Its bounds apply only to separately checked expressions and valid arguments
within the supplied maxima. An excessive upper bound is not certain failure.
"""

class Unknown(ValueError):
    pass


def analyze(expression, arguments, functions=None, records=None, lists=None):
    """Return SUPPORTED with an upper bound, or UNKNOWN without one.

    Argument shapes: {'type': 'Int64'|'Bool'} or
    {'type': 'TextList', 'items': maximum_count, 'bytes': maximum_utf8_bytes}.
    Only the documented expression subset is supported; no evaluation occurs.
    Optional definitions permit bounded helper calls with supported shapes.
    Nominal list bounds require scalar-only record/list declaration maps.
    """
    base = {'schema': 'bagaev-record-work-bound/1',
            'semantic_check': False, 'execution_admission': False,
            'requires_checked_program': True}
    count = 0

    def record_fields(name):
        fields = record_defs.get(name)
        if (type(fields) is not dict or not 1 <= len(fields) <= 8 or
            any(type(k) is not str or v not in ('Int64', 'Bool') for k, v in fields.items())):
            raise Unknown('record-shape')
        return fields

    def list_declaration(name):
        declared = list_defs.get(name)
        if (type(declared) is not dict or set(declared) != {'element', 'capacity'} or
            type(declared['element']) is not str or type(declared['capacity']) is not int or
            not 0 <= declared['capacity'] <= 16):
            raise Unknown('record-list-shape')
        record_fields(declared['element'])
        return declared

    def shape(s):
        if type(s) is not dict:
            raise Unknown('argument-shape')
        if s in ({'type': 'Int64'}, {'type': 'Bool'}):
            return (s['type'], 0, 0)
        if type(s.get('type')) is str and s['type'] in list_defs:
            declared = list_declaration(s['type'])
            if set(s) != {'type', 'items'} or type(s['items']) is not int or not 0 <= s['items'] <= declared['capacity']:
                raise Unknown('argument-bounds')
            return ('Records:' + s['type'], s['items'], 0)
        if set(s) != {'type', 'items', 'bytes'} or s['type'] != 'TextList':
            raise Unknown('argument-shape')
        n, b = s['items'], s['bytes']
        if type(n) is not int or type(b) is not int or not 0 <= n <= 64 or not 0 <= b <= min(4096, 1024*n):
            raise Unknown('argument-bounds')
        return ('TextList', n, b)

    def signature_kind(name):
        if type(name) is not str:
            raise Unknown('function-signature')
        if name in ('Int64', 'Bool', 'Text', 'TextList'):
            return name
        if name in list_defs:
            list_declaration(name)
            return 'Records:' + name
        if name in record_defs:
            record_fields(name)
            return 'Record:' + name
        raise Unknown('function-signature')

    def visit(x, scope, depth, arg_scope, stack, path='', owner=None):
        try:
            return visit_inner(x, scope, depth, arg_scope, stack, path, owner)
        except (Unknown, UnicodeError, RecursionError) as e:
            if not hasattr(e, 'location'):
                e.location = {'function': owner, 'pointer': path}
            raise

    def visit_inner(x, scope, depth, arg_scope, stack, path, owner):
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
            cost, value = visit(x[2], scope, depth+1, arg_scope, stack, path+'/2', owner)
            nested = dict(scope)
            nested[x[1]] = value
            tail, result = visit(x[3], nested, depth+1, arg_scope, stack, path+'/3', owner)
            return 1+cost+tail, result
        if op == 'if' and len(x) == 4:
            condition, cv = visit(x[1], scope, depth+1, arg_scope, stack, path+'/1', owner)
            yes, yv = visit(x[2], scope, depth+1, arg_scope, stack, path+'/2', owner)
            no, nv = visit(x[3], scope, depth+1, arg_scope, stack, path+'/3', owner)
            if cv[0] != 'Bool' or yv[0] != nv[0]:
                raise Unknown('operand-type')
            joined = (yv[0], max(yv[1], nv[1]), max(yv[2], nv[2]))
            return 1+condition+max(yes, no), joined
        if op == 'record' and 2 <= len(x) <= 10 and type(x[1]) is str:
            return 1+sum(visit(v, scope, depth+1, arg_scope, stack, path+'/'+str(i), owner)[0] for i, v in enumerate(x[2:], 2)), ('Record', 0, 0)
        if op in ('records.len', 'records.at') and len(x) == (2 if op == 'records.len' else 3):
            cost, value = visit(x[1], scope, depth+1, arg_scope, stack, path+'/1', owner)
            if not value[0].startswith('Records:'):
                raise Unknown('operand-type')
            declared = list_declaration(value[0][8:])
            if op == 'records.len':
                return 1+cost, ('Int64', 0, 0)
            index_cost, index_shape = visit(x[2], scope, depth+1, arg_scope, stack, path+'/2', owner)
            if index_shape[0] != 'Int64':
                raise Unknown('operand-type')
            return 1+cost+index_cost, ('Record:' + declared['element'], 0, 0)
        if op == 'field' and len(x) == 3 and type(x[2]) is str:
            cost, value = visit(x[1], scope, depth+1, arg_scope, stack, path+'/1', owner)
            if not value[0].startswith('Record:'):
                raise Unknown('operand-type')
            fields = record_fields(value[0][7:])
            if x[2] not in fields:
                raise Unknown('field-reference')
            return 1+cost, (fields[x[2]], 0, 0)
        if op == 'loop' and len(x) == 6:
            iterations, index_name, accumulator_name = x[1:4]
            if type(iterations) is not int or not 0 <= iterations <= 1024:
                raise Unknown('loop-count')
            if (type(index_name) is not str or type(accumulator_name) is not str or
                index_name == accumulator_name or index_name in scope or accumulator_name in scope):
                raise Unknown('loop-bindings')
            initial_cost, initial = visit(x[4], scope, depth+1, arg_scope, stack, path+'/4', owner)
            if initial[0] not in ('Int64', 'Bool', 'Text', 'TextList'):
                raise Unknown('loop-invariant')
            nested = dict(scope)
            nested[index_name] = ('Int64', 0, 0)
            nested[accumulator_name] = initial
            body_cost, result = visit(x[5], nested, depth+1, arg_scope, stack, path+'/5', owner)
            if result[0] != initial[0] or result[1] > initial[1] or result[2] > initial[2]:
                raise Unknown('loop-invariant')
            return 1+initial_cost+iterations*body_cost, initial
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
            if type(params) is not list or len(params) > 8:
                raise Unknown('function-signature')
            if any(type(p) is not list or len(p) != 2 or type(p[0]) is not str for p in params):
                raise Unknown('function-signature')
            result_kind = signature_kind(function['result'])
            parameter_kinds = [signature_kind(p[1]) for p in params]
            if len({p[0] for p in params}) != len(params) or len(x)-2 != len(params):
                raise Unknown('call-arity')
            cost = 1
            bindings = {}
            for i, (actual, (parameter, _), kind) in enumerate(zip(x[2:], params, parameter_kinds), 2):
                charged, value = visit(actual, scope, depth+1, arg_scope, stack, path+'/'+str(i), owner)
                if value[0] != kind:
                    raise Unknown('operand-type')
                cost += charged
                bindings[parameter] = value
            charged, result = visit(function['body'], {}, depth+1, bindings, stack+(name,), '', name)
            if result[0] != result_kind:
                raise Unknown('operand-type')
            return cost+charged, result
        if op in ('list.len', 'list.unique', 'list.increasing') and len(x) == 2:
            cost, value = visit(x[1], scope, depth+1, arg_scope, stack, path+'/1', owner)
            if value[0] != 'TextList':
                raise Unknown('operand-type')
            _, n, b = value
            if op == 'list.len':
                return 1+cost, ('Int64', 0, 0)
            if op == 'list.increasing':
                return 1+cost+n+2*b, ('Bool', 0, 0)
            return 1+cost+n*n+2*n*b, value
        if op in ('eq', 'lt', 'le', 'add', 'sub', 'mul') and len(x) == 3:
            a, av = visit(x[1], scope, depth+1, arg_scope, stack, path+'/1', owner)
            b, bv = visit(x[2], scope, depth+1, arg_scope, stack, path+'/2', owner)
            if av[0] != bv[0] or av[0] not in (('Int64', 'Bool') if op == 'eq' else ('Int64',)):
                raise Unknown('operand-type')
            return 1+a+b, ('Int64' if op in ('add', 'sub', 'mul') else 'Bool', 0, 0)
        if op == 'not' and len(x) == 2:
            cost, value = visit(x[1], scope, depth+1, arg_scope, stack, path+'/1', owner)
            if value[0] != 'Bool':
                raise Unknown('operand-type')
            return 1+cost, value
        raise Unknown('unsupported-expression')

    try:
        record_defs = {} if records is None else records
        list_defs = {} if lists is None else lists
        if (type(record_defs) is not dict or type(list_defs) is not dict or
            len(record_defs)+len(list_defs) > 8 or
            any(type(k) is not str for k in (*record_defs, *list_defs))):
            raise Unknown('declarations-shape')
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
        return dict(base, status='UNKNOWN', reason=str(e),
                    **({'location': e.location} if hasattr(e, 'location') else {}))
