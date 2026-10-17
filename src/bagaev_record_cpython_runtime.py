"""Typed-record value/work helpers; no AST interpretation or execution authority."""
import json
import re
from dataclasses import dataclass, field
from types import MappingProxyType
from bagaev_record_json_view import View, JsonInputError

OUTPUT_LIMIT = 8 * 1048576
NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,31}\Z')
POINTER = re.compile(r'/program/functions/[A-Za-z][A-Za-z0-9_.-]{0,63}/body(?:/(?:0|[1-9][0-9]*))*\Z')
PRIMITIVES = frozenset(('Int64','Bool','Text','OptionInt64','TextList'))
STATUSES = {'RR_WORK':'work-limit','RR_OVERFLOW':'integer-overflow','RR_INDEX':'list-index',
            'RR_LIST_ITEMS':'list-bound','RR_LIST_BYTES':'list-bound','RR_RECORD_LIST_ITEMS':'record-list-bound'}


class RuntimeAPIError(ValueError):
    def __init__(self, code='VALUE_API'):
        self.code = code
        super().__init__(code)


def need(ok):
    if not ok:
        raise RuntimeAPIError()


def integer(v):
    return type(v) is int and -(1 << 63) <= v < (1 << 63)


def text(v):
    if type(v) is not str or len(v) > 256:
        return False
    try:
        return len(v.encode('utf-8')) <= 1024
    except UnicodeError:
        return False


def location(v):
    need(type(v) is str and len(v) <= 4096 and POINTER.fullmatch(v) is not None)


class RuntimeRefusal(ValueError):
    def __init__(self, status, reason, where):
        need(type(reason) is str and reason in STATUSES and type(status) is str and STATUSES[reason] == status)
        location(where)
        self.status, self.reason, self.location = status, reason, where
        super().__init__(reason)


class Budget:
    __slots__ = ('__work',)
    def __init__(self):
        self.__work = 0
    @property
    def work(self):
        return self.__work
    def charge(self, amount, where):
        need(type(amount) is int and amount >= 0)
        location(where)
        if amount > 65536 - self.__work:
            raise RuntimeRefusal('work-limit','RR_WORK',where)
        self.__work += amount


@dataclass(frozen=True)
class Option:
    value: object
    def __post_init__(self):
        need(self.value is None or integer(self.value))


@dataclass(frozen=True)
class TextList:
    items: tuple
    byte_count: int = field(init=False)
    def __post_init__(self):
        need(type(self.items) is tuple and len(self.items) <= 64 and all(text(v) for v in self.items))
        size = sum(len(v.encode('utf-8')) for v in self.items)
        need(size <= 4096)
        object.__setattr__(self,'byte_count',size)


@dataclass(frozen=True, eq=False)
class Layout:
    records: object
    lists: object
    variants: object
    def __init__(self, declarations):
        need(type(declarations) is dict and set(declarations) == {'schema','records','lists','variants'})
        need(type(declarations['schema']) is str and declarations['schema'] == 'bagaev-typed-record/11')
        maps = [declarations[k] for k in ('records','lists','variants')]
        need(all(type(m) is dict for m in maps))
        names = [n for m in maps for n in m]
        need(len(names) <= 8 and len(set(names)) == len(names))
        need(all(type(n) is str and NAME.fullmatch(n) and n not in PRIMITIVES | {'Json'} for n in names))
        def target(v):
            need(type(v) is str and v in PRIMITIVES | set(names))
            return v
        records, lists, variants = {}, {}, {}
        for name, fields in sorted(maps[0].items()):
            need(type(fields) is dict and len(fields) <= 8)
            rows = []
            need(all(type(k) is str and NAME.fullmatch(k) for k in fields))
            for key, value in sorted(fields.items()):
                omit = type(value) is dict
                if omit:
                    need(set(value) == {'type','omit_none'} and type(value['type']) is str
                         and value['type'] == 'OptionInt64' and value['omit_none'] is True)
                    value = 'OptionInt64'
                rows.append((key,target(value),omit))
            records[name] = tuple(rows)
        for name, value in sorted(maps[1].items()):
            need(type(value) is dict and set(value) == {'element','capacity'})
            need(type(value['element']) is str and value['element'] in records)
            need(type(value['capacity']) is int and 0 <= value['capacity'] <= 16)
            lists[name] = (value['element'],value['capacity'])
        for name, fields in sorted(maps[2].items()):
            need(type(fields) is dict and 1 <= len(fields) <= 8)
            need(all(type(k) is str and NAME.fullmatch(k) for k in fields))
            variants[name] = tuple((k,target(v)) for k,v in sorted(fields.items()))
        visiting, units = set(), {}
        def count(name):
            if name in PRIMITIVES:
                return 65 if name == 'TextList' else 1
            need(name not in visiting)
            if name in units:
                return units[name]
            visiting.add(name)
            if name in records:
                n = 1 + sum(count(t) for _,t,_ in records[name])
            elif name in lists:
                element, capacity = lists[name]
                n = 1 + capacity * count(element)
            else:
                n = 1 + max(count(t) for _,t in variants[name])
            visiting.remove(name)
            need(n <= 4096)
            units[name] = n
            return n
        for name in names:
            count(name)
        object.__setattr__(self,'records',MappingProxyType(records))
        object.__setattr__(self,'lists',MappingProxyType(lists))
        object.__setattr__(self,'variants',MappingProxyType(variants))

    def valid(self, value, target):
        if type(target) is not str: return False
        if target == 'Int64': return integer(value)
        if target == 'Bool': return type(value) is bool
        if target == 'Text': return text(value)
        if target == 'OptionInt64': return type(value) is Option and (value.value is None or integer(value.value))
        if target == 'TextList':
            return (type(value) is TextList and type(value.items) is tuple and len(value.items) <= 64
                    and all(text(x) for x in value.items)
                    and type(value.byte_count) is int
                    and value.byte_count == sum(len(x.encode('utf-8')) for x in value.items) <= 4096)
        if target in self.records:
            rows = self.records[target]
            return (type(value) is _Record and value.layout is self and value.name == target
                    and type(value.items) is tuple and len(value.items) == len(rows)
                    and all(self.valid(v,t) for v,(_,t,_) in zip(value.items,rows)))
        if target in self.lists:
            element, cap = self.lists[target]
            return (type(value) is _RecordList and value.layout is self and value.name == target
                    and type(value.items) is tuple and len(value.items) <= cap
                    and all(self.valid(v,element) for v in value.items))
        if target in self.variants:
            if type(value) is not _Variant or value.layout is not self or value.name != target:
                return False
            options = dict(self.variants[target])
            return type(value.tag) is str and value.tag in options and self.valid(value.value,options[value.tag])
        return False


