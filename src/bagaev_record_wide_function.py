"""Focused form5 function fragments and detached replacements; no execution."""
import copy
import bagaev_record_wide_form as form
from bagaev_record_draft import digest, DraftError, need

def fragment(source,name):
    program=form.decode(source)
    need(type(name)is str and name in program['functions'],'FUNCTION_NAME')
    function=program['functions'][name]
    part=copy.deepcopy(program);part['entry']=name;part['functions']={name:copy.deepcopy(function)}
    raw=form.encode(part)
    return {'schema':'bagaev-function-fragment/2','form':'record-form/5',
            'base':digest(program),'function':name,'function_sha256':digest(function),
            'source':raw.decode('utf8'),'semantic_check':False,'execution_admission':False}

def replace(source,replacement,*,base_sha256,function_sha256):
    program=form.decode(source)
    need(type(base_sha256)is str and digest(program)==base_sha256,'FUNCTION_BASE')
    part=form.decode(replacement);name=part['entry']
    need(set(part['functions'])=={name} and name in program['functions'],'FUNCTION_SCOPE')
    original=program['functions'][name];proposed=part['functions'][name]
    need(type(function_sha256)is str and digest(original)==function_sha256,'FUNCTION_PIN')
    need(all(part[k]==program[k] for k in ('schema','records','lists','variants')),'FUNCTION_SCOPE')
    need(original['params']==proposed['params'] and original['result']==proposed['result'],'FUNCTION_SIGNATURE')
    need(original!=proposed,'FUNCTION_NO_CHANGE')
    candidate=copy.deepcopy(program);candidate['functions'][name]=copy.deepcopy(proposed)
    form.bounded(candidate)
    return {'schema':'bagaev-record-draft/2','status':'draft','base':base_sha256,
            'target':digest(candidate),'program':candidate,
            'delta':{'add':[],'replace':[name]},'semantic_check':False,'execution_admission':False}

def _calls(body):
    found=set();pending=[body]
    while pending:
        node=pending.pop()
        if type(node)is not list or not node:continue
        if node[0]=='call':found.add(node[1])
        if node[0]=='match':
            pending.append(node[1]);pending.extend(arm[2] for arm in node[2])
        else:pending.extend(x for x in node[1:] if type(x)is list)
    return found

def context(source,name):
    program=form.decode(source);packet=fragment(source,name)
    functions=program['functions'];calls={n:_calls(f['body']) for n,f in functions.items()}
    def declaration(n):
        f=functions.get(n)
        return {'name':n,'declared':f is not None,
                'params':copy.deepcopy(f['params']) if f is not None else None,
                'result':f['result'] if f is not None else None,
                'function_sha256':digest(f) if f is not None else None}
    return {'schema':'bagaev-function-context/2','fragment':packet,
            'callees':[declaration(n) for n in sorted(calls[name])],
            'callers':[declaration(n) for n in sorted(functions) if name in calls[n]],
            'scope':'direct-syntactic-calls','semantic_check':False,'execution_admission':False}


def located_context(source, name):
    """Optional ranges refer to original full source, never fragment.source."""
    import bagaev_record_wide_spans as spans
    packet = context(source, name)
    mapping = spans.source_map(source)
    need(mapping['program_pin'] == 'sha256:' + packet['fragment']['base'], 'FUNCTION_MAP')
    prefix = '/program/functions/' + name + '/body'
    mapping['locations'] = [item for item in mapping['locations']
                            if item['program_pointer'] == prefix or item['program_pointer'].startswith(prefix + '/')]
    need(bool(mapping['locations']), 'FUNCTION_MAP')
    packet['schema'] = 'bagaev-function-context/3'
    packet['source_locations'] = mapping
    packet['location_source'] = 'original-full-input; not fragment.source'
    return packet


def source_context(source, name):
    """Explicit original expression text, including internal untrusted comments."""
    import hashlib
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
    packet['schema'] = 'bagaev-function-context/4'
    packet['original_body'] = {
        'text': body.decode('utf8'),
        'sha256': hashlib.sha256(body).hexdigest(),
        'source_sha256': packet['source_locations']['source_sha256'],
        'location': copy.deepcopy(location),
        'scope': 'original-body-expression; excludes surrounding trivia',
    }
    return packet
