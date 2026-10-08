//! Data-only projection of source-bound BCMPRES4 success bytes; never executes code.
use crate::{typed_record,record_ir::Type,record_value::Kind,type_graph::{Definition,Ref},composite_result_decode_v11,canonical};
#[derive(Debug,Eq,PartialEq)]
pub enum Error { Source(String), Interface, Wire(composite_result_decode_v11::Refusal), OutputBounds }
const OUTPUT_LIMIT:usize=32*1024*1024;
fn reference(t:Type,records:usize,lists:usize)->Result<Ref,Error>{Ok(match t{
 Type::Int64=>Ref::Primitive(Kind::Int64),Type::Bool=>Ref::Primitive(Kind::Bool),Type::Text=>Ref::Primitive(Kind::Text),Type::OptionInt64=>Ref::Primitive(Kind::OptionInt64),Type::TextList=>Ref::Primitive(Kind::TextList),Type::Record(n)=>Ref::Named(n),Type::RecordList(n)=>Ref::Named((records+usize::from(n)) as u8),Type::Variant(n)=>Ref::Named((records+lists+usize::from(n)) as u8),Type::Json=>return Err(Error::Interface),
})}
fn word(w:&[u8],p:usize)->usize{u32::from_le_bytes(w[p..p+4].try_into().expect("validated word")) as usize}
struct Projection<'a>{program:&'a typed_record::CheckedSource,wire:&'a[u8],pool:usize,out:String}
impl Projection<'_>{
 fn value(&mut self,ty:Type,index:usize)->Result<usize,Error>{
  let p=64+32*index;let tag=word(self.wire,p);let end=word(self.wire,p+16);let count=word(self.wire,p+20);
  let scalar=i64::from_le_bytes(self.wire[p+8..p+16].try_into().expect("validated scalar"));let mut next=index+1;
  match ty{
   Type::Int64=>self.out.push_str(&scalar.to_string()),
   Type::Bool=>self.out.push_str(if scalar==0{"false"}else{"true"}),
   Type::OptionInt64=>if tag==4{self.out.push_str("null")}else{self.out.push_str(&scalar.to_string())},
   Type::Text=>{let start=self.pool+word(self.wire,p+24);let len=word(self.wire,p+28);let text=std::str::from_utf8(&self.wire[start..start+len]).expect("validated scalar text");canonical::quote(text,&mut self.out);},
   Type::TextList=>{self.out.push('[');for i in 0..count{if i>0{self.out.push(',');}next=self.value(Type::Text,next)?;}self.out.push(']');},
   Type::Record(n)=>{
    self.out.push('{');let mut written=0;
    for (name,field) in self.program.record_definitions()[usize::from(n)].fields(){
     let omitted=self.program.record_definitions()[usize::from(n)].omits_none(name)&&word(self.wire,64+32*next)==4;
     if omitted{next=word(self.wire,64+32*next+16);continue;}
     if written>0{self.out.push(',');}written+=1;canonical::quote(name,&mut self.out);self.out.push(':');next=self.value(*field,next)?;
    }self.out.push('}');
   },
   Type::RecordList(n)=>{let element=self.program.list_definitions()[usize::from(n)].element();self.out.push('[');for i in 0..count{if i>0{self.out.push(',');}next=self.value(Type::Record(element as u8),next)?;}self.out.push(']');},
   Type::Variant(n)=>{let (name,payload)=&self.program.variant_definitions()[usize::from(n)].alternatives()[scalar as usize];self.out.push_str("{\"case\":");canonical::quote(name,&mut self.out);self.out.push_str(",\"value\":");next=self.value(*payload,next)?;self.out.push('}');},
   Type::Json=>return Err(Error::Interface),
  }
  debug_assert!(next<=end);
  if self.out.len()>OUTPUT_LIMIT{return Err(Error::OutputBounds);}Ok(end)
 }
}
/// Validate the complete success wire against the explicitly supplied source,
/// then return owned JSON. Binding equality is not origin authentication.
/// Unbound 32-byte failure packets are deliberately unsupported.
pub fn decode_success(raw_source:&[u8],wire:&[u8])->Result<Vec<u8>,Error>{
 let prepared=typed_record::prepare_json_program_v11(raw_source).map_err(Error::Source)?;let program=prepared.source();
 let records=program.record_definitions().len();let lists=program.list_definitions().len();
 let products=program.record_definitions().iter().map(|d|d.fields().iter().map(|(_,t)|reference(*t,records,lists)).collect::<Result<Vec<_>,_>>()).collect::<Result<Vec<_>,_>>()?;
 let sums=program.variant_definitions().iter().map(|d|d.alternatives().iter().map(|(_,t)|reference(*t,records,lists)).collect::<Result<Vec<_>,_>>()).collect::<Result<Vec<_>,_>>()?;
 let mut defs=Vec::new();for fields in &products{defs.push(Definition::Product(fields));}
 for list in program.list_definitions(){defs.push(Definition::List{element:Ref::Named(list.element() as u8),capacity:list.capacity() as u8});}
 for alternatives in &sums{defs.push(Definition::Sum(alternatives));}
 let result=program.functions()[program.entry()].result();
 let pin=program.identity().strip_prefix("sha256:").ok_or(Error::Interface)?;if pin.len()!=64{return Err(Error::Interface);}
 let mut binding=[0u8;32];for(i,byte)in binding.iter_mut().enumerate(){*byte=u8::from_str_radix(&pin[2*i..2*i+2],16).map_err(|_|Error::Interface)?;}
 let checked=composite_result_decode_v11::decode(&defs,reference(result,records,lists)?,wire,&binding).map_err(Error::Wire)?;
 let mut projection=Projection{program,wire:checked.bytes(),pool:64+32*checked.node_count(),out:String::from("{\"schema\":\"bagaev-native-result/11\",\"source_pin\":")};
 canonical::quote(program.identity(),&mut projection.out);
 projection.out.push_str(",\"work\":");projection.out.push_str(&checked.work().to_string());projection.out.push_str(",\"value\":");projection.value(result,0)?;projection.out.push('}');
 if projection.out.len()>OUTPUT_LIMIT{return Err(Error::OutputBounds);}Ok(projection.out.into_bytes())
}
