"""Deterministic specialized lowering of already checked data; never executes it."""
import json
import re


class LoweringError(ValueError):
    def __init__(self,code='CPY_UNSUPPORTED'):
        self.code=code
        super().__init__(code)


def need(ok):
    if not ok:raise LoweringError()


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')


def metrics(value):
    count=depth=0;pending=[(value,1)]
    while pending:
        item,level=pending.pop();count+=1;depth=max(depth,level)
        if type(item) is list:pending.extend((v,level+1) for v in item)
        elif type(item) is dict:pending.extend((v,level+1) for v in item.values())
    return count,depth


HELPERS={'add':('add',2),'sub':('sub',2),'mul':('mul',2),'eq':('eq',2),
 'lt':('lt',2),'le':('le',2),'not':('logical_not',1),
 'text.bytes':('text_bytes',1),'text.byte_at':('text_byte_at',2),
 'text.eq':('text_eq',2),'text.lt':('text_lt',2),
 'list.len':('list_len',1),'list.at':('list_at',2),'list.push':('list_push',2),
 'list.contains':('list_contains',2),'list.unique':('list_unique',1),
 'records.len':('records_len',1),'records.at':('records_at',2),'records.push':('records_push',2),
 'json.kind':('json_kind',1),'json.len':('json_len',1),'json.int':('json_int',1),
 'json.at':('json_at',2),'none.int':('none_int',0),'some.int':('some_int',1)}


