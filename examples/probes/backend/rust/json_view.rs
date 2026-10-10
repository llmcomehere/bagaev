//! Generic bounded JSON views, no application validation or execution.
use crate::{transport::{Document,Value,JsonString},text_value::Text,option_int::OptionInt64,int_projection::{self,IntProjection}};
use std::collections::BTreeMap;
pub struct Owned{document:Document,texts:Vec<Option<String>>}
#[derive(Clone,Copy)]
pub struct View<'a>{owner:&'a Owned,id:Option<usize>}
fn reserve(old:usize,values:&mut Vec<Value>,todo:&mut Vec<(usize,usize)>,map:&mut BTreeMap<usize,usize>)->Result<usize,&'static str>{if let Some(&id)=map.get(&old){return Ok(id);}if values.len()>=16384{return Err("JSON view bound");}let id=values.len();values.push(Value::Null);todo.push((old,id));map.insert(old,id);Ok(id)}
impl Owned{
 pub fn copy(doc:&Document,root:usize)->Result<Self,&'static str>{
  let mut values=Vec::new();let mut todo=Vec::new();let mut map=BTreeMap::new();reserve(root,&mut values,&mut todo,&mut map)?;
  while let Some((old,new))=todo.pop(){let value=match doc.values.get(old).ok_or("JSON view reference")?{
   Value::Null=>Value::Null,Value::Bool(v)=>Value::Bool(*v),Value::Integer(v)=>Value::Integer(v.clone()),Value::Number(v)=>Value::Number(v.clone()),Value::String(v)=>Value::String(v.clone()),
   Value::Array(a)=>{let mut out=Vec::new();for id in a{out.push(reserve(*id,&mut values,&mut todo,&mut map)?);}Value::Array(out)},
   Value::Object(a)=>{let mut out=BTreeMap::new();for(key,id)in a{out.insert(key.clone(),reserve(*id,&mut values,&mut todo,&mut map)?);}Value::Object(out)},
  };values[new]=value;}
  let texts=values.iter().map(|v|match v{Value::String(s) if s.0.len()<=256=>s.scalar_string().filter(|s|Text::from_bytes(s.as_bytes()).is_ok()),_=>None}).collect();Ok(Self{document:Document{values,root:0},texts})
 }
 pub fn document(&self)->&Document{&self.document}
 pub fn root(&self)->View<'_>{View{owner:self,id:Some(0)}}
}
impl<'a> View<'a>{
 fn value(self)->Option<&'a Value>{self.id.and_then(|i|self.owner.document.values.get(i))}
 pub fn boolean(self)->Option<bool>{match self.value(){Some(Value::Bool(v))=>Some(*v),_=>None}}
 pub fn kind(self)->&'static str{match self.value(){None=>"missing",Some(Value::Null)=>"null",Some(Value::Bool(_))=>"bool",Some(Value::Integer(_))=>"int",Some(Value::Number(_))=>"number",Some(Value::String(_))=>"text",Some(Value::Array(_))=>"array",Some(Value::Object(_))=>"object"}}
 pub fn field_charge(self,key:&str)->u64{match self.value(){Some(Value::Object(m))=>(m.len() as u64).saturating_mul((key.len() as u64).saturating_add(1)),_=>0}}
 pub fn field(self,key:&str)->Self{let id=match self.value(){Some(Value::Object(m))=>m.get(&JsonString::from_str(key)).copied(),_=>None};Self{owner:self.owner,id}}
 pub fn at(self,index:i64)->Self{let id=match self.value(){Some(Value::Array(a)) if index>=0 && (index as u64)<a.len() as u64=>Some(a[index as usize]),_=>None};Self{owner:self.owner,id}}
 pub fn len(self)->OptionInt64{match self.value(){Some(Value::Array(a))=>OptionInt64::some(a.len() as i64),Some(Value::Object(m))=>OptionInt64::some(m.len() as i64),_=>OptionInt64::none()}}
 pub fn int_charge(self)->u64{match self.value(){Some(Value::Integer(s))=>s.len() as u64,_=>0}}
 pub fn integer(self)->OptionInt64{match int_projection::project_int(self.value()){IntProjection::Present(v)=>OptionInt64::some(v),_=>OptionInt64::none()}}
 pub fn text_len(self)->Option<usize>{self.id.and_then(|i|self.owner.texts.get(i)).and_then(|x|x.as_ref()).map(String::len)}
 pub fn text(self)->Option<Text<'a>>{self.id.and_then(|i|self.owner.texts.get(i)).and_then(|x|x.as_ref()).and_then(|s|Text::from_bytes(s.as_bytes()).ok())}
}
