"""Bounded context reconstruction. No discovery, model calls, effects or admission.

Kernel semantic checking is an explicit trusted host dependency. Packet metadata
can never supply a callable, endpoint, checker selection or execution permission.
"""
from __future__ import annotations
import copy
import hashlib
import math
import re
import bagaev_forms as forms
import bagaev_l2 as l2

CODES = frozenset(('CTX_BOUNDS CTX_JSON CTX_SHAPE CTX_VERSION CTX_MISSING CTX_STALE '
                   'CTX_PIN CTX_REMAPPED CTX_UNSUPPORTED CTX_DRAFT CTX_ROLE CTX_NO_CHOICE').split())
AXES = ('semantic','ir','form','envelope','evidence')
DIGEST = re.compile(r'sha256:[0-9a-f]{64}\Z',re.ASCII)
ID = re.compile(r'[A-Za-z][A-Za-z0-9._-]{0,63}\Z',re.ASCII)
CONTEXT_FIELDS = ('schema','axes','snapshot','sources','obligations','unknowns','open_effects','candidates','candidate_set','metadata')

class ContextError(ValueError):
    def __init__(self, code, location=''):
        self.code,self.location=code,location
        super().__init__(code)

class ContextUnavailable(RuntimeError):
    """Missing/invalid host checking capability, not a semantic observation."""

class KernelRefusal(ValueError):
    """Trusted checker refusal, with program-relative normative IR location."""
    def __init__(self, code, location):
        self.code,self.location=code,location
        super().__init__(code)

def _need(test,code='CTX_SHAPE',path=''):
    if not test:raise ContextError(code,path)

def _fields(value, names, path=''):
    _need(type(value) is dict and set(value)==set(names),path=path)

def _text(value,path,limit=4096,nonempty=False):
    _need(type(value) is str,path=path)
    _need(not any(0xd800<=ord(c)<=0xdfff for c in value),path=path)
    raw=value.encode('utf-8')
    if limit is not None:_need(len(raw)<=limit,'CTX_BOUNDS',path)
    if nonempty:_need(bool(raw),path=path)
    return raw

def _id(value,path):
    _need(type(value) is str and ID.fullmatch(value) is not None,path=path)

def _pin(value,path):
    _need(type(value) is str and DIGEST.fullmatch(value) is not None,path=path)

def _schema(value,name,path=''):
    _text(value['schema'],path+'/schema',None)
    _need(value['schema']==name,'CTX_VERSION',path+'/schema')

def _axes(value,path='/axes'):
    _fields(value,AXES,path)
    for key in AXES:_text(value[key],path+'/'+key,None)
    _need(value['semantic'] in ('bagaev-l2/1','bagaev-probe-ir/1'),'CTX_VERSION',path+'/semantic')
    _need(value['ir']==value['semantic'],'CTX_VERSION',path+'/ir')
    for key,name in [('form','probe-forms/1'),('envelope','probe-context/1'),('evidence','probe-evidence/1')]:
        _need(value[key]==name,'CTX_VERSION',path+'/'+key)

def _bounds(value,depth_limit,count_limit):
    pending=[(value,1)];count=0
    while pending:
        item,depth=pending.pop();count+=1
        _need(depth<=depth_limit and count<=count_limit,'CTX_BOUNDS')
        if type(item) is dict:pending.extend((item[k],depth+1) for k in reversed(sorted(item)))
        elif type(item) is list:pending.extend((x,depth+1) for x in reversed(item))

def _parse(source,byte_limit):
    _need(type(source) in (str,bytes),'CTX_JSON')
    try:raw=source.encode('utf-8') if type(source) is str else source
    except UnicodeError:raise ContextError('CTX_JSON') from None
    _need(len(raw)<=byte_limit,'CTX_BOUNDS')
    try:return forms._json_exact(raw,text_limit=False)
    except l2.L2Error:raise ContextError('CTX_JSON') from None

