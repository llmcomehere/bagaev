//! Experimental source-once Json /8 native boundary. Data preparation is not code admission.
use crate::{typed_record,record_ir::Type as SourceType,record_value::Kind,
 variant_admission::{self,Type,ListDefinition},composite_export_v8,json_native_input};
pub use crate::json_native_adapter_v8::{Error,Kernel,NativeValue,NativeText,KernelOutput,Cells,Arena};
pub use composite_export_v8::Owned;

pub struct Prepared {
 source:typed_record::PreparedJsonProgram,
 definitions:Vec<Vec<Type>>, lists:Vec<ListDefinition>, variants:Vec<Vec<Type>>, result:Type,
}
impl Prepared { pub fn source(&self)->&typed_record::PreparedJsonProgram { &self.source } }
fn ty(t:SourceType)->Result<Type,Error> { Ok(match t {
 SourceType::Int64=>Type::Primitive(Kind::Int64),SourceType::Bool=>Type::Primitive(Kind::Bool),
 SourceType::Text=>Type::Primitive(Kind::Text),SourceType::OptionInt64=>Type::Primitive(Kind::OptionInt64),
 SourceType::TextList=>Type::Primitive(Kind::TextList),SourceType::Record(n)=>Type::Record(n),
 SourceType::RecordList(n)=>Type::RecordList(n),SourceType::Variant(n)=>Type::Variant(n),
 SourceType::Json=>return Err(Error::Interface),
 }) }
pub fn prepare(raw_source:&[u8])->Result<Prepared,Error> {
 let source=typed_record::prepare_json_program_v8(raw_source).map_err(Error::Admission)?;
 let program=source.source();
 let definitions=program.record_definitions().iter().map(|d|d.fields().iter().map(|(_,t)|ty(*t)).collect::<Result<Vec<_>,_>>()).collect::<Result<Vec<_>,_>>()?;
 let variants=program.variant_definitions().iter().map(|d|d.alternatives().iter().map(|(_,t)|ty(*t)).collect::<Result<Vec<_>,_>>()).collect::<Result<Vec<_>,_>>()?;
 let lists=program.list_definitions().iter().map(|d|Ok(ListDefinition{element:u8::try_from(d.element()).map_err(|_|Error::Interface)?,capacity:u8::try_from(d.capacity()).map_err(|_|Error::Interface)?})).collect::<Result<Vec<_>,Error>>()?;
 let result=ty(program.functions()[program.entry()].result())?;
 {
  let defs=definitions.iter().map(Vec::as_slice).collect::<Vec<_>>();
  let sums=variants.iter().map(Vec::as_slice).collect::<Vec<_>>();
  variant_admission::check(&defs,&lists,&sums,&[],result,&[],65536,65536,32768).map_err(Error::Graph)?;
 }
 Ok(Prepared{source,definitions,lists,variants,result})
}
/// # Safety
/// kernel must be separately admitted for this exact prepared source and result
/// graph and binding. It preserves immutable inputs, writes only disjoint live
/// scratch/output bounds, initializes reachable output, retains no pointers and
/// never unwinds. A digest or this data handle cannot admit arbitrary native code.
pub unsafe fn evaluate(program:&Prepared,raw_arguments:&[u8],text:&mut[NativeText],cells:&mut[NativeValue],binding:&[u8;32],kernel:Kernel)->Result<Owned,Error> {
 let invocation=typed_record::prepare_json_arguments_v8(&program.source,raw_arguments).map_err(Error::Admission)?;
 let defs=program.definitions.iter().map(Vec::as_slice).collect::<Vec<_>>();
 let sums=program.variants.iter().map(Vec::as_slice).collect::<Vec<_>>();
 // Recheck the actual per-call storage; no cached proof of someone else's slices.
 let checked=variant_admission::check(&defs,&program.lists,&sums,&[],program.result,&[],text.len(),cells.len(),32768).map_err(Error::Graph)?;
 let documents=invocation.json_arguments().iter().map(|v|v.document()).collect::<Vec<_>>();
 let input=json_native_input::encode_admitted(&documents).map_err(Error::Input)?;
 let mut arguments=Vec::with_capacity(documents.len());
 for i in 0..documents.len() { arguments.push(NativeValue{scalar:0,bytes:input.root(i).ok_or(Error::Interface)?.cast(),len:0,scalars:0}); }
 let tb=text.as_mut_ptr();let cb=cells.as_mut_ptr();
 let mut arena=Arena{base:tb,capacity:65536,used:0};let mut cell_arena=Cells{base:cb,capacity:65536,used:0};
 let mut output=KernelOutput{meta:composite_export_v8::Output::zero(),value:NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0}};
 unsafe { kernel(arguments.as_ptr(),&mut arena,&mut cell_arena,&mut output); }
 if arena.base!=tb||arena.capacity!=65536||arena.used>65536||cell_arena.base!=cb||cell_arena.capacity!=65536||cell_arena.used>65536 {
  return Err(Error::Output(composite_export_v8::Error("NATIVE_ARENA")));
 }
 unsafe { composite_export_v8::export(&checked,&output,binding) }.map_err(Error::Output)
}
