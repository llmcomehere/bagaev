//! Own initialized-data qualification only. No generated kernel is called.
pub mod transport;pub mod option_int;pub mod int_projection;pub mod text_value;pub mod text_list;
pub mod record_value;pub mod type_graph;pub mod list_callframe;pub mod list_native_adapter;
pub mod variant_admission;pub mod variant_admission_v11;
pub mod composite_export_v11;pub mod composite_result_decode_v10;pub mod composite_result_decode_v11;
use variant_admission_v11::{Type,ListDefinition};
use list_native_adapter::{NativeValue,Output};
use type_graph::{Definition,Ref};
fn zero()->NativeValue{NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0}}
fn main(){
 let fields=[Type::Primitive(record_value::Kind::Int64)];let defs:[&[Type];1]=[&fields];let lists=[ListDefinition{element:0,capacity:16}];
 let checked=variant_admission_v11::check(&defs,&lists,&[],&[],Type::RecordList(0),&[],65536,65536,32768).expect("wide graph");
 let primitive=Ref::Primitive(record_value::Kind::Int64);let row=[primitive];let graph=[Definition::Product(&row),Definition::List{element:Ref::Named(0),capacity:16}];let binding=[42u8;32];
 let owned={
  let records:Vec<[NativeValue;1]>=(0..16).map(|i|[NativeValue{scalar:i,..zero()}]).collect();
  let cells:Vec<NativeValue>=records.iter().map(|r|NativeValue{bytes:r.as_ptr().cast(),..zero()}).collect();
  let mut out=composite_export_v11::KernelOutput{meta:Output{status:0,value_type:7,value:0,work:7,reason:0,location:0},value:NativeValue{bytes:cells.as_ptr().cast(),len:16,..zero()}};
  // Every recursively reached descriptor is aligned, initialized and owned above.
  let good=unsafe{composite_export_v11::export(&checked,&out,&binding)}.expect("owned export");
  out.value.len=17;assert_eq!(unsafe{composite_export_v11::export(&checked,&out,&binding)}.err().expect("oversize refusal").0,"NATIVE_VALUE");
  out.value.len=16;out.meta.work=65537;assert_eq!(unsafe{composite_export_v11::export(&checked,&out,&binding)}.err().expect("metadata refusal").0,"NATIVE_META");
  good
 }; // All descriptor owners are now destroyed; only detached bytes remain.
 let literal=include_str!("../../native-wide-wire/expected-wire.hex").trim();let expected:Vec<u8>=(0..literal.len()).step_by(2).map(|i|u8::from_str_radix(&literal[i..i+2],16).expect("literal hex")).collect();assert_eq!(owned.bytes,expected);
 let decoded=composite_result_decode_v11::decode(&graph,Ref::Named(1),&owned.bytes,&binding).expect("detached decode");assert_eq!(decoded.node_count(),33);assert_eq!(decoded.work(),7);assert_eq!(decoded.bytes(),expected);
 let too_large=[ListDefinition{element:0,capacity:17}];assert_eq!(variant_admission_v11::check(&defs,&too_large,&[],&[],Type::RecordList(0),&[],65536,65536,32768).err().expect("capacity refusal").reason,"ADMIT_LIST_CAPACITY");
 let cyclic=[Type::Record(0)];let cyclic_defs:[&[Type];1]=[&cyclic];assert_eq!(variant_admission_v11::check(&cyclic_defs,&[],&[],&[],Type::Record(0),&[],65536,65536,32768).err().expect("cycle refusal").reason,"GRAPH_CYCLE");
 let old_fields=[variant_admission::Type::Primitive(record_value::Kind::Int64)];let old_defs:[&[variant_admission::Type];1]=[&old_fields];let old_lists=[variant_admission::ListDefinition{element:0,capacity:16}];assert_eq!(variant_admission::check(&old_defs,&old_lists,&[],&[],variant_admission::Type::RecordList(0),&[],65536,65536,32768).err().expect("old bound").reason,"ADMIT_LIST_CAPACITY");
 let mut forged=owned.bytes.clone();forged[24]^=1;assert_eq!(composite_result_decode_v11::decode(&graph,Ref::Named(1),&forged,&binding).err().expect("binding refusal").reason,"WIRE_BINDING");
 forged=owned.bytes.clone();forged[84..88].copy_from_slice(&17u32.to_le_bytes());assert_eq!(composite_result_decode_v11::decode(&graph,Ref::Named(1),&forged,&binding).err().expect("shape refusal").reason,"WIRE_SHAPE");
 forged=owned.bytes.clone();forged[..8].copy_from_slice(b"BCMPRES3");assert_eq!(composite_result_decode_v11::decode(&graph,Ref::Named(1),&forged,&binding).err().expect("old magic refusal").reason,"WIRE_MAGIC");
 let empty=composite_export_v11::KernelOutput{meta:Output{status:0,value_type:7,value:0,work:7,reason:0,location:0},value:zero()};
 let mut empty_wire=unsafe{composite_export_v11::export(&checked,&empty,&binding)}.expect("empty export").bytes;
 let old_graph=[Definition::Product(&row),Definition::List{element:Ref::Named(0),capacity:4}];
 assert_eq!(composite_result_decode_v10::decode(&old_graph,Ref::Named(1),&empty_wire,&binding).err().expect("new magic refusal").reason,"WIRE_MAGIC");
 empty_wire[..8].copy_from_slice(b"BCMPRES3");assert_eq!(composite_result_decode_v10::decode(&old_graph,Ref::Named(1),&empty_wire,&binding).expect("old wire remains valid").node_count(),1);
 let big_fields=[Type::RecordList(0);8];let big_defs:[&[Type];2]=[&fields,&big_fields];let big_lists=[ListDefinition{element:0,capacity:16},ListDefinition{element:1,capacity:16}];
 assert_eq!(variant_admission_v11::check(&big_defs,&big_lists,&[],&[],Type::RecordList(1),&[],65536,65536,32768).err().expect("expanded shape refusal").reason,"GRAPH_EXPANSION");
 let mut failure=composite_export_v11::KernelOutput{meta:Output{status:8,value_type:0,value:0,work:7,reason:15,location:1},value:zero()};
 assert_eq!(unsafe{composite_export_v11::export(&checked,&failure,&binding)}.expect("language failure").bytes,failure.meta.bytes());
 failure.meta.status=6;failure.meta.reason=13;assert_eq!(unsafe{composite_export_v11::export(&checked,&failure,&binding)}.err().expect("environment status rejected").0,"NATIVE_META");
 failure.meta.status=8;failure.meta.reason=15;failure.meta.value_type=7;assert_eq!(unsafe{composite_export_v11::export(&checked,&failure,&binding)}.err().expect("inactive payload metadata rejected").0,"NATIVE_META");
 println!("{{\"status\":\"PASSED\",\"full_wire_bytes\":1120,\"nodes\":33,\"refusals\":12,\"detached_after_owner_drop\":true,\"generated_kernel_calls\":0}}");
}
