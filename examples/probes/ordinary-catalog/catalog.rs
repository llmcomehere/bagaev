//! Direct ordinary catalogue application. Shared JSON transport, no language interpreter.
use crate::transport::{Document,JsonString,Value,ValueId};
use std::collections::BTreeMap;

#[derive(Clone,Debug,Eq,PartialEq)]
pub struct Entry {pub id:String,pub title:String,pub manual_tags:Vec<String>,pub indexed_tags:Vec<String>,pub date:Option<i64>}
#[derive(Clone,Debug,Eq,PartialEq)]
pub struct State {pub entries:Vec<Entry>}
#[derive(Clone,Debug,Eq,PartialEq)]
pub enum Response {Refusal(&'static str),Success{state:State,entry_ids:Vec<String>}}
struct PendingEntry {entry:Entry,date_id:Option<ValueId>}
struct Reindex {entry_id:String,tags:Vec<String>}
struct Request {revision:i64,entries:Vec<PendingEntry>,reindex:Option<Reindex>}
type Object=BTreeMap<JsonString,ValueId>;
fn field(o:&Object,k:&str)->Option<ValueId>{o.get(&JsonString::from_str(k)).copied()}
fn object<'a>(d:&'a Document,id:ValueId,required:&[&str],optional:&[&str])->Option<&'a Object>{
 let Value::Object(o)=d.values.get(id)? else{return None};
 if !required.iter().all(|k|field(o,k).is_some()){return None}
 if !o.keys().all(|k|required.iter().chain(optional).any(|s|*k==JsonString::from_str(s))){return None}
 Some(o)
}
fn text(d:&Document,id:ValueId)->Option<String>{if let Value::String(s)=d.values.get(id)?{s.scalar_string()}else{None}}
fn integer(d:&Document,id:ValueId,high:i64)->Option<i64>{
 let Value::Integer(raw)=d.values.get(id)? else{return None};let n=raw.parse::<i64>().ok()?;(0..=high).contains(&n).then_some(n)
}
fn identifier(s:&str)->bool{let b=s.as_bytes();(1..=8).contains(&b.len())&&b[0].is_ascii_lowercase()&&b.iter().all(|c|c.is_ascii_lowercase()||c.is_ascii_digit()||*c==b'-')}
fn id_text(d:&Document,id:ValueId)->Option<String>{let s=text(d,id)?;identifier(&s).then_some(s)}
fn tags(d:&Document,id:ValueId)->Option<Vec<String>>{
 let Value::Array(a)=d.values.get(id)? else{return None};if a.len()>4{return None};a.iter().map(|id|id_text(d,*id)).collect()
}
fn shape(d:&Document)->Option<Request>{
 let o=object(d,d.root,&["interface","behavior_revision","state","reindex"],&[])?;
 if text(d,field(o,"interface")?)?!="catalog-application/2"{return None}
 let revision=integer(d,field(o,"behavior_revision")?,3)?;
 let state=object(d,field(o,"state")?,&["entries"],&[])?;
 let Value::Array(items)=d.values.get(field(state,"entries")?)? else{return None};if items.len()>4{return None}
 let mut entries=Vec::with_capacity(items.len());
 for &id in items {
  let e=object(d,id,&["id","title","manual_tags","indexed_tags"],&["date"])?;
  let id=id_text(d,field(e,"id")?)?;let title=text(d,field(e,"title")?)?;
  if !(1..=16).contains(&title.len())||!title.bytes().all(|c|(32..=126).contains(&c)){return None}
  let manual_tags=tags(d,field(e,"manual_tags")?)?;let indexed_tags=tags(d,field(e,"indexed_tags")?)?;
  entries.push(PendingEntry{entry:Entry{id,title,manual_tags,indexed_tags,date:None},date_id:field(e,"date")});
 }
 let reindex_id=field(o,"reindex")?;
 let reindex=if matches!(d.values.get(reindex_id)?,Value::Null){None}else{
  let r=object(d,reindex_id,&["entry_id","tags"],&[])?;Some(Reindex{entry_id:id_text(d,field(r,"entry_id")?)?,tags:tags(d,field(r,"tags")?)?})
 };
 Some(Request{revision,entries,reindex})
}
fn intersects(a:&[String],b:&[String])->bool{a.iter().any(|x|b.contains(x))}
/// Complete application result over immutable admitted JSON data. No external effects.
pub fn evaluate(d:&Document)->Response{
 let Some(mut request)=shape(d) else{return Response::Refusal("invalid-request")};
 // Date validation is deliberately after the complete request-shape gate.
 for p in &mut request.entries {
  if let Some(id)=p.date_id{let Some(n)=integer(d,id,31) else{return Response::Refusal("invalid-date")};p.entry.date=Some(n);}
 }
 let mut entries:Vec<Entry>=request.entries.into_iter().map(|p|p.entry).collect();
 for i in 0..entries.len(){if entries[i+1..].iter().any(|e|e.id==entries[i].id){return Response::Refusal("duplicate-entry-id")}}
 if entries.windows(2).any(|es|es[0].id>=es[1].id){return Response::Refusal("entry-order")}
 if entries.iter().any(|e|intersects(&e.manual_tags,&e.indexed_tags)){return Response::Refusal("origin-collision")}
 let target=if let Some(r)=&request.reindex{
  let Some(i)=entries.iter().position(|e|e.id==r.entry_id) else{return Response::Refusal("entry-not-found")};
  if request.revision>=2&&intersects(&entries[i].manual_tags,&r.tags){return Response::Refusal("origin-collision")}
  Some(i)
 }else{None};
 // All refusal gates precede the actual transformation.
 if let (Some(i),Some(r))=(target,request.reindex){if request.revision<2{entries[i].manual_tags.clear()};entries[i].indexed_tags=r.tags;}
 if request.revision>=1{for e in &mut entries{e.manual_tags.sort_unstable();e.manual_tags.dedup();e.indexed_tags.sort_unstable();e.indexed_tags.dedup();}}
 let mut order:Vec<usize>=(0..entries.len()).collect();
 order.sort_unstable_by(|&a,&b|{
  let x=&entries[a];let y=&entries[b];
  let key=|e:&Entry|match e.date{Some(n)=>(0,n),None=>(if request.revision==3{1}else{-1},0)};
  key(x).cmp(&key(y)).then_with(||x.id.cmp(&y.id))
 });
 let entry_ids=order.into_iter().map(|i|entries[i].id.clone()).collect();Response::Success{state:State{entries},entry_ids}
}
fn quote(s:&str,out:&mut String){
 out.push('"');for c in s.chars(){match c{'"'=>out.push_str("\\\""),'\\'=>out.push_str("\\\\"),'\n'=>out.push_str("\\n"),'\r'=>out.push_str("\\r"),'\t'=>out.push_str("\\t"),c if c<' '=>{use std::fmt::Write;write!(out,"\\u{:04x}",c as u32).unwrap()},c=>out.push(c)}}out.push('"');
}
fn array(xs:&[String],out:&mut String){out.push('[');for (i,s) in xs.iter().enumerate(){if i>0{out.push(',')};quote(s,out)}out.push(']')}
/// JSON encoding of owned application data, not a bagaev result/work envelope.
pub fn encode(response:&Response)->Vec<u8>{
 let mut out=String::new();match response{
  Response::Refusal(reason)=>{out.push_str("{\"kind\":\"refusal\",\"reason\":");quote(reason,&mut out);out.push('}')},
  Response::Success{state,entry_ids}=>{
   out.push_str("{\"entry_ids\":");array(entry_ids,&mut out);out.push_str(",\"kind\":\"success\",\"state\":{\"entries\":[");
   for (i,e) in state.entries.iter().enumerate(){
    if i>0{out.push(',')};out.push('{');if let Some(n)=e.date{use std::fmt::Write;write!(out,"\"date\":{n},").unwrap()}
    out.push_str("\"id\":");quote(&e.id,&mut out);out.push_str(",\"indexed_tags\":");array(&e.indexed_tags,&mut out);out.push_str(",\"manual_tags\":");array(&e.manual_tags,&mut out);out.push_str(",\"title\":");quote(&e.title,&mut out);out.push('}');
   }
   out.push_str("]}}")
  }
 };out.push('\n');out.into_bytes()
}