@dataclass(frozen=True)
class _Record:
    layout: Layout
    name: str
    items: tuple


@dataclass(frozen=True)
class _RecordList:
    layout: Layout
    name: str
    items: tuple


@dataclass(frozen=True)
class _Variant:
    layout: Layout
    name: str
    tag: str
    value: object


class Frame:
    def __init__(self,budget,where,layout):
        need(type(budget) is Budget and type(layout) is Layout)
        location(where)
        self.budget,self.location,self.layout = budget,where,layout
        budget.charge(1,where)
    def charge(self,n): self.budget.charge(n,self.location)
    def fail(self,reason): raise RuntimeRefusal(STATUSES[reason],reason,self.location)
    def int_literal(self,n): need(integer(n)); return n
    def bool_literal(self,b): need(type(b) is bool); return b
    def text_literal(self,s): need(text(s)); self.charge(len(s.encode('utf-8'))); return s
    def _binary(self,a,b,op):
        need(integer(a) and integer(b))
        result = {'add':lambda:a+b,'sub':lambda:a-b,'mul':lambda:a*b}[op]()
        if not integer(result): self.fail('RR_OVERFLOW')
        return result
    def add(self,a,b): return self._binary(a,b,'add')
    def sub(self,a,b): return self._binary(a,b,'sub')
    def mul(self,a,b): return self._binary(a,b,'mul')
    def eq(self,a,b): need(type(a) is type(b) and (integer(a) and integer(b) or type(a) is bool)); return a == b
    def lt(self,a,b): need(integer(a) and integer(b)); return a < b
    def le(self,a,b): need(integer(a) and integer(b)); return a <= b
    def logical_not(self,b): need(type(b) is bool); return not b
    def text_eq(self,a,b):
        need(text(a) and text(b)); self.charge(len(a.encode())+len(b.encode())); return a == b
    def text_lt(self,a,b):
        need(text(a) and text(b)); self.charge(len(a.encode())+len(b.encode())); return a.encode() < b.encode()
    def text_bytes(self,s): need(text(s)); return len(s.encode())
    def text_byte_at(self,s,i):
        need(text(s) and integer(i)); raw=s.encode(); return Option(raw[i] if 0 <= i < len(raw) else None)
    def _list(self,x): need(self.layout.valid(x,'TextList'))
    def list_text(self,items):
        need(type(items) is tuple and len(items) <= 64 and all(text(x) for x in items))
        if sum(len(x.encode()) for x in items) > 4096: self.fail('RR_LIST_BYTES')
        return TextList(items)
    def list_push(self,x,s):
        self._list(x); need(text(s)); n=len(x.items)+1; self.charge(n)
        if n > 64: self.fail('RR_LIST_ITEMS')
        if x.byte_count + len(s.encode()) > 4096: self.fail('RR_LIST_BYTES')
        return TextList(x.items+(s,))
    def list_len(self,x): self._list(x); return len(x.items)
    def list_at(self,x,i):
        self._list(x); need(integer(i))
        if not 0 <= i < len(x.items): self.fail('RR_INDEX')
        return x.items[i]
    def list_contains(self,x,s):
        self._list(x); need(text(s)); n=len(x.items); self.charge(n+x.byte_count+n*len(s.encode())); return s in x.items
    def list_unique(self,x):
        self._list(x); n=len(x.items); self.charge(n*n+2*n*x.byte_count)
        return TextList(tuple(sorted(set(x.items),key=lambda s:s.encode())))
    def none_int(self): return Option(None)
    def some_int(self,n): need(integer(n)); return Option(n)
    def record(self,name,items):
        need(type(name) is str and name in self.layout.records and type(items) is tuple)
        value=_Record(self.layout,name,items); need(self.layout.valid(value,name)); return value
    def field(self,value,name):
        need(type(value) is _Record and type(name) is str and self.layout.valid(value,value.name))
        fields=[key for key,_,_ in self.layout.records[value.name]]; need(name in fields)
        return value.items[fields.index(name)]
    def records_list(self,name,items):
        need(type(name) is str and name in self.layout.lists and type(items) is tuple)
        value=_RecordList(self.layout,name,items); need(self.layout.valid(value,name)); return value
    def _records(self,x): need(type(x) is _RecordList and self.layout.valid(x,x.name))
    def records_push(self,x,value):
        self._records(x); element,cap=self.layout.lists[x.name]; need(self.layout.valid(value,element))
        n=len(x.items)+1; self.charge(n)
        if n > cap: self.fail('RR_RECORD_LIST_ITEMS')
        return _RecordList(self.layout,x.name,x.items+(value,))
    def records_len(self,x): self._records(x); return len(x.items)
    def records_at(self,x,i):
        self._records(x); need(integer(i))
        if not 0 <= i < len(x.items): self.fail('RR_INDEX')
        return x.items[i]
    def variant(self,name,tag,value):
        need(type(name) is str and name in self.layout.variants and type(tag) is str)
        result=_Variant(self.layout,name,tag,value); need(self.layout.valid(result,name)); return result
    def _json(self,v): need(type(v) is View)
    def json_kind(self,v): self._json(v); return v.kind()
    def json_len(self,v): self._json(v); return Option(v.length())
    def json_int(self,v): self._json(v); self.charge(v.int_charge()); return Option(v.integer())
    def json_field(self,v,key):
        self._json(v)
        try: amount=v.field_charge(key)
        except JsonInputError: raise RuntimeAPIError() from None
        self.charge(amount)
        return v.field(key)
    def json_at(self,v,i):
        self._json(v)
        try: return v.at(i)
        except JsonInputError: raise RuntimeAPIError() from None
    def json_text(self,v):
        self._json(v); result=v.text()
        if result is not None: self.charge(len(result.encode()))
        return result