def _canonical(value,limit=4194304,path=''):
    """Iterative bounded C, preserving exact integers and scalar Unicode."""
    chunks=[];size=0;pending=[('value',value)]
    def add(text):
        nonlocal size
        raw=text.encode('utf-8');size+=len(raw)
        _need(size<=limit,'CTX_BOUNDS',path);chunks.append(raw)
    while pending:
        tag,item=pending.pop()
        if tag=='token':add(item);continue
        kind=type(item)
        if kind is dict:
            _need(all(type(k) is str for k in item),path=path)
            add('{');pending.append(('token','}'));keys=sorted(item)
            for i in range(len(keys)-1,-1,-1):
                key=keys[i];pending.extend([('value',item[key]),('token',':'),('value',key)])
                if i:pending.append(('token',','))
        elif kind is list:
            add('[');pending.append(('token',']'))
            for i in range(len(item)-1,-1,-1):
                pending.append(('value',item[i]))
                if i:pending.append(('token',','))
        else:
            _need(kind in (str,int,float,bool,type(None)),path=path)
            if kind is str:_text(item,path,None)
            if kind is float:_need(math.isfinite(item),path=path)
            try:add(forms._quote(item,integer_byte_limit=limit))
            except forms.FormError:raise ContextError('CTX_BOUNDS',path) from None
    return b''.join(chunks)

