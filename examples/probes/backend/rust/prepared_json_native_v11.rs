//! Experimental source-once Json /11 native boundary. Data preparation is not code admission.
use crate::{typed_record,record_ir::Type as SourceType,record_value::Kind,
 variant_admission_v11::{self,Type,ListDefinition},composite_export_v11,json_native_input};
pub use crate::json_native_adapter_v11::{Error,Kernel,NativeValue,NativeText,KernelOutput,Cells,Arena};
pub use composite_export_v11::Owned;

pub struct Prepared {
 source:typed_record::PreparedJsonProgramV11,
 binding:[u8;32],
 definitions:Vec<Vec<Type>>, lists:Vec<ListDefinition>, variants:Vec<Vec<Type>>, result:Type,
}
impl Prepared {
 pub fn source(&self)->&typed_record::PreparedJsonProgramV11 { &self.source }
 pub fn binding(&self)->&[u8;32] { &self.binding }
}
fn ty(t:SourceType)->Result<Type,Error> { Ok(match t {
 SourceType::Int64=>Type::Primitive(Kind::Int64),SourceType::Bool=>Type::Primitive(Kind::Bool),
 SourceType::Text=>Type::Primitive(Kind::Text),SourceType::OptionInt64=>Type::Primitive(Kind::OptionInt64),
 SourceType::TextList=>Type::Primitive(Kind::TextList),SourceType::Record(n)=>Type::Record(n),
 SourceType::RecordList(n)=>Type::RecordList(n),SourceType::Variant(n)=>Type::Variant(n),
 SourceType::Json=>return Err(Error::Interface),
 }) }
pub fn prepare(raw_source:&[u8])->Result<Prepared,Error> {
 let source=typed_record::prepare_json_program_v11(raw_source).map_err(Error::Admission)?;
 let program=source.source();
 let definitions=program.record_definitions().iter().map(|d|d.fields().iter().map(|(_,t)|ty(*t)).collect::<Result<Vec<_>,_>>()).collect::<Result<Vec<_>,_>>()?;
 let variants=program.variant_definitions().iter().map(|d|d.alternatives().iter().map(|(_,t)|ty(*t)).collect::<Result<Vec<_>,_>>()).collect::<Result<Vec<_>,_>>()?;
 let lists=program.list_definitions().iter().map(|d|Ok(ListDefinition{element:u8::try_from(d.element()).map_err(|_|Error::Interface)?,capacity:u8::try_from(d.capacity()).map_err(|_|Error::Interface)?})).collect::<Result<Vec<_>,Error>>()?;
 let result=ty(program.functions()[program.entry()].result())?;
 {
  let defs=definitions.iter().map(Vec::as_slice).collect::<Vec<_>>();
  let sums=variants.iter().map(Vec::as_slice).collect::<Vec<_>>();
  variant_admission_v11::check(&defs,&lists,&sums,&[],result,&[],65536,65536,32768).map_err(Error::Graph)?;
 }
 let hex=program.identity().strip_prefix("sha256:").ok_or(Error::Interface)?;
 if hex.len()!=64 { return Err(Error::Interface); }
 let digit=|b:u8|->Result<u8,Error>{match b{b'0'..=b'9'=>Ok(b-b'0'),b'a'..=b'f'=>Ok(b-b'a'+10),_=>Err(Error::Interface)}};
 let mut binding=[0u8;32];
 for (i,pair) in hex.as_bytes().chunks_exact(2).enumerate(){binding[i]=(digit(pair[0])?<<4)|digit(pair[1])?;}
 Ok(Prepared{source,binding,definitions,lists,variants,result})
}
/// # Safety
/// kernel must be separately admitted for this exact prepared source and result
/// graph and binding. It preserves immutable inputs, writes only disjoint live
/// scratch/output bounds, initializes reachable output, retains no pointers and
/// never unwinds. A digest or this data handle cannot admit arbitrary native code.
pub unsafe fn evaluate(program:&Prepared,raw_arguments:&[u8],text:&mut[NativeText],cells:&mut[NativeValue],binding:&[u8;32],kernel:Kernel)->Result<Owned,Error> {
 if binding!=&program.binding { return Err(Error::Admission("PREPARED_SOURCE_PIN".to_owned())); }
 let invocation=typed_record::prepare_json_arguments_v11(&program.source,raw_arguments).map_err(Error::Admission)?;
 let defs=program.definitions.iter().map(Vec::as_slice).collect::<Vec<_>>();
 let sums=program.variants.iter().map(Vec::as_slice).collect::<Vec<_>>();
 // Recheck the actual per-call storage; no cached proof of someone else's slices.
 let checked=variant_admission_v11::check(&defs,&program.lists,&sums,&[],program.result,&[],text.len(),cells.len(),32768).map_err(Error::Graph)?;
 let documents=invocation.json_arguments().iter().map(|v|v.document()).collect::<Vec<_>>();
 let input=json_native_input::encode_admitted(&documents).map_err(Error::Input)?;
 let mut arguments=Vec::with_capacity(documents.len());
 for i in 0..documents.len() { arguments.push(NativeValue{scalar:0,bytes:input.root(i).ok_or(Error::Interface)?.cast(),len:0,scalars:0}); }
 let tb=text.as_mut_ptr();let cb=cells.as_mut_ptr();
 let mut arena=Arena{base:tb,capacity:65536,used:0};let mut cell_arena=Cells{base:cb,capacity:65536,used:0};
 let mut output=KernelOutput{meta:composite_export_v11::Output::zero(),value:NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0}};
 unsafe { kernel(arguments.as_ptr(),&mut arena,&mut cell_arena,&mut output); }
 if arena.base!=tb||arena.capacity!=65536||arena.used>65536||cell_arena.base!=cb||cell_arena.capacity!=65536||cell_arena.used>65536 {
  return Err(Error::Output(composite_export_v11::Error("NATIVE_ARENA")));
 }
 unsafe { composite_export_v11::export(&checked,&output,binding) }.map_err(Error::Output)
}
