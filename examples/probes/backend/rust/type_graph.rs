//! Bounded acyclic composite shape admission only; no source syntax or native ABI.
use crate::record_value::Kind;
#[derive(Clone,Copy)]
pub enum Ref{Primitive(Kind),Named(u8)}
pub enum Definition<'a>{Product(&'a[Ref]),Sum(&'a[Ref]),List{element:Ref,capacity:u8}}
impl Definition<'_>{fn refs(&self)->&[Ref]{match self{Self::Product(x)|Self::Sum(x)=>x,Self::List{element,..}=>std::slice::from_ref(element)}}}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct Refusal{pub reason:&'static str,pub index:usize}
pub struct Checked<'a>{definitions:&'a[Definition<'a>],entry_units:u32}
impl Checked<'_>{pub fn entry_units(&self)->u32{self.entry_units} pub fn definition_count(&self)->usize{self.definitions.len()}}
fn cycle(i:usize,defs:&[Definition<'_>],color:&mut[u8;8])->Result<(),Refusal>{
 if color[i]==1{return Err(Refusal{reason:"GRAPH_CYCLE",index:i});}
 if color[i]==2{return Ok(());}color[i]=1;
 for r in defs[i].refs(){if let Ref::Named(j)=r{cycle(usize::from(*j),defs,color)?;}}
 color[i]=2;Ok(())
}
fn units(r:Ref,defs:&[Definition<'_>],memo:&mut[Option<u32>;8])->u32{
 match r{Ref::Primitive(Kind::TextList)=>65,Ref::Primitive(_)=>1,Ref::Named(n)=>{
  let i=usize::from(n);if let Some(x)=memo[i]{return x;}
  let count=match &defs[i]{
   Definition::Product(fields)=>{let mut sum=1;for x in *fields{sum=(sum+units(*x,defs,memo)).min(4097);}sum},
   Definition::Sum(alts)=>{let mut largest=0;for x in *alts{largest=largest.max(units(*x,defs,memo));}(1+largest).min(4097)},
   Definition::List{element,capacity}=>(1+u32::from(*capacity)*units(*element,defs,memo)).min(4097),
  };memo[i]=Some(count);count
 }}
}
pub fn check<'a>(defs:&'a[Definition<'a>],entry:Ref)->Result<Checked<'a>,Refusal>{
 if defs.len()>8{return Err(Refusal{reason:"GRAPH_COUNT",index:8});}
 for (i,d) in defs.iter().enumerate(){
  let bad=match d{Definition::Product(x)=>x.len()>8,Definition::Sum(x)=>x.is_empty()||x.len()>8,Definition::List{capacity,..}=>*capacity>4};
  if bad{return Err(Refusal{reason:"GRAPH_ARITY",index:i});}
  for r in d.refs(){if let Ref::Named(j)=r{if usize::from(*j)>=defs.len(){return Err(Refusal{reason:"GRAPH_REF",index:i});}}}
 }
 if let Ref::Named(j)=entry{if usize::from(j)>=defs.len(){return Err(Refusal{reason:"GRAPH_ENTRY",index:usize::from(j)});}}
 let mut color=[0u8;8];for i in 0..defs.len(){cycle(i,defs,&mut color)?;}
 let mut memo=[None;8];for i in 0..defs.len(){if units(Ref::Named(i as u8),defs,&mut memo)>4096{return Err(Refusal{reason:"GRAPH_EXPANSION",index:i});}}
 Ok(Checked{definitions:defs,entry_units:units(entry,defs,&mut memo)})
}