class _Lowering:
    def __init__(self,program):
        need(type(program) is dict and program.get('schema')=='bagaev-typed-record/11')
        self.program=program
        functions=program.get('functions');need(type(functions) is dict and 1<=len(functions)<=32)
        self.roots={name:i for i,name in enumerate(sorted(functions))}
        need(program.get('entry') in self.roots)
        self.next=len(self.roots);self.count=0;self.code={}
        entry=functions[program['entry']]
        need(type(entry['params']) is list and len(entry['params'])<=8
             and all(type(p) is list and len(p)==2 and p[1]=='Json' for p in entry['params']))

    def node(self,expr,pointer,depth=1,number=None):
        self.count+=1;need(self.count<=2048 and depth<=32)
        need(type(expr) is list and expr and type(expr[0]) is str)
        if number is None:number=self.next;self.next+=1
        op=expr[0]
        lines=[f'def _n{number}(_env, _args, _budget, _layout):',
               f'    _f = Frame(_budget, {pointer!r}, _layout)',
               '    if False: yield None']
        def emit(text,indent=1):lines.append('    '*indent+text)
        def child(value,index,target,indent=1,env='_env'):
            n=self.node(value,pointer+'/'+str(index),depth+1)
            emit(f'{target} = yield (_n{n}, {env}, _args)',indent)
        def operands(start=1):
            variables=[]
            for i,value in enumerate(expr[start:],start):
                variable='_v'+str(i);child(value,i,variable);variables.append(variable)
            return variables
        def tuple_code(values):return '('+','.join(values)+(',' if values else '')+')'
        if op in ('int','bool','text'):
            need(len(expr)==2);emit(f'return _f.{op}_literal({expr[1]!r})')
        elif op in ('arg','use'):
            need(len(expr)==2 and type(expr[1]) is str)
            container='_args' if op=='arg' else '_env';emit(f'return {container}[{expr[1]!r}]')
        elif op in HELPERS:
            method,arity=HELPERS[op];need(len(expr)==arity+1)
            values=operands();emit(f'return _f.{method}('+', '.join(values)+')')
        elif op=='list.text':
            need(len(expr)<=65);values=operands();emit('return _f.list_text('+tuple_code(values)+')')
        elif op in ('record','records.list'):
            need(len(expr)>=2 and type(expr[1]) is str)
            values=operands(2);method='record' if op=='record' else 'records_list'
            emit(f'return _f.{method}({expr[1]!r}, '+tuple_code(values)+')')
        elif op in ('field','json.field'):
            need(len(expr)==3 and type(expr[2]) is str);child(expr[1],1,'_value')
            method='field' if op=='field' else 'json_field';emit(f'return _f.{method}(_value, {expr[2]!r})')
        elif op=='variant':
            need(len(expr)==4 and type(expr[1]) is str and type(expr[2]) is str)
            child(expr[3],3,'_value');emit(f'return _f.variant({expr[1]!r}, {expr[2]!r}, _value)')
        elif op=='call':
            need(len(expr)>=2 and type(expr[1]) is str and expr[1] in self.roots)
            params=self.program['functions'][expr[1]]['params'];need(len(expr)==len(params)+2)
            values=operands(2);pairs=', '.join(repr(p[0])+': '+v for p,v in zip(params,values))
            emit(f'_value = yield (_n{self.roots[expr[1]]}, {{}}, {{{pairs}}})');emit('return _value')
        elif op=='let':
            need(len(expr)==4 and type(expr[1]) is str);child(expr[2],2,'_value')
            emit('_local = dict(_env)');emit(f'_local[{expr[1]!r}] = _value')
            child(expr[3],3,'_answer',env='_local');emit('return _answer')
        elif op=='if':
            need(len(expr)==4);child(expr[1],1,'_condition');emit('need(type(_condition) is bool)')
            emit('if _condition:');child(expr[2],2,'_answer',2)
            emit('else:');child(expr[3],3,'_answer',2);emit('return _answer')
        elif op in ('option.or','json.text_or'):
            need(len(expr)==3);child(expr[1],1,'_selected')
            if op=='option.or':emit('need(type(_selected) is Option)');emit('_available = _selected.value')
            else:emit('_available = _f.json_text(_selected)')
            emit('if _available is not None:');emit('return _available',2)
            child(expr[2],2,'_fallback');emit('return _fallback')
        elif op=='loop':
            need(len(expr)==6 and type(expr[1]) is int and 0<=expr[1]<=1024
                 and type(expr[2]) is str and type(expr[3]) is str)
            child(expr[4],4,'_value');emit(f'for _index in range({expr[1]}):')
            emit('_local = dict(_env)',2);emit(f'_local[{expr[2]!r}] = _index',2)
            emit(f'_local[{expr[3]!r}] = _value',2)
            child(expr[5],5,'_value',2,env='_local');emit('return _value')
        elif op=='match':
            need(len(expr)==3 and type(expr[2]) is list and 1<=len(expr[2])<=8)
            child(expr[1],1,'_choice')
            emit('need(type(_choice) is _Variant and _layout.valid(_choice, _choice.name))')
            for i,arm in enumerate(expr[2]):
                need(type(arm) is list and len(arm)==3 and type(arm[0]) is str and type(arm[1]) is str)
                emit(('if' if i==0 else 'elif')+f' _choice.tag == {arm[0]!r}:')
                emit('_local = dict(_env)',2);emit(f'_local[{arm[1]!r}] = _choice.value',2)
                child(arm[2],f'2/{i}/2','_answer',2,env='_local');emit('return _answer',2)
            emit('raise RuntimeAPIError()')
        else:raise LoweringError()
        self.code[number]='\n'.join(lines)
        return number

    def source(self,json_source,runtime_source):
        need(type(json_source) is bytes and type(runtime_source) is bytes)
        line=b'from bagaev_record_json_view import View, JsonInputError\n'
        need(runtime_source.count(line)==1)
        runtime_source=runtime_source.replace(line,b'',1)
        for name,index in self.roots.items():
            self.node(self.program['functions'][name]['body'],'/program/functions/'+name+'/body',number=index)
        need(len(self.code)==self.next)
        declarations={k:self.program[k] for k in ('schema','records','lists','variants')}
        declarations=json.loads(canonical(declarations))
        source_raw=canonical(self.program);values,depth=metrics(self.program)
        params=tuple(p[0] for p in self.program['functions'][self.program['entry']]['params'])
        replacements={'__DECLARATIONS__':repr(declarations),'__SOURCE_BYTES__':str(len(source_raw)),
                      '__SOURCE_VALUES__':str(values),'__SOURCE_DEPTH__':str(depth),
                      '__PARAMETERS__':repr(params),'__ROOT__':'_n'+str(self.roots[self.program['entry']])}
        # Substitute the template once; never rescan inserted identifier data.
        footer=re.sub(r'__(?:DECLARATIONS|SOURCE_BYTES|SOURCE_VALUES|SOURCE_DEPTH|PARAMETERS|ROOT)__',
                      lambda match:replacements[match.group(0)],_FOOTER)
        result=(json_source.decode('utf-8')+'\n\n'+runtime_source.decode('utf-8')+'\n\n'
                +'\n\n'.join(self.code[i] for i in sorted(self.code))+'\n\n'+footer).encode('utf-8')
        if len(result)>1048576:raise LoweringError('CPY_ARTIFACT_BOUNDS')
        return result


