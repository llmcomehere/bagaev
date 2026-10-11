//! Separate /12 emitter and pre-dispatch checks. No generated kernel is executed.
pub mod transport; pub mod check; pub mod ir; pub mod canonical; pub mod sha256;
pub mod record_ir; pub mod option_int; pub mod text_value; pub mod text_list;
pub mod typed_record; pub mod text_inspection; pub mod int_projection;
pub mod record_value; pub mod type_graph; pub mod json_view;
pub mod variant_admission_v11; pub mod list_callframe; pub mod list_native_adapter;
pub mod json_native_input; pub mod json_native_input12; pub mod json_native_invocation12;
pub mod json_native_adapter_v12; pub mod composite_export_v11;
pub mod composite_native_cells; pub mod composite_result_decode_v11;
pub mod json_view11_llvm; pub mod json_view12_llvm;

#[cfg(test)]
mod tests {
 use super::*;
 use std::sync::atomic::{AtomicUsize,Ordering};
 use json_native_adapter_v12::{NativeValue,NativeText,KernelOutput,Cells,Arena};
 static CALLS:AtomicUsize=AtomicUsize::new(0);
 // Reviewed fixed main(Json)->Int64 =0 implementation; only the matching case calls it.
 unsafe extern "C" fn zero(_v:*const NativeValue,_a:*mut Arena,_c:*mut Cells,out:*mut KernelOutput){
  CALLS.fetch_add(1,Ordering::SeqCst);
  unsafe{out.write(KernelOutput{meta:composite_export_v11::Output{status:0,value_type:1,value:0,work:1,reason:0,location:0},value:NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0}});}
 }
 fn invocation(v:u8,body:&str,result:&str)->Vec<u8>{
  format!("{{\"schema\":\"bagaev-typed-record-invocation/{v}\",\"program\":{{\"schema\":\"bagaev-typed-record/{v}\",\"records\":{{}},\"lists\":{{}},\"variants\":{{}},\"entry\":\"main\",\"functions\":{{\"main\":{{\"params\":[[\"x\",\"Json\"]],\"result\":\"{result}\",\"body\":{body}}}}}}},\"arguments\":[true]}}").into_bytes()
 }
 #[test]
 fn explicit_emitter_selection_and_lazy_phi(){
  let raw=invocation(12,"[\"json.bool_or\",[\"arg\",\"x\"],[\"bool\",false]]","Bool");
  let x=typed_record::checked_json_invocation_v12(&raw).unwrap();
  assert!(json_view11_llvm::emit_program(x.program()).is_err());
  let module=json_view12_llvm::emit_program(x.program()).unwrap();
  let text=std::str::from_utf8(module.bytes()).unwrap();
  assert!(text.contains("bagaev_json_view12_kernel"));assert!(text.contains("i64 72)"));assert!(text.contains("phi i64"));
  let old=typed_record::checked_json_invocation_v11(&invocation(11,"[\"int\",0]","Int64")).unwrap();
  assert!(json_view12_llvm::emit_program(old.program()).is_err());
  assert!(json_native_invocation12::prepare(&old).is_err());
  assert!(json_view12_llvm::emit_with_limits(x.program(),1,1).is_err());
  assert!(json_view11_llvm::emit_with_limits(old.program(),1,1).is_err());
 }
 #[test]
 fn source_binding_and_slice_refuse_before_dispatch(){
  CALLS.store(0,Ordering::SeqCst);
  let raw=invocation(12,"[\"int\",0]","Int64");let x=typed_record::checked_json_invocation_v12(&raw).unwrap();
  let hex=x.program().identity().strip_prefix("sha256:").unwrap();let mut pin=[0u8;32];
  for(i,b)in pin.iter_mut().enumerate(){*b=u8::from_str_radix(&hex[2*i..2*i+2],16).unwrap();}
  let mut text=vec![NativeText{bytes:std::ptr::null(),len:0,scalars:0};65536];
  let mut cells=vec![NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0};65536];
  let mut wrong=pin;wrong[0]^=1;
  assert!(unsafe{json_native_adapter_v12::evaluate(&raw,&mut text,&mut cells,&wrong,zero)}.is_err());
  assert!(unsafe{json_native_adapter_v12::evaluate(&raw,&mut text[..65535],&mut cells,&pin,zero)}.is_err());
  assert!(unsafe{json_native_adapter_v12::evaluate(&invocation(11,"[\"int\",0]","Int64"),&mut text,&mut cells,&pin,zero)}.is_err());
  assert_eq!(CALLS.load(Ordering::SeqCst),0);
  let result=unsafe{json_native_adapter_v12::evaluate(&raw,&mut text,&mut cells,&pin,zero)}.unwrap();
  assert_eq!((result.meta.status,result.meta.work),(0,1));assert_eq!(&result.bytes[..8],b"BCMPRES4");assert_eq!(CALLS.load(Ordering::SeqCst),1);
 }
}
