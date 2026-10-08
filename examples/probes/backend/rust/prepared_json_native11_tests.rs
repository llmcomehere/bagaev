//! Owned primitive callback and pre-dispatch prepared /11 refusal tests.
pub mod transport;
pub mod check;
pub mod ir;
pub mod canonical;
pub mod sha256;
pub mod record_ir;
pub mod option_int;
pub mod text_value;
pub mod text_list;
pub mod typed_record;
pub mod text_inspection;
pub mod int_projection;
pub mod record_value;
pub mod type_graph;
pub mod json_view;
pub mod variant_admission_v11;
pub mod list_callframe;
pub mod list_native_adapter;
pub mod json_native_input;
pub mod json_native_invocation;
pub mod json_native_adapter_v11;
pub mod composite_export_v11;
pub mod composite_native_cells;
pub mod composite_result_decode_v11;
pub mod prepared_json_native_v11;

#[cfg(test)]
mod tests {
 use super::*;
 use std::sync::atomic::{AtomicUsize,Ordering};
 use prepared_json_native_v11::{NativeValue,NativeText,KernelOutput,Cells,Arena};
 static CALLS:AtomicUsize=AtomicUsize::new(0);
 // Reviewed fixed implementation of main(Json)->Int64 = 0, work1.
 unsafe extern "C" fn zero(_v:*const NativeValue,_a:*mut Arena,_c:*mut Cells,out:*mut KernelOutput){
  CALLS.fetch_add(1,Ordering::SeqCst);
  unsafe{out.write(KernelOutput{meta:composite_export_v11::Output{status:0,value_type:1,value:0,work:1,reason:0,location:0},value:NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0}});}
 }
 fn source(version:u8,param:&str,result:&str)->Vec<u8>{
  let body=if result=="Json"{"[\"arg\",\"x\"]"}else{"[\"int\",0]"};
  format!("{{\"schema\":\"bagaev-typed-record/{}\",\"records\":{{}},\"lists\":{{}},\"variants\":{{}},\"entry\":\"main\",\"functions\":{{\"main\":{{\"params\":[[\"x\",\"{}\"]],\"result\":\"{}\",\"body\":{}}}}}}}",version,param,result,body).into_bytes()
 }
 #[test]
 fn preparation_refusals(){
  assert!(prepared_json_native_v11::prepare(&source(10,"Json","Int64")).is_err());
  assert!(prepared_json_native_v11::prepare(&source(11,"Int64","Int64")).is_err());
  let error=prepared_json_native_v11::prepare(&source(11,"Json","Json")).err().unwrap();assert!(matches!(error,json_native_adapter_v11::Error::Admission(ref text) if text == "Refusal(Refusal { reason: Type, location: \"/functions/main/result\" })"));
  println!("preparation refusals=3");
 }
 #[test]
 fn actual_slices_and_binding_refuse_before_dispatch(){
  CALLS.store(0,Ordering::SeqCst);let p=prepared_json_native_v11::prepare(&source(11,"Json","Int64")).unwrap();let binding=*p.binding();
  let mut text=vec![NativeText{bytes:std::ptr::null(),len:0,scalars:0};65536];
  let mut cells=vec![NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0};65536];
  let result=unsafe{prepared_json_native_v11::evaluate(&p,b"[0]",&mut text,&mut cells,&binding,zero)}.unwrap();
  assert_eq!((result.meta.status,result.meta.value_type,result.meta.work),(0,1,1));assert_eq!(&result.bytes[..8],b"BCMPRES4");assert_eq!(CALLS.load(Ordering::SeqCst),1);
  let mut wrong=binding;wrong[0]^=1;
  let cases:[(&[u8],[u8;32],usize,usize);6]=[(b"[0]",wrong,65536,65536),(b"[",binding,65536,65536),(b"[]",binding,65536,65536),(b"{}",binding,65536,65536),(b"[0]",binding,65535,65536),(b"[0]",binding,65536,65535)];
  for (raw,pin,tn,cn) in cases{
   assert!(unsafe{prepared_json_native_v11::evaluate(&p,raw,&mut text[..tn],&mut cells[..cn],&pin,zero)}.is_err());
   assert_eq!(CALLS.load(Ordering::SeqCst),1);
  }
  println!("owned primitive dispatch=1 per-call refusals=6 refused-call dispatch=0");
 }
}
