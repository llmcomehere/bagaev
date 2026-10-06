"""Outer framing/context only. Not semantic validation, authentication or execution authority."""
from dataclasses import dataclass,field
import hashlib,struct
MAX_PAYLOAD=4325440
class Refusal(ValueError):
 def __init__(self,code):self.code=code;super().__init__(code)
def refuse(code):raise Refusal(code)
@dataclass(frozen=True,slots=True)
class Context:
 profile:int
 source:bytes
 artifact:bytes
 invocation:bytes
 def __post_init__(self):
  if type(self.profile)is not int or self.profile not in(8,9,10):refuse('CONTEXT_INPUT')
  if any(type(x)is not bytes or len(x)!=32 for x in(self.source,self.artifact,self.invocation)):refuse('CONTEXT_INPUT')
@dataclass(frozen=True,slots=True)
class FramedPayload:
 context:Context
 payload:bytes
 kind:int
 semantic_validated:bool=field(default=False,init=False)
 authenticated:bool=field(default=False,init=False)
 execution_authority:bool=field(default=False,init=False)
def check_context(c):
 if type(c)is not Context:refuse('CONTEXT_INPUT')
 c.__post_init__()
def native_framing(c,payload,kind):
 if kind==1:
  if len(payload)!=32:refuse('NATIVE_FAILURE')
  status,ty,value,work,reason,location=struct.unpack('<IIqQII',payload)
  pairs={(1,9),(2,10),(4,11),(5,12)}
  if c.profile>=9:pairs.add((7,14))
  if c.profile>=10:pairs.add((8,15))
  if (status,reason)not in pairs or ty!=0 or value!=0 or work>65536 or not 1<=location<=2048:refuse('NATIVE_FAILURE')
 else:
  if len(payload)<96:refuse('NATIVE_FRAME')
  if payload[:8]!=f'BCMPRES{c.profile-7}'.encode():refuse('NATIVE_VERSION')
  nodes,text,work=struct.unpack_from('<IIQ',payload,8)
  if not 1<=nodes<=4096 or text>4194304 or work>65536 or len(payload)!=64+32*nodes+text or payload[56:64]!=bytes(8):refuse('NATIVE_FRAME')
  if payload[24:56]!=c.source:refuse('NATIVE_SOURCE')
  # Node/type/semantic checking is intentionally left to the typed reader.
def pack(c,payload):
 check_context(c)
 if type(payload)is not bytes:refuse('FRAME_INPUT')
 if len(payload)>MAX_PAYLOAD:refuse('FRAME_BOUNDS')
 kind=1 if len(payload)==32 else 0;native_framing(c,payload,kind)
 return b'BOUTCTX1'+struct.pack('<HHI',c.profile,1,0)+c.source+c.artifact+c.invocation+struct.pack('<II',len(payload),kind)+bytes(8)+hashlib.sha256(payload).digest()+payload
def unpack(blob,expected):
 check_context(expected)
 if type(blob)is not bytes:refuse('FRAME_INPUT')
 if not 160<=len(blob)<=160+MAX_PAYLOAD:refuse('FRAME_BOUNDS')
 if blob[:8]!=b'BOUTCTX1':refuse('MAGIC')
 profile,method,flags=struct.unpack_from('<HHI',blob,8)
 if profile not in(8,9,10):refuse('PROFILE')
 if method!=1:refuse('METHOD')
 if flags or blob[120:128]!=bytes(8):refuse('RESERVED')
 length,kind=struct.unpack_from('<II',blob,112)
 if length!=len(blob)-160 or length>MAX_PAYLOAD:refuse('LENGTH')
 if kind not in(0,1):refuse('KIND')
 if profile!=expected.profile:refuse('CONTEXT_PROFILE')
 for offset,name in [(16,'source'),(48,'artifact'),(80,'invocation')]:
  if blob[offset:offset+32]!=getattr(expected,name):refuse('CONTEXT_'+name.upper())
 payload=blob[160:]
 if hashlib.sha256(payload).digest()!=blob[128:160]:refuse('PAYLOAD_HASH')
 native_framing(expected,payload,kind)
 return FramedPayload(expected,payload,kind)
