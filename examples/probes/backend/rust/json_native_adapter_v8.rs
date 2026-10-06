//! Unsafe exact-kernel boundary; sealed Json data is not execution authority.
use crate::{typed_record,record_ir::Type as SourceType,record_value::Kind,
 variant_admission::{self,Type,ListDefinition},composite_export_v8,json_native_invocation};
pub use crate::composite_export_v8::{KernelOutput,Owned,NativeValue,NativeText};
pub use crate::composite_native_cells::Cells;
pub type Kernel=unsafe extern "C" fn(*const NativeValue,*mut Arena,*mut Cells,*mut KernelOutput);
pub use crate::list_native_adapter::Arena;
#[derive(Debug,Eq,PartialEq)]
pub enum Error{Admission(String),Interface,Graph(variant_admission::Refusal),Input(crate::json_native_input::Error),Output(composite_export_v8::Error)}
fn ty(t:SourceType)->Result<Type,Error>{Ok(match t{
 SourceType::Int64=>Type::Primitive(Kind::Int64),SourceType::Bool=>Type::Primitive(Kind::Bool),SourceType::Text=>Type::Primitive(Kind::Text),SourceType::OptionInt64=>Type::Primitive(Kind::OptionInt64),SourceType::TextList=>Type::Primitive(Kind::TextList),SourceType::Record(n)=>Type::Record(n),SourceType::RecordList(n)=>Type::RecordList(n),SourceType::Variant(n)=>Type::Variant(n),SourceType::Json=>return Err(Error::Interface),
})}
/// # Safety
/// kernel must be separately admitted for this exact checked source/result graph
/// and binding. It preserves immutable inputs, stays within disjoint live scratch
/// and64byteoutput, fully initializes all reachable output, retains no pointers
/// and never unwinds. Shape checks cannot admit arbitrary code or raw pointers.
pub unsafe fn evaluate(raw:&[u8],text:&mut[NativeText],cells:&mut[NativeValue],binding:&[u8;32],kernel:Kernel)->Result<Owned,Error>{
 let invocation=typed_record::checked_json_invocation_v8(raw).map_err(Error::Admission)?;
 let program=invocation.program();
 let definitions=program.record_definitions().iter().map(|d|d.fields().iter().map(|(_,t)|ty(*t)).collect::<Result<Vec<_>,_>>()).collect::<Result<Vec<_>,_>>()?;
 let variants=program.variant_definitions().iter().map(|d|d.alternatives().iter().map(|(_,t)|ty(*t)).collect::<Result<Vec<_>,_>>()).collect::<Result<Vec<_>,_>>()?;
 let lists=program.list_definitions().iter().map(|d|Ok(ListDefinition{element:u8::try_from(d.element()).map_err(|_|Error::Interface)?,capacity:u8::try_from(d.capacity()).map_err(|_|Error::Interface)?})).collect::<Result<Vec<_>,Error>>()?;
 let defs=definitions.iter().map(Vec::as_slice).collect::<Vec<_>>();let sums=variants.iter().map(Vec::as_slice).collect::<Vec<_>>();let result=ty(program.functions()[program.entry()].result())?;
 let checked=variant_admission::check(&defs,&lists,&sums,&[],result,&[],text.len(),cells.len(),32768).map_err(Error::Graph)?;
 let input=json_native_invocation::prepare(&invocation).map_err(Error::Input)?;
 let mut arguments=Vec::new();for i in 0..invocation.json_arguments().len(){arguments.push(NativeValue{scalar:0,bytes:input.root(i).ok_or(Error::Interface)?.cast(),len:0,scalars:0});}
 let tb=text.as_mut_ptr();let cb=cells.as_mut_ptr();let mut arena=Arena{base:tb,capacity:65536,used:0};let mut cell_arena=Cells{base:cb,capacity:65536,used:0};
 let mut output=KernelOutput{meta:composite_export_v8::Output::zero(),value:NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0}};
 unsafe{kernel(arguments.as_ptr(),&mut arena,&mut cell_arena,&mut output);}
 if arena.base!=tb||arena.capacity!=65536||arena.used>65536||cell_arena.base!=cb||cell_arena.capacity!=65536||cell_arena.used>65536{return Err(Error::Output(composite_export_v8::Error("NATIVE_ARENA")));}
 unsafe{composite_export_v8::export(&checked,&output,binding)}.map_err(Error::Output)
}
