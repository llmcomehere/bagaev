"""Independent call interpreter for the finite CALL-0.1 research corpus.

This module imports neither the call engine nor either frozen OBS/law engine.
Function records and programs are JSON-shaped fixture inputs. The interpreter
assumes the well-typed fragment checked by the profile; it is not a second full
type checker and does not implement bagaev.
"""
from __future__ import annotations

from dataclasses import dataclass


class OracleInputError(ValueError):
    pass


class _ProgramError(Exception):
    pass


class _UnknownExecution(Exception):
    pass


@dataclass(frozen=True)
class Execution:
    status: str
    value: object = None
    error: str | None = None
    trace: tuple = ()
    complete: bool = True
    unknown_reason: str | None = None


def json_value(value):
    if isinstance(value, (set, frozenset)):
        return {'$set': sorted(json_value(item) for item in value)}
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in sorted(value.items())}
    return value


def observations(result):
    """The fixed OBS visible domain, also used for complete CALL outcomes."""
    return {'status': result.status, 'value': json_value(result.value),
            'error': result.error, 'trace': json_value(result.trace),
            'complete': result.complete}


def _resource(spec):
    if spec is None:
        return (), 'MISSING_RESOURCE'
    if not isinstance(spec, dict) or 'members' not in spec:
        raise OracleInputError('RESOURCE_SPEC')
    members = spec['members']
    if not isinstance(members, (list, tuple)) or any(type(x) is not str for x in members):
        raise OracleInputError('RESOURCE_MEMBERS')
    if len(set(members)) != len(members):
        raise OracleInputError('DUPLICATE_AUTHOR')
    error = spec.get('read_error')
    if error is not None and type(error) is not str:
        raise OracleInputError('RESOURCE_ERROR')
    return tuple(members), error


def resource_observations(spec):
    members, error = _resource(spec)
    values = {'ordered_members': members, 'member_set': frozenset(members),
              'count': len(members)}
    result = {name: ('error', error) if error is not None else ('ok', value)
              for name, value in values.items()}
    result['read_status'] = 'ok' if error is None else 'error:' + error
    return result


def changed_observations(before, after):
    left, right = resource_observations(before), resource_observations(after)
    return frozenset(name for name in left if left[name] != right[name])


def _registry(functions):
    rows = functions.values() if isinstance(functions, dict) else functions
    result = {}
    for function in rows:
        identifier = function['stable_id']
        if identifier in result:
            raise OracleInputError('DUPLICATE_FUNCTION')
        names = [parameter['name'] for parameter in function['params']]
        if len(set(names)) != len(names):
            raise OracleInputError('DUPLICATE_PARAMETER')
        result[identifier] = function
    return result


def execute(program, functions, resource_spec, config=None):
    """Evaluate strict arguments in caller env, then enter a fresh callee env.

    A missing target and a call to an already active function become unknown
    only after the arguments have completed. A nonselected branch is not run.
    The active stack provides the explicit finite cycle guard; no external
    implementation is invoked or inferred.
    """
    members, resource_error = _resource(resource_spec)
    declarations = _registry(functions)
    configuration = dict(config or {})
    effects = []

    def evaluate(node, environment, active):
        op = node['op']
        if op == 'const':
            return node['value']
        if op == 'read':
            view = node['view']
            if view == 'read_status':
                return 'ok' if resource_error is None else 'error:' + resource_error
            if resource_error is not None:
                raise _ProgramError(resource_error)
            if view == 'ordered_members':
                return members
            if view == 'member_set':
                return frozenset(members)
            if view == 'count':
                return len(members)
            raise OracleInputError('UNKNOWN_VIEW')
        if op == 'var':
            if node['name'] not in environment:
                raise OracleInputError('UNBOUND_VARIABLE')
            return environment[node['name']]
        if op == 'config':
            key = node['key']
            if key not in configuration or type(configuration[key]) is not bool:
                raise OracleInputError('CONFIG_BOOL_REQUIRED')
            return configuration[key]
        if op == 'call':
            # Deliberately keep argument evaluation separate from parameter
            # binding: an earlier parameter cannot capture a later argument.
            arguments = []
            for argument in node['args']:
                arguments.append(evaluate(argument, environment, active))
            target = node['target']
            if target not in declarations:
                raise _UnknownExecution('MISSING_CALLEE:' + target)
            if target in active:
                raise _UnknownExecution('CALL_CYCLE:' + target)
            function = declarations[target]
            if len(arguments) != len(function['params']):
                raise OracleInputError('CALL_ARITY_MISMATCH')
            if function['body'] is None:
                raise _UnknownExecution('EXTERNAL_CALLEE:' + target)
            callee_environment = {parameter['name']: value
                                  for parameter, value in zip(function['params'], arguments)}
            return evaluate(function['body'], callee_environment, active + (target,))
        if op == 'let':
            value = evaluate(node['value'], environment, active)
            inner = dict(environment)
            inner[node['name']] = value
            return evaluate(node['body'], inner, active)
        if op == 'if':
            condition = evaluate(node['condition'], environment, active)
            if type(condition) is not bool:
                raise OracleInputError('CONDITION_BOOL_REQUIRED')
            return evaluate(node['then'] if condition else node['else'], environment, active)
        if op == 'contains':
            collection = evaluate(node['collection'], environment, active)
            item = evaluate(node['item'], environment, active)
            return item in collection
        if op == 'size':
            return len(evaluate(node['value'], environment, active))
        if op == 'to_set':
            return frozenset(evaluate(node['value'], environment, active))
        if op == 'head':
            value = evaluate(node['value'], environment, active)
            if len(value) == 0:
                raise _ProgramError('EMPTY_HEAD')
            return value[0]
        if op == 'eq':
            left = evaluate(node['left'], environment, active)
            right = evaluate(node['right'], environment, active)
            return left == right
        if op == 'pair':
            left = evaluate(node['left'], environment, active)
            right = evaluate(node['right'], environment, active)
            return left, right
        if op == 'tuple':
            return tuple(evaluate(item, environment, active) for item in node['items'])
        if op == 'seq':
            if not node['items']:
                raise OracleInputError('EMPTY_SEQUENCE')
            value = None
            for item in node['items']:
                value = evaluate(item, environment, active)
            return value
        if op == 'emit':
            value = evaluate(node['value'], environment, active)
            effects.append({'label': node['label'], 'value': value})
            return evaluate(node['then'], environment, active) if 'then' in node else None
        if op == 'fail':
            raise _ProgramError(node['code'])
        if op == 'opaque':
            for argument in node.get('args', ()):
                evaluate(argument, environment, active)
            raise _UnknownExecution(node.get('name', 'opaque'))
        if op == 'unknown':
            raise _UnknownExecution(node.get('reason', 'unknown'))
        raise OracleInputError('UNKNOWN_AST_OPERATION:' + str(op))

    try:
        value = evaluate(program, {}, ())
        return Execution('ok', value, trace=tuple(effects))
    except _ProgramError as error:
        return Execution('error', error=str(error), trace=tuple(effects))
    except _UnknownExecution as unknown:
        return Execution('unknown', trace=tuple(effects), complete=False,
                         unknown_reason=str(unknown))
