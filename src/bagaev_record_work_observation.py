"""Source-pinned conditional work and actual dimension observations; no aggregate admission."""
import hashlib
import re
from bagaev_record_draft import digest,need
import bagaev_record_wide_form as form
from bagaev_record_work import analyze
from bagaev_record_argument_dimensions import observe


def observe_source(source,bounds,arguments,*,program_sha256):
    need(type(program_sha256) is str and re.fullmatch('[0-9a-f]{64}',program_sha256) is not None,'WORK_PIN')
    program=form.decode(source)
    need(digest(program)==program_sha256,'WORK_PROGRAM')
    entry=program['functions'].get(program['entry'])
    need(entry is not None,'WORK_ARGUMENTS')
    params=entry['params'];names=[p[0] for p in params]
    need(len(set(names))==len(names) and type(arguments) is list and len(arguments)==len(params),'WORK_ARGUMENTS')
    need(type(bounds) is dict and set(bounds)==set(names) and
         all(type(bounds[n]) is dict and bounds[n].get('type')==t for n,t in params),'WORK_ARGUMENTS')
    dimensions=observe(bounds,dict(zip(names,arguments)))
    work=analyze(entry['body'],bounds,program['functions'],program['records'],program['lists'])
    if 'location' in work and work['location']['function'] is None:
        work['location']['function']=program['entry']
    raw=source.encode('utf-8') if isinstance(source,str) else source
    return {'schema':'bagaev-record-work-observation/1','status':'observation',
            'source_sha256':hashlib.sha256(raw).hexdigest(),'program_sha256':program_sha256,
            'entry':program['entry'],'argument_dimensions':dimensions,'work_bound':work,
            'semantic_check':False,'execution_admission':False,'requires_checked_program':True}
