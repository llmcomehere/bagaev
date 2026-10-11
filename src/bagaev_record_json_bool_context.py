"""Read-only focused form6 context. No replacement, evaluation or admission."""
import copy
import hashlib
import bagaev_record_json_bool_form as form
import bagaev_record_json_bool_spans as spans
from bagaev_record_draft import digest, DraftError, need
from bagaev_record_wide_function import _calls


def fragment(source, name):
    program = form.decode(source)
    need(type(name) is str and name in program['functions'], 'FUNCTION_NAME')
    function = program['functions'][name]
    part = copy.deepcopy(program)
    part['entry'] = name
    part['functions'] = {name: copy.deepcopy(function)}
    return dict(schema='bagaev-function-fragment/2', form='record-form/6',
                base=digest(program), function=name, function_sha256=digest(function),
                source=form.encode(part).decode('utf8'),
                semantic_check=False, execution_admission=False)


def context(source, name):
    program = form.decode(source)
    packet = fragment(source, name)
    functions = program['functions']
    calls = {n: _calls(f['body']) for n, f in functions.items()}
    def declaration(n):
        f = functions.get(n)
        return dict(name=n, declared=f is not None,
                    params=copy.deepcopy(f['params']) if f is not None else None,
                    result=f['result'] if f is not None else None,
                    function_sha256=digest(f) if f is not None else None)
    return dict(schema='bagaev-function-context/2', fragment=packet,
                callees=[declaration(n) for n in sorted(calls[name])],
                callers=[declaration(n) for n in sorted(functions) if name in calls[n]],
                scope='direct-syntactic-calls', semantic_check=False, execution_admission=False)


def located_context(source, name):
    packet = context(source, name)
    mapping = spans.source_map(source)
    need(mapping['program_pin'] == 'sha256:' + packet['fragment']['base'], 'FUNCTION_MAP')
    prefix = '/program/functions/' + name + '/body'
    mapping['locations'] = [item for item in mapping['locations']
                            if item['program_pointer'] == prefix or item['program_pointer'].startswith(prefix + '/')]
    need(bool(mapping['locations']), 'FUNCTION_MAP')
    packet.update(schema='bagaev-function-context/3', source_locations=mapping,
                  location_source='original-full-input; not fragment.source')
    return packet


def source_context(source, name):
    packet = located_context(source, name)
    pointer = '/program/functions/' + name + '/body'
    roots = [item for item in packet['source_locations']['locations']
             if item['program_pointer'] == pointer]
    need(len(roots) == 1 and roots[0]['precision'] == 'exact-expression', 'FUNCTION_MAP')
    location = roots[0]
    raw = source.encode('utf8') if type(source) is str else source
    start, end = location['start_byte'], location['end_byte']
    need(0 <= start < end <= len(raw), 'FUNCTION_MAP')
    body = raw[start:end]
    packet.update(schema='bagaev-function-context/4', original_body=dict(
        text=body.decode('utf8'), sha256=hashlib.sha256(body).hexdigest(),
        source_sha256=packet['source_locations']['source_sha256'],
        location=copy.deepcopy(location),
        scope='original-body-expression; excludes surrounding trivia'))
    return packet
