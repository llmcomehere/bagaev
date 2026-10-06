//! Data-only projection of /10 JSON result data. Detached JSON proves no source identity.
use crate::{catalog::{Entry,State,Response},transport::{self,Document,JsonString,Value,ValueId},text_value::Text};
use std::collections::BTreeMap;
#[derive(Debug,Eq,PartialEq)]pub enum Error{Transport(transport::TransportError),Projection(&'static str)}
fn bad(s:&'static str)->Error{Error::Projection(s)}
type Object=BTreeMap<JsonString,ValueId>;
fn field(o:&Object,k:&str)->Result<ValueId,Error>{o.get(&JsonString::from_str(k)).copied().ok_or_else(||bad("FIELD"))}
fn object<'a>(d:&'a Document,id:ValueId,keys:&[&str],optional:&[&str])->Result<&'a Object,Error>{
 let Some(Value::Object(o))=d.values.get(id)else{return Err(bad("OBJECT"))};
 if !keys.iter().all(|k|field(o,k).is_ok())||!o.keys().all(|k|keys.iter().chain(optional).any(|s|*k==JsonString::from_str(s))){return Err(bad("KEYS"))};Ok(o)
}
fn text(d:&Document,id:ValueId)->Result<String,Error>{let Some(Value::String(s))=d.values.get(id)else{return Err(bad("TEXT"))};let s=s.scalar_string().ok_or_else(||bad("TEXT"))?;Text::from_bytes(s.as_bytes()).map_err(|_|bad("TEXT"))?;Ok(s)}
fn integer(d:&Document,id:ValueId)->Result<i64,Error>{let Some(Value::Integer(s))=d.values.get(id)else{return Err(bad("INTEGER"))};s.parse().map_err(|_|bad("INTEGER"))}
fn array(d:&Document,id:ValueId,cap:usize)->Result<&[ValueId],Error>{let Some(Value::Array(a))=d.values.get(id)else{return Err(bad("ARRAY"))};if a.len()>cap{return Err(bad("ARRAY"))};Ok(a)}
fn texts(d:&Document,id:ValueId)->Result<Vec<String>,Error>{let mut out=Vec::new();let mut total=0;for &id in array(d,id,64)?{let s=text(d,id)?;total+=s.len();if total>4096{return Err(bad("TEXTS"))};out.push(s)}Ok(out)}
fn reason(s:&str)->Result<&'static str,Error>{match s{"invalid-request"=>Ok("invalid-request"),"invalid-date"=>Ok("invalid-date"),"duplicate-entry-id"=>Ok("duplicate-entry-id"),"entry-order"=>Ok("entry-order"),"origin-collision"=>Ok("origin-collision"),"entry-not-found"=>Ok("entry-not-found"),_=>Err(bad("REASON"))}}
fn state(d:&Document,id:ValueId)->Result<State,Error>{
 let o=object(d,id,&["entries"],&[])?;let mut entries=Vec::new();
 for &id in array(d,field(o,"entries")?,4)?{
  let e=object(d,id,&["id","title","manual_tags","indexed_tags"],&["date"])?;
  let date=e.get(&JsonString::from_str("date")).map(|&id|integer(d,id)).transpose()?;
  entries.push(Entry{id:text(d,field(e,"id")?)?,title:text(d,field(e,"title")?)?,manual_tags:texts(d,field(e,"manual_tags")?)?,indexed_tags:texts(d,field(e,"indexed_tags")?)?,date});
 }
 Ok(State{entries})
}
/// Preserves all application values; caller must bind the actual evaluation separately.
pub fn project(bytes:&[u8])->Result<Response,Error>{
 let d=transport::parse(bytes).map_err(Error::Transport)?;let o=object(&d,d.root,&["schema","status","reason","location","value_type","value","work"],&[])?;
 if text(&d,field(o,"schema")?)?!="bagaev-typed-record-result/10"{return Err(bad("SCHEMA"))}
 if text(&d,field(o,"status")?)?!="success"{return Err(bad("LANGUAGE_FAILURE"))}
 if !matches!(d.values.get(field(o,"reason")?),Some(Value::Null))||!matches!(d.values.get(field(o,"location")?),Some(Value::Null)){return Err(bad("METADATA"))}
 if text(&d,field(o,"value_type")?)?!="Variant:Result"{return Err(bad("TYPE"))};let work=integer(&d,field(o,"work")?)?;if !(0..=65536).contains(&work){return Err(bad("WORK"))}
 let result=object(&d,field(o,"value")?,&["case","value"],&[])?;let payload=field(result,"value")?;
 match text(&d,field(result,"case")?)?.as_str(){
  "Error"=>{let r=object(&d,payload,&["kind","reason"],&[])?;if text(&d,field(r,"kind")?)?!="refusal"{return Err(bad("MARKER"))};Ok(Response::Refusal(reason(&text(&d,field(r,"reason")?)?)?))},
  "Ok"=>{let s=object(&d,payload,&["kind","state","entry_ids"],&[])?;if text(&d,field(s,"kind")?)?!="success"{return Err(bad("MARKER"))};Ok(Response::Success{state:state(&d,field(s,"state")?)?,entry_ids:texts(&d,field(s,"entry_ids")?)?})},
  _=>Err(bad("VARIANT")),
 }
}