_FOOTER='''class CPythonPreparationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

_LAYOUT = Layout(__DECLARATIONS__)
_SOURCE_BYTES = __SOURCE_BYTES__
_SOURCE_VALUES = __SOURCE_VALUES__
_SOURCE_DEPTH = __SOURCE_DEPTH__
_PARAMETERS = __PARAMETERS__

def _prepare(arguments_raw):
    if type(arguments_raw) is not bytes:
        raise CPythonPreparationError('CPY_ARGUMENTS_INPUT')
    if 70 + _SOURCE_BYTES + len(arguments_raw) > 1048576:
        raise CPythonPreparationError('CPY_FRAME_BOUNDS')
    try:
        viewed = parse(arguments_raw)
    except JsonInputError as error:
        codes = {'JP_INPUT':'CPY_ARGUMENTS_INPUT','JP_BOUNDS':'CPY_ARGUMENTS_BOUNDS','JP_FORMAT':'CPY_ARGUMENTS_FORMAT'}
        raise CPythonPreparationError(codes[error.code]) from None
    value = json.loads(arguments_raw.decode('utf-8'), parse_int=lambda _:None, parse_float=lambda _:None)
    count = depth = 0
    pending = [(value, 1)]
    while pending:
        item, level = pending.pop()
        count += 1
        depth = max(depth, level)
        if type(item) is list: pending.extend((v,level+1) for v in item)
        elif type(item) is dict: pending.extend((v,level+1) for v in item.values())
    if _SOURCE_VALUES + count + 2 > 16384 or 1 + max(_SOURCE_DEPTH,depth,1) > 132:
        raise CPythonPreparationError('CPY_ARGUMENTS_BOUNDS')
    if viewed.kind() != 'array' or viewed.length() != len(_PARAMETERS):
        raise CPythonPreparationError('CPY_ARGUMENTS_ARITY')
    return tuple(viewed.at(i) for i in range(len(_PARAMETERS)))

def _drive(function, arguments, budget):
    stack = [function({}, arguments, budget, _LAYOUT)]
    answer = None
    while stack:
        try:
            function, environment, arguments = stack[-1].send(answer)
            answer = None
            stack.append(function(environment, arguments, budget, _LAYOUT))
        except StopIteration as done:
            stack.pop()
            answer = done.value
    return answer

def evaluate(arguments_raw):
    arguments = _prepare(arguments_raw)
    budget = Budget()
    try:
        value = _drive(__ROOT__, dict(zip(_PARAMETERS,arguments)), budget)
    except RuntimeRefusal as error:
        return serialize_refusal(error,budget.work)
    return serialize_success(value,_LAYOUT,budget.work)
'''


def lower_checked(program,json_source,runtime_source):
    """Internal data lowering; callers must supply actual checked preparation."""
    return _Lowering(program).source(json_source,runtime_source)
