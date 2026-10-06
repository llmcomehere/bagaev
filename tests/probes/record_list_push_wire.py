"""Data-only /10 fixtures and bounded result checks. Never compile or execute code."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def same(a,b):return json.dumps(a,sort_keys=True,ensure_ascii=True,separators=(',',':'))==json.dumps(b,sort_keys=True,ensure_ascii=True,separators=(',',':'))
def read(path,limit):
 if path.is_symlink() or not path.is_file():raise ValueError('input must be a regular file')
 with path.open('rb')as f:data=f.read(limit+1)
 if len(data)>limit:raise ValueError('input exceeds bound')
 return data

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['request','check-reference','check-native','harness']);parser.add_argument('case');parser.add_argument('--output',type=Path);parser.add_argument('--backend',type=Path);a=parser.parse_args()
 cases=json.loads(read(ROOT/'examples/probes/record-list-push/cases.json',1048576));case=next(c for c in cases if c['id']==a.case)
 if a.mode=='request':
  if a.output is not None or a.backend is not None:raise ValueError('request emits stdout only')
  print(json.dumps({'schema':f"bagaev-typed-record-invocation/{case['profile']}",'program':case['program'],'arguments':case['arguments']},ensure_ascii=True,separators=(',',':')));return
 if a.mode=='check-reference':
  if a.output is None or a.backend is not None:raise ValueError('check-reference requires only --output')
  if not same(json.loads(read(a.output,4325440)),case['expected']):raise ValueError('complete reference result mismatch')
  print(json.dumps({'case':a.case,'complete_reference':True}));return
 observations=json.loads(read(ROOT/'examples/probes/record-list-push/native-observations.json',1048576))['cases'];item=observations.get(a.case)
 if item is None:raise ValueError('case has no admitted native fixture')
 canonical=bytes.fromhex(item['canonical_source_hex']);binding=hashlib.sha256(canonical).digest()
 if binding.hex()!=item['source_sha256'] or not same(json.loads(canonical),case['program']):raise ValueError('source binding mismatch')
 expected=bytes.fromhex(item['expected_wire_hex'])
 if a.mode=='check-native':
  if a.output is None or a.backend is not None:raise ValueError('check-native requires only --output')
  if read(a.output,4325440)!=expected:raise ValueError('complete native wire mismatch')
  print(json.dumps({'case':a.case,'complete_native_wire':True,'measurement':False}));return
 if a.output is not None or a.backend is None:raise ValueError('harness requires only --backend and emits source data')
 backend=str(a.backend.resolve())
 if not re.fullmatch(r'/[A-Za-z0-9_./-]+',backend):raise ValueError('backend path requires the portable ASCII path form')
 e=case['expected'];status,reason=(0,0)if e['status']=='success'else {'RR_OVERFLOW':(1,9),'RR_RECORD_LIST_ITEMS':(8,15),'RR_LIST_ITEMS':(7,14),'RR_LIST_BYTES':(4,11),'RR_INDEX':(5,12),'RR_WORK':(2,10)}[e['reason']]
 arr=lambda x:'['+','.join(map(str,x))+']'
 values={'BACKEND':backend,'CANONICAL_BYTES':arr(canonical),'SOURCE_BINDING':arr(binding),'EXPECTED_PATH':json.dumps(e['location']or''),'STATUS':str(status),'REASON':str(reason),'WORK':str(e['work']),'EXPECTED_WIRE':arr(expected)}
 h=read(ROOT/'tests/probes/backend/record_list_push_native_harness.rs.in',131072).decode()
 for name,value in values.items():h=h.replace('{{'+name+'}}',value)
 if re.search(r'\{\{[A-Z_]+\}\}',h):raise ValueError('unexpanded harness placeholder')
 print(h,end='')
if __name__=='__main__':main()
