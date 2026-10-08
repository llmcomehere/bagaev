//! Data-only validation of owned composite bytes against an admitted type graph.
use crate::{type_graph::{self,Definition,Ref},record_value::Kind,text_value::Text};
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct Refusal{pub reason:&'static str,pub index:usize}
fn bad(reason:&'static str,index:usize)->Refusal{Refusal{reason,index}}
fn word(b:&[u8],at:usize)->usize{u32::from_le_bytes(b[at..at+4].try_into().expect("bounded word")) as usize}
pub struct Checked<'a>{wire:&'a[u8],nodes:usize,work:u64}
impl Checked<'_>{pub fn bytes(&self)->&[u8]{self.wire}pub fn node_count(&self)->usize{self.nodes}pub fn work(&self)->u64{self.work}}
struct Decoder<'a>{wire:&'a[u8],nodes:usize,pool:usize,pool_len:usize,used:usize}
impl Decoder<'_>{
 fn node(&mut self,defs:&[Definition<'_>],expected:Ref,i:usize)->Result<usize,Refusal>{
  if i>=self.nodes{return Err(bad("WIRE_SHAPE",i));}
  let p=64+32*i;let tag=word(self.wire,p);let nominal=word(self.wire,p+4);let scalar=i64::from_le_bytes(self.wire[p+8..p+16].try_into().expect("bounded scalar"));
  let end=word(self.wire,p+16);let count=word(self.wire,p+20);let offset=word(self.wire,p+24);let len=word(self.wire,p+28);
  let type_ok=match expected{Ref::Primitive(k)=>nominal==0&&match k{Kind::Int64=>tag==1,Kind::Bool=>tag==2,Kind::Text=>tag==3,Kind::OptionInt64=>tag==4||tag==9,Kind::TextList=>tag==5,Kind::IntProjection=>(10..=12).contains(&tag)},Ref::Named(n)=>nominal==usize::from(n)&&match defs[usize::from(n)]{Definition::Product(_)=>tag==6,Definition::List{..}=>tag==7,Definition::Sum(_)=>tag==8}};
  if !type_ok{return Err(bad("WIRE_TYPE",i));}
  if end<=i||end>self.nodes||tag!=3&&(offset!=0||len!=0){return Err(bad("WIRE_SHAPE",i));}
  let mut next=i+1;
  match expected{
   Ref::Primitive(Kind::Text)=>{
    if count!=0||scalar!=0{return Err(bad("WIRE_SHAPE",i));}
    if offset!=self.used||len>self.pool_len-self.used{return Err(bad("WIRE_TEXT",i));}
    Text::from_bytes(&self.wire[self.pool+offset..self.pool+offset+len]).map_err(|_|bad("WIRE_TEXT",i))?;self.used+=len;
   },
   Ref::Primitive(Kind::TextList)=>{
    if count>64||scalar!=0{return Err(bad("WIRE_SHAPE",i));}let before=self.used;
    for _ in 0..count{next=self.node(defs,Ref::Primitive(Kind::Text),next)?;}
    if self.used-before>4096{return Err(bad("WIRE_SHAPE",i));}
   },
   Ref::Primitive(k)=>{
    if count!=0{return Err(bad("WIRE_SHAPE",i));}
    if matches!(k,Kind::Bool)&&scalar!=0&&scalar!=1{return Err(bad("WIRE_VALUE",i));}
    if matches!(tag,4|10|11)&&scalar!=0{return Err(bad("WIRE_SHAPE",i));}
   },
   Ref::Named(n)=>match &defs[usize::from(n)]{
    Definition::Product(fields)=>{
     if count!=fields.len()||scalar!=0{return Err(bad("WIRE_SHAPE",i));}
     for &field in *fields{next=self.node(defs,field,next)?;}
    },
    Definition::List{element,capacity}=>{
     if count>usize::from(*capacity)||scalar!=0{return Err(bad("WIRE_SHAPE",i));}
     for _ in 0..count{next=self.node(defs,*element,next)?;}
    },
    Definition::Sum(alts)=>{
     if count!=1{return Err(bad("WIRE_SHAPE",i));}
     if scalar<0||scalar as u64>=alts.len() as u64{return Err(bad("WIRE_VALUE",i));}
     next=self.node(defs,alts[scalar as usize],next)?;
    },
   }
  }
  if next!=end{return Err(bad("WIRE_SHAPE",i));}Ok(next)
 }
}
pub fn decode<'a>(defs:&[Definition<'_>],entry:Ref,wire:&'a[u8],binding:&[u8;32])->Result<Checked<'a>,Refusal>{
 type_graph::check_wide(defs,entry).map_err(|e|bad(e.reason,e.index))?;
 if wire.len()<64{return Err(bad("WIRE_SIZE",wire.len()));}
 if &wire[..8]!=b"BCMPRES4"{return Err(bad("WIRE_MAGIC",0));}
 let nodes=word(wire,8);if !(1..=4096).contains(&nodes){return Err(bad("WIRE_COUNT",8));}
 let bytes=word(wire,12);if bytes>4194304{return Err(bad("WIRE_BYTES",12));}
 let pool=64+32*nodes;if wire.len()!=pool+bytes{return Err(bad("WIRE_SIZE",wire.len()));}
 let work=u64::from_le_bytes(wire[16..24].try_into().expect("bounded work"));if work>65536{return Err(bad("WIRE_WORK",16));}
 if &wire[24..56]!=binding{return Err(bad("WIRE_BINDING",24));}
 if let Some(i)=wire[56..64].iter().position(|&x|x!=0){return Err(bad("WIRE_RESERVED",56+i));}
 let mut decoder=Decoder{wire,nodes,pool,pool_len:bytes,used:0};let next=decoder.node(defs,entry,0)?;
 if next!=nodes{return Err(bad("WIRE_UNUSED",next));}
 if decoder.used!=bytes{return Err(bad("WIRE_TEXT_UNUSED",decoder.used));}
 Ok(Checked{wire,nodes,work})
}
