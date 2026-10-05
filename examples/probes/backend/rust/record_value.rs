//! Immutable flat products only; no source grammar, transport admission or ABI.
use crate::{text_value::Text,text_list::TextList,option_int::OptionInt64,int_projection::IntProjection};
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum Kind {Int64,Bool,Text,OptionInt64,TextList,IntProjection}
pub struct Field<'a>{pub name:&'a str,pub kind:Kind}
#[derive(Clone,Copy)]
pub enum Value<'items,'text>{Int64(i64),Bool(bool),Text(Text<'text>),Optional(OptionInt64),List(&'items TextList<'items,'text>),Projection(IntProjection)}
impl Value<'_,'_>{pub fn kind(&self)->Kind{match self{Self::Int64(_)=>Kind::Int64,Self::Bool(_)=>Kind::Bool,Self::Text(_)=>Kind::Text,Self::Optional(_)=>Kind::OptionInt64,Self::List(_)=>Kind::TextList,Self::Projection(_)=>Kind::IntProjection}}}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct Refusal{pub reason:&'static str,pub index:usize}
pub struct Record<'record,'items,'text>{schema:&'record[Field<'record>],values:&'record[Value<'items,'text>]}
impl<'record,'items,'text> Record<'record,'items,'text>{
 pub fn new(schema:&'record[Field<'record>],values:&'record[Value<'items,'text>])->Result<Self,Refusal>{
  if schema.len()>8{return Err(Refusal{reason:"RECORD_FIELDS",index:8});}
  for (i,field) in schema.iter().enumerate(){
   let n=field.name.as_bytes();
   if n.is_empty()||n.len()>32||!n[0].is_ascii_alphabetic()||!n[1..].iter().all(|b|b.is_ascii_alphanumeric()||*b==b'_'){return Err(Refusal{reason:"RECORD_NAME",index:i});}
   if i>0&&schema[i-1].name>=field.name{return Err(Refusal{reason:"RECORD_ORDER",index:i});}
  }
  if schema.len()!=values.len(){return Err(Refusal{reason:"RECORD_VALUES",index:schema.len().min(values.len())});}
  for (i,(field,value)) in schema.iter().zip(values).enumerate(){if field.kind!=value.kind(){return Err(Refusal{reason:"RECORD_TYPE",index:i});}}
  Ok(Self{schema,values})
 }
 pub fn len(&self)->usize{self.values.len()}
 pub fn is_empty(&self)->bool{self.values.is_empty()}
 pub fn get(&self,name:&str)->Option<&Value<'items,'text>>{self.schema.iter().position(|f|f.name==name).and_then(|i|self.values.get(i))}
}