def _hash(value):return 'sha256:'+hashlib.sha256(_canonical(value)).hexdigest()
def _bytes_pin(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()

def _records(value,minimum,maximum,path,fields):
    _need(type(value) is list,path=path)
    _need(minimum<=len(value)<=maximum,'CTX_BOUNDS',path)
    previous=None
    for i,row in enumerate(value):
        at=path+'/'+str(i);_fields(row,fields,at);_id(row['id'],at+'/id')
        _need(previous is None or previous<row['id'],path=at+'/id');previous=row['id']
    return value

def _reference(ref,path):
    _fields(ref,('source','pin','start','end'),path)
    _id(ref['source'],path+'/source');_pin(ref['pin'],path+'/pin')
    for key in ('start','end'):_need(type(ref[key]) is int,path=path+'/'+key)

def _references(refs,minimum,path):
    _need(type(refs) is list,path=path);_need(minimum<=len(refs)<=8,'CTX_BOUNDS',path)
    previous=None
    for i,ref in enumerate(refs):
        at=path+'/'+str(i);_reference(ref,at);order=(ref['source'],ref['start'],ref['end'])
        _need(previous is None or previous<order,path=at);previous=order

def _resolve(ref,sources,path):
    _need(ref['source'] in sources,'CTX_MISSING',path+'/source')
    row,_,raw=sources[ref['source']]
    _need(ref['pin']==row['pin'],'CTX_STALE',path+'/pin')
    start,end=ref['start'],ref['end']
    _need(0<=start<end<=len(raw),path=path)
    try:raw[:start].decode('utf-8');raw[:end].decode('utf-8')
    except UnicodeError:raise ContextError('CTX_SHAPE',path) from None

def _shape(context):
    _fields(context,CONTEXT_FIELDS);_fields(context['axes'],AXES,'/axes')
    _schema(context,'probe-context/1');_axes(context['axes']);_bounds(context,136,65536)
    _pin(context['snapshot'],'/snapshot')
    total=0
    for i,row in enumerate(_records(context['sources'],1,16,'/sources',('id','pin','text'))):
        path='/sources/'+str(i);_pin(row['pin'],path+'/pin')
        total+=len(_text(row['text'],path+'/text',131072))
        _need(total<=1048576,'CTX_BOUNDS','/sources')
    for name,lo,hi in [('obligations',1,32),('unknowns',0,32),('open_effects',0,16)]:
        fields=('id','text','refs','pin') if name=='obligations' else ('id','text','refs')
        for i,row in enumerate(_records(context[name],lo,hi,'/'+name,fields)):
            path='/'+name+'/'+str(i);_text(row['text'],path+'/text',nonempty=True)
            _references(row['refs'],0 if name=='unknowns' else 1,path+'/refs')
            if name=='obligations':_pin(row['pin'],path+'/pin')
    total=0
    for i,row in enumerate(_records(context['candidates'],0,16,'/candidates',('id','kind','state','content','pin'))):
        path='/candidates/'+str(i)
        _need(type(row['kind']) is str and row['kind'] in ('program','patch'),path=path+'/kind')
        if context['axes']['semantic']=='bagaev-probe-ir/1':_need(row['kind']=='program',path=path+'/kind')
        _need(type(row['state']) is str and row['state'] in ('choice','draft'),path=path+'/state')
        _need(type(row['content']) is dict,path=path+'/content')
        total+=len(_canonical(row['content'],1048576,path+'/content'))
        _need(total<=2097152,'CTX_BOUNDS','/candidates');_pin(row['pin'],path+'/pin')
    _pin(context['candidate_set'],'/candidate_set')
    meta=context['metadata'];_fields(meta,('representation','model_profile','codec'),'/metadata')
    _need(type(meta['representation']) is str and meta['representation']=='canonical-json/1',path='/metadata/representation')
    for key in ('model_profile','codec'):
        if meta[key] is not None:_text(meta[key],'/metadata/'+key)
    _canonical(context)

def _expectation(source):
    _need(source is not None,'CTX_MISSING')
    value=_parse(source,2097152)
    _fields(value,('schema','axes','snapshot','candidate_set','sources','obligations','baseline'))
    _schema(value,'probe-expectation/1');_axes(value['axes']);_bounds(value,136,32768)
    _pin(value['snapshot'],'/snapshot');_pin(value['candidate_set'],'/candidate_set')
    for name,limit in [('sources',16),('obligations',32)]:
        for i,row in enumerate(_records(value[name],1,limit,'/'+name,('id','pin'))):_pin(row['pin'],'/'+name+'/'+str(i)+'/pin')
    _canonical(value,2097152)
    return value

def _semantic(program,semantic,kernel_checker,path):
    if semantic=='bagaev-l2/1':
        # Already-reconstructed string roots cannot re-enter the text parser.
        if type(program) is not dict:raise l2.L2Error('L2_PROGRAM')
        checked=l2.check_program(program).canonical
    else:
        if kernel_checker is None:raise ContextUnavailable('an explicit trusted kernel checker is required')
        try:checked=kernel_checker(copy.deepcopy(program))
        except KernelRefusal as error:raise KernelRefusal(error.code,path+error.location) from None
        if type(checked) is not bytes:raise ContextUnavailable('checker must return checked canonical program bytes')
    if checked!=_canonical(program,1048576,path):raise ContextUnavailable('checker changed or failed to bind the complete program')
    return _bytes_pin(checked)

def _validate(context_source,expectation_source,kernel_checker):
    context=_parse(context_source,4194304);_shape(context)
    expected=_expectation(expectation_source)
    snapshot=_semantic(expected['baseline'],expected['axes']['semantic'],kernel_checker,'/baseline')
    for key in AXES:_need(expected['axes'][key]==context['axes'][key],'CTX_STALE','/axes/'+key)
    _need(expected['snapshot']==snapshot and context['snapshot']==snapshot,'CTX_STALE','/snapshot')
    sources={row['id']:(row,i,row['text'].encode('utf-8')) for i,row in enumerate(context['sources'])}
    for row,i,raw in sources.values():_need(_bytes_pin(raw)==row['pin'],'CTX_PIN','/sources/'+str(i)+'/pin')
    for row in expected['sources']:
        _need(row['id'] in sources,'CTX_MISSING','/sources')
        actual,i,_=sources[row['id']];_need(actual['pin']==row['pin'],'CTX_STALE','/sources/'+str(i)+'/pin')
    for name in ('obligations','unknowns','open_effects'):
        for i,row in enumerate(context[name]):
            for j,ref in enumerate(row['refs']):_resolve(ref,sources,'/'+name+'/'+str(i)+'/refs/'+str(j))
    obligations={row['id']:(row,i) for i,row in enumerate(context['obligations'])}
    for row,i in obligations.values():_need(_hash({k:v for k,v in row.items() if k!='pin'})==row['pin'],'CTX_PIN','/obligations/'+str(i)+'/pin')
    for row in expected['obligations']:
        _need(row['id'] in obligations,'CTX_MISSING','/obligations')
        actual,i=obligations[row['id']];_need(actual['pin']==row['pin'],'CTX_STALE','/obligations/'+str(i)+'/pin')
    for i,row in enumerate(context['candidates']):_need(_hash(row['content'])==row['pin'],'CTX_PIN','/candidates/'+str(i)+'/pin')
    mapping={'schema':'probe-candidate-set/1','candidates':[{k:row[k] for k in ('id','kind','state','pin')} for row in context['candidates']]}
    _need(_hash(mapping)==context['candidate_set'],'CTX_PIN','/candidate_set')
    _need(expected['candidate_set']==context['candidate_set'],'CTX_REMAPPED','/candidate_set')
    for i,row in enumerate(context['candidates']):
        if row['state']=='draft':continue
        if row['kind']=='program':_semantic(row['content'],context['axes']['semantic'],kernel_checker,'/candidates/'+str(i)+'/content')
        else:
            l2.apply_patch(expected['baseline'],row['content'])
    return context,expected,sources,obligations

def inspect(context,expectation,*,kernel_checker=None):
    """Validate phases 1–6 only. No evidence/decision/response acceptance yet.

    A kernel_checker is trusted host code, never packet data. It must perform
    complete deterministic semantic checking and return the exact canonical
    program bytes, or raise KernelRefusal. No missing-checker fallback exists.
    """
    value,_,_,_=_validate(context,expectation,kernel_checker)
    return {'schema':'probe-context-inspection/1','snapshot':value['snapshot'],
            'candidate_set':value['candidate_set'],'unknowns':[x['id'] for x in value['unknowns']],
            'open_effects':[x['id'] for x in value['open_effects']],
            'admission':False,'model_calls':0}

def _frame(source,fields,schema,byte_limit,depth,count):
    value=_parse(source,byte_limit);_fields(value,fields);_schema(value,schema)
    _bounds(value,depth,count);_canonical(value,byte_limit)
    return value

def _evidence(source,context,sources,obligations):
    if source is None:return {'phase':'evidence','status':'absent','records':[]}
    value=_frame(source,('schema','context','snapshot','records'),'probe-evidence/1',262144,16,4096)
    _pin(value['context'],'/context');_pin(value['snapshot'],'/snapshot')
    rows=_records(value['records'],0,32,'/records',('id','subject','obligations','result','source'))
    for i,row in enumerate(rows):
        path='/records/'+str(i);_pin(row['subject'],path+'/subject')
        _need(type(row['obligations']) is list,path=path+'/obligations')
        _need(1<=len(row['obligations'])<=32,'CTX_BOUNDS',path+'/obligations')
        previous=None
        for j,identifier in enumerate(row['obligations']):
            _id(identifier,path+'/obligations/'+str(j))
            _need(previous is None or previous<identifier,path=path+'/obligations/'+str(j));previous=identifier
        _need(type(row['result']) is str and row['result'] in ('supported','negative','indeterminate','not-run'),path=path+'/result')
        _reference(row['source'],path+'/source')
    _need(value['context']==_hash(context),'CTX_STALE','/context')
    _need(value['snapshot']==context['snapshot'],'CTX_STALE','/snapshot')
    subjects={context['snapshot'],*[x['pin'] for x in context['candidates']]}
    result=[]
    for i,row in enumerate(rows):
        path='/records/'+str(i)
        _need(row['subject'] in subjects,'CTX_MISSING',path+'/subject')
        for j,identifier in enumerate(row['obligations']):_need(identifier in obligations,'CTX_MISSING',path+'/obligations/'+str(j))
        _resolve(row['source'],sources,path+'/source')
        result.append({k:copy.deepcopy(row[k]) for k in ('id','result','subject','obligations')})
    return {'phase':'evidence','status':'applicable','records':result}

def _request(source,context,candidates):
    value=_frame(source,('schema','context','snapshot','candidate_set','role','target','intent'),'probe-decision/1',65536,8,64)
    for key in ('context','snapshot','candidate_set'):_pin(value[key],'/'+key)
    _need(type(value['role']) is str and value['role'] in ('generate','refine','select','rank','solve'),path='/role')
    if value['target'] is not None:_id(value['target'],'/target')
    _text(value['intent'],'/intent',nonempty=True)
    _need(value['context']==_hash(context),'CTX_STALE','/context')
    _need(value['snapshot']==context['snapshot'],'CTX_STALE','/snapshot')
    _need(value['candidate_set']==context['candidate_set'],'CTX_REMAPPED','/candidate_set')
    _need(value['role'] not in ('rank','solve'),'CTX_UNSUPPORTED','/role')
    if value['role']=='refine':
        _need(value['target'] is not None,path='/target')
        _need(value['target'] in candidates,'CTX_MISSING','/target')
        _need(candidates[value['target']]['state']=='draft','CTX_DRAFT','/target')
    else:_need(value['target'] is None,path='/target')
    return value

def _response(source,request,context,candidates):
    fields=('schema','request','context','snapshot','candidate_set','role','outcome','candidate_id','content','content_pin','code')
    value=_frame(source,fields,'probe-response/1',2097152,136,32768)
    for key in ('request','context','snapshot','candidate_set'):_pin(value[key],'/'+key)
    _need(type(value['role']) is str and value['role'] in ('generate','refine','select','rank','solve'),path='/role')
    _need(type(value['outcome']) is str and value['outcome'] in ('draft','choice','abstain','no-choice','refused'),path='/outcome')
    if value['candidate_id'] is not None:_id(value['candidate_id'],'/candidate_id')
    if value['content'] is not None:
        _need(type(value['content']) is dict,path='/content');_canonical(value['content'],1048576,'/content')
    if value['content_pin'] is not None:_pin(value['content_pin'],'/content_pin')
    if value['code'] is not None:_need(type(value['code']) is str and value['code'] in CODES,path='/code')
    _need(value['request']==_hash(request),'CTX_STALE','/request')
    _need(value['context']==_hash(context),'CTX_STALE','/context')
    _need(value['snapshot']==context['snapshot'],'CTX_STALE','/snapshot')
    _need(value['candidate_set']==context['candidate_set'],'CTX_REMAPPED','/candidate_set')
    _need(value['role']==request['role'],'CTX_ROLE','/role')
    role,outcome=value['role'],value['outcome']
    event={'phase':'response','outcome':outcome,'candidate_id':value['candidate_id'],'admission':False}
    if outcome=='draft':
        _need(role in ('generate','refine'),'CTX_ROLE','/outcome')
        _need(value['candidate_id'] is None and type(value['content']) is dict and value['content_pin'] is not None and value['code'] is None)
        _need(_hash(value['content'])==value['content_pin'],'CTX_PIN','/content_pin')
        event.update({'content':copy.deepcopy(value['content']),'content_pin':value['content_pin']})
    elif outcome=='choice':
        _need(role=='select','CTX_ROLE','/outcome')
        _need(value['candidate_id'] is not None and value['content'] is None and value['content_pin'] is None and value['code'] is None)
        _need(value['candidate_id'] in candidates,'CTX_MISSING','/candidate_id')
        selected=candidates[value['candidate_id']]
        _need(selected['state']=='choice','CTX_DRAFT','/candidate_id')
        event['content_pin']=selected['pin']
    else:
        _need(value['candidate_id'] is None and value['content'] is None and value['content_pin'] is None)
        if outcome=='abstain':_need(value['code'] is None)
        elif outcome=='no-choice':
            _need(role=='select','CTX_ROLE','/outcome');_need(value['code']=='CTX_NO_CHOICE')
        else:_need(value['code'] in CODES)
        event['code']=value['code']
    return event

def process(context,expectation,*,evidence=None,request=None,response=None,kernel_checker=None):
    """Validate a complete bounded exchange; all inputs remain separate frames.

    Evidence labels are preserved assertions, never proof of execution. Requests
    and responses must either both be supplied or both absent. No response or
    validated choice is exposed until every applicable phase has succeeded.
    """
    value,_,sources,obligations=_validate(context,expectation,kernel_checker)
    events=[{'phase':'context','status':'valid','snapshot':value['snapshot'],'candidate_set':value['candidate_set']}]
    events.append(_evidence(evidence,value,sources,obligations))
    if request is not None or response is not None:
        _need(request is not None,'CTX_MISSING','/request')
        candidates={row['id']:row for row in value['candidates']}
        req=_request(request,value,candidates)
        _need(response is not None,'CTX_MISSING','/response')
        events.append(_response(response,req,value,candidates))
    return {'events':events,'unknowns':[x['id'] for x in value['unknowns']],
            'open_effects':[x['id'] for x in value['open_effects']],
            'admission':False,'model_calls':0}
