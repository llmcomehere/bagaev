//! Owned primitive callback and pre-dispatch prepared /12 refusal tests.
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
pub mod json_native_input12;
pub mod json_native_invocation12;
pub mod json_native_adapter_v12;
pub mod composite_export_v11;
pub mod composite_native_cells;
pub mod composite_result_decode_v11;
pub mod prepared_json_native_v12;

#[cfg(test)]
mod tests {
 use super::*;
 use std::sync::atomic::{AtomicUsize,Ordering};
 use prepared_json_native_v12::{NativeValue,NativeText,KernelOutput,Cells,Arena};
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
  assert!(prepared_json_native_v12::prepare(&source(11,"Json","Int64")).is_err());
  assert!(prepared_json_native_v12::prepare(&source(12,"Int64","Int64")).is_err());
  let error=prepared_json_native_v12::prepare(&source(12,"Json","Json")).err().unwrap();assert!(matches!(error,json_native_adapter_v12::Error::Admission(ref text) if text == "Refusal(Refusal { reason: Type, location: \"/functions/main/result\" })"));
  println!("preparation refusals=3");
 }
 #[test]
 fn actual_slices_and_binding_refuse_before_dispatch(){
  CALLS.store(0,Ordering::SeqCst);let p=prepared_json_native_v12::prepare(&source(12,"Json","Int64")).unwrap();let binding=*p.binding();
  let mut text=vec![NativeText{bytes:std::ptr::null(),len:0,scalars:0};65536];
  let mut cells=vec![NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0};65536];
  let result=unsafe{prepared_json_native_v12::evaluate(&p,b"[0]",&mut text,&mut cells,&binding,zero)}.unwrap();
  assert_eq!((result.meta.status,result.meta.value_type,result.meta.work),(0,1,1));assert_eq!(&result.bytes[..8],b"BCMPRES4");assert_eq!(CALLS.load(Ordering::SeqCst),1);
  let mut wrong=binding;wrong[0]^=1;
  let cases:[(&[u8],[u8;32],usize,usize);6]=[(b"[0]",wrong,65536,65536),(b"[",binding,65536,65536),(b"[]",binding,65536,65536),(b"{}",binding,65536,65536),(b"[0]",binding,65535,65536),(b"[0]",binding,65536,65535)];
  for (raw,pin,tn,cn) in cases{
   assert!(unsafe{prepared_json_native_v12::evaluate(&p,raw,&mut text[..tn],&mut cells[..cn],&pin,zero)}.is_err());
   assert_eq!(CALLS.load(Ordering::SeqCst),1);
  }
  println!("owned primitive dispatch=1 per-call refusals=6 refused-call dispatch=0");
 }
 // Exact fixed implementation of bool_or(x,false), admitted for this test source only.
 unsafe extern "C" fn boolean(v:*const NativeValue,_a:*mut Arena,_c:*mut Cells,out:*mut KernelOutput){
  CALLS.fetch_add(1,Ordering::SeqCst);
  let node=unsafe{&*((*v).bytes.cast::<json_native_input12::Node>())};
  let (value,work)=if node.kind==2{assert!(node.bool_payload<=1);(node.bool_payload as i64,2)}else{(0,3)};
  unsafe{out.write(KernelOutput{meta:composite_export_v11::Output{status:0,value_type:2,value,work,reason:0,location:0},value:NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0}});}
 }
 #[test]
 fn boolean_payload_repeat_and_ownership(){
  CALLS.store(0,Ordering::SeqCst);
  let raw=br#"{"schema":"bagaev-typed-record/12","records":{},"lists":{},"variants":{},"entry":"main","functions":{"main":{"params":[["x","Json"]],"result":"Bool","body":["json.bool_or",["arg","x"],["bool",false]]}}}"#.to_vec();
  let p=prepared_json_native_v12::prepare(&raw).unwrap();drop(raw);let binding=*p.binding();let mut outputs=Vec::new();
  for _ in 0..2{
   for (raw,value,work) in [(b"[true]".as_slice(),1,2),(b"[false]".as_slice(),0,2),(b"[null]".as_slice(),0,3)]{
    let mut text=vec![NativeText{bytes:std::ptr::null(),len:0,scalars:0};65536];
    let mut cells=vec![NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0};65536];
    let result=unsafe{prepared_json_native_v12::evaluate(&p,raw,&mut text,&mut cells,&binding,boolean)}.unwrap();
    assert_eq!((result.meta.status,result.meta.value_type,result.meta.value,result.meta.work),(0,2,value,work));
    outputs.push(result.bytes);
   }
  }
  drop(p);assert_eq!(CALLS.load(Ordering::SeqCst),6);
  assert_eq!(outputs[..3],outputs[3..]);assert!(outputs.iter().all(|x|&x[..8]==b"BCMPRES4"));
 }

}
