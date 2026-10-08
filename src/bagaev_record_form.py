"""Data-only readable record-form/1 over the existing typed-record/10 subset."""
import json,re
import bagaev_component_record_list_form as prior
old=prior.old
FormError=prior.FormError;need=prior.need;bounded=prior.bounded
TOKEN=prior.TOKEN;RESERVED=prior.RESERVED;INTRINSICS=prior.INTRINSICS
class Reader(prior.Reader):
 def __init__(self,source):
  need(type(source) in (str,bytes),'FORM_SYNTAX')
  try:raw=source.encode('utf8') if type(source)is str else source;text=raw.decode('utf8')
  except UnicodeError:raise FormError('FORM_SYNTAX') from None
  need(len(raw)<=old.BYTE_LIMIT,'FORM_BOUNDS');need(not text.startswith('\ufeff'))
  h=re.match(r'\A[ \t\r\n]*bagaev[ \t\r\n]+record-form/([A-Za-z0-9_]+)[ \t\r\n]*;',text);need(h is not None);need(h[1]=='1','FORM_VERSION');pos=h.end();self.tokens=[]
  while pos<len(text):
   if text[pos] in old.WS:pos+=1;continue
   m=TOKEN.match(text,pos);need(m is not None);self.tokens.append(m[0]);need(len(self.tokens)<=old.TOKEN_LIMIT,'FORM_BOUNDS');pos=m.end()
  self.pos=0;self.records={};self.functions={};self.variants={};self.clauses={};self.lists={}
 def read(self):
  self.take('program');self.take('{');entry=None
  while self.peek()!='}':
   kind=self.take()
   if kind in ('record','variant'):
    n=self.ident();need(n not in self.records and n not in self.variants and n not in self.lists,'FORM_DUPLICATE');fields=self.fields(self.ident);(self.records if kind=='record' else self.variants)[n]=fields
   elif kind=='list':
    n=self.ident();need(n not in self.records and n not in self.variants and n not in self.lists,'FORM_DUPLICATE');self.take('of');element=self.ident();self.take('capacity');token=self.take();need(re.fullmatch(r'[0-9]+',token) is not None);need(len(token)==1 and int(token)<=4,'FORM_BOUNDS');self.lists[n]={'element':element,'capacity':int(token)}
   elif kind=='fn':
    n=self.ident();need(n not in self.functions,'FORM_DUPLICATE');self.take('(');params=[]
    if self.peek()!=')':
     while True:
      p=self.ident();self.take(':');params.append([p,self.ident()])
      if self.peek()!=',':break
      self.take(',')
    self.take(')');self.take('->');result=self.ident();self.take('=');self.functions[n]={'params':params,'result':result,'body':self.expression()}
   elif kind=='entry':
    need(entry is None,'FORM_DUPLICATE');entry=self.ident()
   else:need(False)
   self.take(';')
  self.take('}');need(self.peek() is None);need(entry is not None,'FORM_SHAPE')
  for f in self.functions.values():f['body']=self.lower(f['body'])
  result={'schema':'bagaev-typed-record/10','records':self.records,'lists':self.lists,'variants':self.variants,'entry':entry,'functions':self.functions}
  bounded(result);return result
def decode(source):
 try:return Reader(source).read()
 except RecursionError:raise FormError('FORM_BOUNDS') from None
