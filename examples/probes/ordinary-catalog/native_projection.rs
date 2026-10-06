//! Data-only lossless projection of one exact catalogue result graph. No authority.
use crate::{catalog::{Entry,State,Response},composite_result_decode_v10 as wire,type_graph::{Definition,Ref},record_value::Kind};
#[derive(Debug,Eq,PartialEq)]pub enum Error{Wire(wire::Refusal),Projection(&'static str)}
fn bad(s:&'static str)->Error{Error::Projection(s)}
struct Node{tag:u32,nominal:u32,scalar:i64,end:usize,count:usize,offset:usize,len:usize}
struct View<'a>{bytes:&'a[u8],nodes:usize,pool:usize}
impl View<'_>{
 fn node(&self,i:usize)->Result<Node,Error>{
  if i>=self.nodes{return Err(bad("NODE"))};let b=self.bytes.get(64+32*i..64+32*(i+1)).ok_or_else(||bad("NODE"))?;
  let u=|at|u32::from_le_bytes(b[at..at+4].try_into().unwrap());Ok(Node{tag:u(0),nominal:u(4),scalar:i64::from_le_bytes(b[8..16].try_into().unwrap()),end:u(16)as usize,count:u(20)as usize,offset:u(24)as usize,len:u(28)as usize})
 }
 fn record(&self,at:&mut usize,nominal:u32,count:usize)->Result<usize,Error>{let n=self.node(*at)?;if n.tag!=6||n.nominal!=nominal||n.count!=count{return Err(bad("RECORD"))};*at+=1;Ok(n.end)}
 fn text(&self,at:&mut usize)->Result<String,Error>{
  let n=self.node(*at)?;if n.tag!=3{return Err(bad("TEXT"))};let bytes=self.bytes.get(self.pool+n.offset..self.pool+n.offset+n.len).ok_or_else(||bad("TEXT"))?;let value=std::str::from_utf8(bytes).map_err(|_|bad("TEXT"))?.to_owned();*at=n.end;Ok(value)
 }
 fn texts(&self,at:&mut usize)->Result<Vec<String>,Error>{let n=self.node(*at)?;if n.tag!=5{return Err(bad("TEXTS"))};*at+=1;let mut out=Vec::with_capacity(n.count);for _ in 0..n.count{out.push(self.text(at)?)}if *at!=n.end{return Err(bad("TEXTS"))};Ok(out)}
 fn date(&self,at:&mut usize)->Result<Option<i64>,Error>{let n=self.node(*at)?;let v=match n.tag{4=>None,9=>Some(n.scalar),_=>return Err(bad("OPTION"))};*at=n.end;Ok(v)}
 fn entry(&self,at:&mut usize)->Result<Entry,Error>{
  let end=self.record(at,0,5)?;let date=self.date(at)?;let id=self.text(at)?;let indexed_tags=self.texts(at)?;let manual_tags=self.texts(at)?;let title=self.text(at)?;if *at!=end{return Err(bad("ENTRY"))};Ok(Entry{id,title,manual_tags,indexed_tags,date})
 }
 fn state(&self,at:&mut usize)->Result<State,Error>{
  let end=self.record(at,2,1)?;let list=self.node(*at)?;if list.tag!=7||list.nominal!=4{return Err(bad("ENTRIES"))};*at+=1;let mut entries=Vec::with_capacity(list.count);for _ in 0..list.count{entries.push(self.entry(at)?)}if *at!=list.end||*at!=end{return Err(bad("STATE"))};Ok(State{entries})
 }
}
fn reason(s:&str)->Result<&'static str,Error>{match s{"invalid-request"=>Ok("invalid-request"),"invalid-date"=>Ok("invalid-date"),"duplicate-entry-id"=>Ok("duplicate-entry-id"),"entry-order"=>Ok("entry-order"),"origin-collision"=>Ok("origin-collision"),"entry-not-found"=>Ok("entry-not-found"),_=>Err(bad("REASON"))}}
/// Validates a supplied wire and copies all application fields without repairing them.
/// Matching binding is a data constraint, not evidence of truthful execution.
pub fn project(bytes:&[u8],binding:&[u8;32])->Result<Response,Error>{
 let entry_fields=[Ref::Primitive(Kind::OptionInt64),Ref::Primitive(Kind::Text),Ref::Primitive(Kind::TextList),Ref::Primitive(Kind::TextList),Ref::Primitive(Kind::Text)];
 let refusal_fields=[Ref::Primitive(Kind::Text),Ref::Primitive(Kind::Text)];let state_fields=[Ref::Named(4)];let success_fields=[Ref::Primitive(Kind::TextList),Ref::Primitive(Kind::Text),Ref::Named(2)];let alternatives=[Ref::Named(1),Ref::Named(3)];
 let graph=[Definition::Product(&entry_fields),Definition::Product(&refusal_fields),Definition::Product(&state_fields),Definition::Product(&success_fields),Definition::List{element:Ref::Named(0),capacity:4},Definition::Sum(&alternatives)];
 let checked=wire::decode(&graph,Ref::Named(5),bytes,binding).map_err(Error::Wire)?;let view=View{bytes:checked.bytes(),nodes:checked.node_count(),pool:64+32*checked.node_count()};let root=view.node(0)?;let mut at=1;
 let result=match root.scalar{
  0=>{let end=view.record(&mut at,1,2)?;if view.text(&mut at)?!="refusal"{return Err(bad("MARKER"))};let r=view.text(&mut at)?;if at!=end{return Err(bad("REFUSAL"))};Response::Refusal(reason(&r)?)},
  1=>{let end=view.record(&mut at,3,3)?;let entry_ids=view.texts(&mut at)?;if view.text(&mut at)?!="success"{return Err(bad("MARKER"))};let state=view.state(&mut at)?;if at!=end{return Err(bad("SUCCESS"))};Response::Success{state,entry_ids}},
  _=>return Err(bad("VARIANT")),
 };
 if at!=root.end||at!=view.nodes{return Err(bad("ROOT"))};Ok(result)
}
