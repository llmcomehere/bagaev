"""Explicit portable form6 history; no semantic check or execution admission."""
import hashlib,json
import bagaev_record_json_bool_form as form
from bagaev_record_draft import digest
from bagaev_record_revisions import (RevisionError,need,pin,canonical,package_digest,
                                     source_bytes,MAX_REVISIONS)
SCHEMA='bagaev-record-revisions/2'
FORM='record-form/6'

def make_revision(source,parent,source_sha256,program_sha256):
    pin(source_sha256);pin(program_sha256)
    if parent is not None:pin(parent)
    raw=source_bytes(source)
    need(hashlib.sha256(raw).hexdigest()==source_sha256,'REVISION_SOURCE_PIN')
    try:program=form.decode(raw)
    except form.FormError:raise RevisionError('REVISION_SOURCE') from None
    need(digest(program)==program_sha256,'REVISION_PROGRAM_PIN')
    identity=dict(form=FORM,parent=parent,source_sha256=source_sha256,program_sha256=program_sha256)
    return dict(parent=parent,source_sha256=source_sha256,program_sha256=program_sha256,
                id=package_digest(identity),source=raw.decode('utf8'))

def validate(package):
    canonical(package)
    need(type(package) is dict and set(package)=={'schema','form','revisions','head',
         'semantic_check','execution_admission'},'REVISION_SHAPE')
    need(package['schema']==SCHEMA and package['form']==FORM,'REVISION_PROFILE')
    need(package['semantic_check'] is False and package['execution_admission'] is False,'REVISION_ASSURANCE')
    rows=package['revisions'];need(type(rows) is list,'REVISION_SHAPE')
    need(1<=len(rows)<=MAX_REVISIONS,'REVISION_BOUNDS')
    parent,previous,ids=None,None,set()
    for row in rows:
        need(type(row) is dict and set(row)=={'id','parent','source','source_sha256','program_sha256'},'REVISION_SHAPE')
        need(type(row['source']) is str,'REVISION_SHAPE');pin(row['id'])
        need(row['parent']==parent,'REVISION_LINEAGE')
        rebuilt=make_revision(row['source'],parent,row['source_sha256'],row['program_sha256'])
        need(row['id']==rebuilt['id'] and row['id'] not in ids,'REVISION_ID')
        need(row['program_sha256']!=previous,'REVISION_NO_CHANGE')
        ids.add(row['id']);parent,previous=row['id'],row['program_sha256']
    pin(package['head']);need(package['head']==parent,'REVISION_HEAD')
    return package

def initialize(source,*,source_sha256,program_sha256):
    row=make_revision(source,None,source_sha256,program_sha256)
    return validate(dict(schema=SCHEMA,form=FORM,revisions=[row],head=row['id'],
                         semantic_check=False,execution_admission=False))

def append(package,source,*,expected_package_sha256,expected_head,source_sha256,program_sha256):
    validate(package);pin(expected_package_sha256);pin(expected_head)
    need(package_digest(package)==expected_package_sha256,'REVISION_STALE_PACKAGE')
    need(package['head']==expected_head,'REVISION_STALE_HEAD')
    need(len(package['revisions'])<MAX_REVISIONS,'REVISION_BOUNDS')
    row=make_revision(source,expected_head,source_sha256,program_sha256)
    result=json.loads(canonical(package));result['revisions'].append(row);result['head']=row['id']
    return validate(result)

def inspect(package):
    validate(package)
    return dict(schema=SCHEMA,form=FORM,head=package['head'],
        revisions=[{key:value for key,value in row.items() if key!='source'} for row in package['revisions']],
        semantic_check=False,execution_admission=False)

def checkout(package,revision_id):
    validate(package);pin(revision_id)
    for row in package['revisions']:
        if row['id']==revision_id:return row['source'].encode('utf8')
    raise RevisionError('REVISION_NOT_FOUND')

def loads(raw):
    raw=source_bytes(raw)
    depth,quoted,escaped=0,False,False
    for byte in raw:
        if quoted:
            if escaped:escaped=False
            elif byte==92:escaped=True
            elif byte==34:quoted=False
        elif byte==34:quoted=True
        elif byte in (91,123):
            depth+=1;need(depth<=32,'REVISION_BOUNDS')
        elif byte in (93,125):depth-=1
    def pairs(items):
        result={}
        for key,value in items:
            need(key not in result,'REVISION_JSON');result[key]=value
        return result
    def reject(value):raise RevisionError('REVISION_JSON')
    try:value=json.loads(raw,object_pairs_hook=pairs,parse_int=reject,parse_float=reject,parse_constant=reject)
    except (ValueError,RecursionError) as error:
        if isinstance(error,RevisionError):raise
        raise RevisionError('REVISION_JSON') from None
    return validate(value)