def _render(value,layout):
    if type(value) is bool: return value,'Bool'
    if integer(value): return value,'Int64'
    if text(value): return value,'Text'
    if type(value) is Option and layout.valid(value,'OptionInt64'): return value.value,'OptionInt64'
    if type(value) is TextList and layout.valid(value,'TextList'): return list(value.items),'TextList'
    if type(value) in (_Record,_RecordList,_Variant):
        need(layout.valid(value,value.name))
        if type(value) is _Record:
            result={}
            for child,(name,_,omit) in zip(value.items,layout.records[value.name]):
                if omit and type(child) is Option and child.value is None: continue
                result[name]=_render(child,layout)[0]
            return result,'Record:'+value.name
        if type(value) is _RecordList:
            return [_render(child,layout)[0] for child in value.items],'RecordList:'+value.name
        return {'case':value.tag,'value':_render(value.value,layout)[0]},'Variant:'+value.name
    raise RuntimeAPIError()


def _wire(status,reason,where,value,label,work):
    need(type(work) is int and 1 <= work <= 65536)
    result={'location':where,'reason':reason,'schema':'bagaev-typed-record-result/11',
            'status':status,'value':value,'value_type':label,'work':work}
    pieces=[];size=1
    for piece in json.JSONEncoder(ensure_ascii=False,allow_nan=False,separators=(',',':')).iterencode(result):
        raw=piece.encode('utf-8'); size+=len(raw)
        if size > OUTPUT_LIMIT: raise RuntimeAPIError('VALUE_OUTPUT_BOUNDS')
        pieces.append(raw)
    return b''.join(pieces)+b'\n'


def serialize_success(value,layout,work):
    need(type(layout) is Layout and type(work) is int and 1 <= work <= 65536)
    rendered,label=_render(value,layout)
    return _wire('success',None,None,rendered,label,work)


def serialize_refusal(error,work):
    need(type(error) is RuntimeRefusal)
    checked=RuntimeRefusal(error.status,error.reason,error.location)
    return _wire(checked.status,checked.reason,checked.location,None,None,work)
