"""Focused form4 function fragments and detached replacements; no execution."""
import copy
import bagaev_record_json_form as form
from bagaev_record_draft import digest, DraftError, need

def fragment(source,name):
    program=form.decode(source)
    need(type(name)is str and name in program['functions'],'FUNCTION_NAME')
    function=program['functions'][name]
    part=copy.deepcopy(program);part['entry']=name;part['functions']={name:copy.deepcopy(function)}
    raw=form.encode(part)
    return {'schema':'bagaev-function-fragment/1','form':'record-form/4',
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
    return {'schema':'bagaev-record-draft/1','status':'draft','base':base_sha256,
            'target':digest(candidate),'program':candidate,
            'delta':{'add':[],'replace':[name]},'semantic_check':False,'execution_admission':False}
