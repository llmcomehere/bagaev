"""Synthetic outer-framing controls. No native execution or evidence promotion."""
from pathlib import Path
import json,importlib.util,sys,types
ROOT=Path(__file__).resolve().parents[2]
def context(api,x):return api.Context(x['profile'],bytes.fromhex(x['source']),bytes.fromhex(x['artifact']),bytes.fromhex(x['invocation']))
def main():
 d=ROOT/'examples/probes/outcome-context';spec=importlib.util.spec_from_file_location('outcome_context_codec',d/'codec.py');c=importlib.util.module_from_spec(spec);sys.modules[spec.name]=c;spec.loader.exec_module(c)
 cases=json.loads((d/'cases.json').read_text());assert len(cases)==40
 for case in cases:
  ctx=context(c,case['expected_context']);blob=bytes.fromhex(case['frame_hex'])
  try:
   v=c.unpack(blob,ctx);actual='ACCEPT_FRAMING_ONLY';assert not(v.semantic_validated or v.authenticated or v.execution_authority);assert c.pack(ctx,v.payload)==blob
  except c.Refusal as e:actual=e.code
  assert actual==case['expected'],(case['id'],actual)
 ctx=c.Context(8,bytes([8])*32,bytes([40])*32,bytes([72])*32)
 guards=[('FRAME_INPUT',lambda:c.unpack(bytearray(192),ctx)),('FRAME_BOUNDS',lambda:c.unpack(bytes(160+c.MAX_PAYLOAD+1),ctx)),('CONTEXT_INPUT',lambda:c.Context(True,bytes(32),bytes(32),bytes(32))),('CONTEXT_INPUT',lambda:c.Context(8,bytearray(32),bytes(32),bytes(32)))]
 for expected,fn in guards:
  try:fn()
  except c.Refusal as e:assert e.code==expected
  else:raise AssertionError('missing guard')
 original=(d/'codec.py').read_text();mutations=json.loads((d/'mutation-cases.json').read_text());assert len(mutations)==6
 for item in mutations:
  name=item['mutation']
  if name in ['source','artifact','invocation']:a="if blob[offset:offset+32]!=getattr(expected,name):";z=f"if name!='{name}' and blob[offset:offset+32]!=getattr(expected,name):"
  elif name=='hash':a="if hashlib.sha256(payload).digest()!=blob[128:160]:refuse('PAYLOAD_HASH')";z='# missing digest comparison control'
  elif name=='native-source':a="if payload[24:56]!=c.source:refuse('NATIVE_SOURCE')";z='# missing source comparison control'
  elif name=='profile':a="if profile!=expected.profile:refuse('CONTEXT_PROFILE')";z='# missing profile comparison control'
  else:raise AssertionError(name)
  assert original.count(a)==1;s=original.replace(a,z);api=types.ModuleType('ctx_mut_'+name.replace('-','_'));sys.modules[api.__name__]=api;exec(compile(s,api.__name__,'exec'),api.__dict__)
  case=item['case'];expected=context(c,case['expected_context'])
  try:c.unpack(bytes.fromhex(case['frame_hex']),expected)
  except c.Refusal as e:assert e.code==case['expected']
  else:raise AssertionError('witness must refuse in original')
  got=api.unpack(bytes.fromhex(case['frame_hex']),context(api,case['expected_context']));assert not(got.semantic_validated or got.authenticated or got.execution_authority)
 print(json.dumps({'status':'PASS','literal_cases':40,'api_guards':4,'normal_wrong_controls':6,'native_calls':0}))
if __name__=='__main__':main()
