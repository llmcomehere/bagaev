//! Controlled owned Rust callback qualification, not generated LLVM execution.
pub mod transport;pub mod check;pub mod ir;pub mod canonical;pub mod sha256;
pub mod record_ir;pub mod option_int;pub mod text_value;pub mod text_list;
pub mod typed_record;pub mod text_inspection;pub mod int_projection;pub mod record_value;
pub mod type_graph;pub mod json_view;pub mod variant_admission_v11;
pub mod list_callframe;pub mod list_native_adapter;pub mod composite_native_cells;
pub mod json_native_input;pub mod json_native_invocation;pub mod composite_export_v11;
pub mod composite_result_decode_v11;pub mod json_native_adapter_v11;
use json_native_adapter_v11::{NativeValue,NativeText,KernelOutput,Arena,Cells};
use list_native_adapter::Output;
use std::sync::atomic::{AtomicUsize,Ordering};
static CALLS:AtomicUsize=AtomicUsize::new(0);
fn zero()->NativeValue{NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0}}
unsafe extern "C" fn constant(_: *const NativeValue,_:*mut Arena,cells:*mut Cells,out:*mut KernelOutput){
 CALLS.fetch_add(1,Ordering::SeqCst);
 // The adapter owns 65536 initialized cells; this callback uses only the first32.
 let arena=unsafe{&mut*cells};
 for i in 0..16{unsafe{arena.base.add(i).write(NativeValue{scalar:i as i64,..zero()});arena.base.add(16+i).write(NativeValue{bytes:arena.base.add(i).cast(),..zero()});}}
 arena.used=32;
 unsafe{out.write(KernelOutput{meta:Output{status:0,value_type:7,value:0,work:33,reason:0,location:0},value:NativeValue{bytes:arena.base.add(16).cast(),len:16,..zero()}});}
}
unsafe extern "C" fn bad_arena(_: *const NativeValue,arena:*mut Arena,_:*mut Cells,_:*mut KernelOutput){CALLS.fetch_add(1,Ordering::SeqCst);unsafe{(*arena).capacity=0;}}
unsafe extern "C" fn bad_output(_: *const NativeValue,_:*mut Arena,_:*mut Cells,out:*mut KernelOutput){CALLS.fetch_add(1,Ordering::SeqCst);unsafe{out.write(KernelOutput{meta:Output{status:0,value_type:7,value:0,work:33,reason:0,location:0},value:NativeValue{len:17,..zero()}});}}
fn main(){
 let raw=include_bytes!("../../native-wide-adapter/invocation.json");let text=include_str!("../../native-wide-adapter/expected-wire.hex").trim();let expected:Vec<u8>=(0..text.len()).step_by(2).map(|i|u8::from_str_radix(&text[i..i+2],16).expect("literal hex")).collect();let binding=[42u8;32];
 for fill in [90,165]{
  let output={let mut text=vec![NativeText{bytes:std::ptr::null(),len:fill,scalars:fill};65536];let mut cells=vec![NativeValue{scalar:fill as i64,bytes:std::ptr::null(),len:fill,scalars:fill};65536];
   unsafe{json_native_adapter_v11::evaluate(raw,&mut text,&mut cells,&binding,constant)}.expect("controlled callback")};
  assert_eq!(output.bytes,expected);assert_eq!(output.meta.work,33);
 }
 assert_eq!(CALLS.load(Ordering::SeqCst),2);
 let mut text=vec![NativeText::zero();65536];let mut cells=vec![zero();65536];
 assert!(matches!(unsafe{json_native_adapter_v11::evaluate(raw,&mut text[..1],&mut cells,&binding,constant)},Err(json_native_adapter_v11::Error::Graph(_))));assert_eq!(CALLS.load(Ordering::SeqCst),2);
 let old=std::str::from_utf8(raw).expect("fixture utf8").replace("/11","/10");assert!(matches!(unsafe{json_native_adapter_v11::evaluate(old.as_bytes(),&mut text,&mut cells,&binding,constant)},Err(json_native_adapter_v11::Error::Admission(_))));assert_eq!(CALLS.load(Ordering::SeqCst),2);
 assert!(matches!(unsafe{json_native_adapter_v11::evaluate(raw,&mut text,&mut cells,&binding,bad_arena)},Err(json_native_adapter_v11::Error::Output(composite_export_v11::Error("NATIVE_ARENA")))));
 assert!(matches!(unsafe{json_native_adapter_v11::evaluate(raw,&mut text,&mut cells,&binding,bad_output)},Err(json_native_adapter_v11::Error::Output(composite_export_v11::Error("NATIVE_VALUE")))));
 assert_eq!(CALLS.load(Ordering::SeqCst),4);
 let row=[type_graph::Ref::Primitive(record_value::Kind::Int64)];let graph=[type_graph::Definition::Product(&row),type_graph::Definition::List{element:type_graph::Ref::Named(0),capacity:16}];assert_eq!(composite_result_decode_v11::decode(&graph,type_graph::Ref::Named(1),&expected,&binding).expect("detached wire").node_count(),33);
 println!("{{\"status\":\"PASSED\",\"controlled_callback_calls\":4,\"success_fills\":2,\"refusals\":4,\"full_wire_bytes\":1120,\"generated_kernel_calls\":0}}");
}