def encode(value):
 bounded(value)
 def shape(v,keys):need(type(v)is dict and set(v)==set(keys),'FORM_PROFILE')
 def ident(v):need(type(v)is str and old.IDENT.fullmatch(v) is not None and v not in RESERVED,'FORM_PROFILE');return v
 p=value;shape(p,['schema','records','lists','variants','entry','functions']);need(p['schema']=='bagaev-typed-record/10','FORM_PROFILE')
 need(all(type(p[k])is dict for k in ['records','lists','variants','functions']),'FORM_PROFILE');need(not(set(p['records'])&set(p['variants'])),'FORM_PROFILE')
 need(not(set(p['lists'])&(set(p['records'])|set(p['variants']))),'FORM_PROFILE')
 for name,d in p['lists'].items():
  ident(name);shape(d,['element','capacity']);ident(d['element']);need(type(d['capacity'])is int and 0<=d['capacity']<=4,'FORM_PROFILE')
 for defs in (p['records'],p['variants']):
  for n,fields in defs.items():
   ident(n);need(type(fields)is dict,'FORM_PROFILE')
   for k,v in fields.items():ident(k);ident(v)
 def expr(x):
  need(type(x)is list and x,'FORM_PROFILE');op=x[0];need(type(op)is str,'FORM_PROFILE')
  if op=='records.list':
   need(len(x)>=2,'FORM_PROFILE');name=ident(x[1]);need(name in p['lists'] and len(x)-2<=p['lists'][name]['capacity'],'FORM_PROFILE');return 'records.list('+name+('' if len(x)==2 else ', '+', '.join(expr(a) for a in x[2:]))+')'
  if op=='loop' and len(x)==6:
   need(type(x[1])is int and 0<=x[1]<=1024,'FORM_PROFILE');index=ident(x[2]);acc=ident(x[3]);need(index!=acc,'FORM_PROFILE');return 'fold ('+str(x[1])+', ('+expr(x[4])+')) with ('+index+', '+acc+') in ('+expr(x[5])+')'
  if op=='int' and len(x)==2:need(type(x[1])is int and -(1<<63)<=x[1]<(1<<63),'FORM_PROFILE');return str(x[1])
  if op=='bool' and len(x)==2:need(type(x[1])is bool,'FORM_PROFILE');return 'true' if x[1] else 'false'
  if op=='text' and len(x)==2:need(type(x[1])is str and not any(0xd800<=ord(c)<=0xdfff for c in x[1]),'FORM_PROFILE');return json.dumps(x[1],ensure_ascii=False)
  if op in ('arg','use') and len(x)==2:return ident(x[1])
  if op in ('add','sub','mul') and len(x)==3:return '('+expr(x[1])+' '+{'add':'+','sub':'-','mul':'*'}[op]+' '+expr(x[2])+')'
  if op in INTRINSICS:
   arity=INTRINSICS[op];need((len(x)-1<=64) if arity is None else len(x)==arity+1,'FORM_PROFILE');return op+'('+', '.join(expr(a) for a in x[1:])+')'
  if op=='match' and len(x)==3:
   need(type(x[2])is list,'FORM_PROFILE');arms=[]
   for arm in x[2]:
    need(type(arm)is list and len(arm)==3,'FORM_PROFILE');arms.append(ident(arm[0])+'('+ident(arm[1])+'): '+expr(arm[2])+';')
   return 'match ('+expr(x[1])+') { '+' '.join(arms)+' }'
  if op=='let' and len(x)==4:return 'let '+ident(x[1])+' = ('+expr(x[2])+') in ('+expr(x[3])+')'
  if op=='field' and len(x)==3:need(type(x[1])is list and x[1] and x[1][0] in ('arg','use','field'),'FORM_PROFILE');return expr(x[1])+'.'+ident(x[2])
  if op=='list.unique' and len(x)==2:return 'list.unique('+expr(x[1])+')'
  if op=='call' and len(x)>=2:return ident(x[1])+'('+', '.join(expr(a) for a in x[2:])+')'
  if op=='lt' and len(x)==3:return '('+expr(x[1])+' < '+expr(x[2])+')'
  if op=='if' and len(x)==4:return 'if ('+expr(x[1])+') then ('+expr(x[2])+') else ('+expr(x[3])+')'
  if op=='variant' and len(x)==4:
   n=ident(x[1]);alt=ident(x[2]);need(n+'.'+alt not in INTRINSICS,'FORM_PROFILE');need(n in p['variants'] and alt in p['variants'][n],'FORM_PROFILE');return n+'.'+alt+'('+expr(x[3])+')'
  if op=='record' and len(x)>=2:
   n=ident(x[1]);need(n in p['records'],'FORM_PROFILE');fields=sorted(p['records'][n]);need(len(x)==len(fields)+2,'FORM_PROFILE');return n+' { '+', '.join(k+': '+expr(a) for k,a in zip(fields,x[2:]))+' }'
  raise FormError('FORM_PROFILE')
 lines=['bagaev record-form/1;','program {']
 for kind,defs in [('record',p['records']),('variant',p['variants'])]:
  for n in sorted(defs):lines.append('  '+kind+' '+n+' { '+', '.join(k+': '+defs[n][k] for k in sorted(defs[n]))+' };')
 for name,d in sorted(p['lists'].items()):lines.append('  list '+name+' of '+d['element']+' capacity '+str(d['capacity'])+';')
 lines+=['','  entry '+ident(p['entry'])+';','']
 for n in sorted(p['functions']):
  f=p['functions'][n];shape(f,['params','result','body']);need(type(f['params'])is list,'FORM_PROFILE');params=[]
  for pair in f['params']:need(type(pair)is list and len(pair)==2,'FORM_PROFILE');params.append(ident(pair[0])+': '+ident(pair[1]))
  lines.append('  fn '+ident(n)+'('+', '.join(params)+') -> '+ident(f['result'])+' = '+expr(f['body'])+';')
 lines.append('}');out=('\n'.join(lines)+'\n').encode();need(len(out)<=old.BYTE_LIMIT,'FORM_BOUNDS');need(json.dumps(decode(out),sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)==json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False),'FORM_PROFILE');return out
