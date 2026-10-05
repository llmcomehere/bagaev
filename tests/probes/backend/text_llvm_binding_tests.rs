#[path="../../../examples/probes/backend/rust/transport.rs"] pub mod transport;
#[path="../../../examples/probes/backend/rust/check.rs"] pub mod check;
#[path="../../../examples/probes/backend/rust/ir.rs"] pub mod ir;
#[path="../../../examples/probes/backend/rust/canonical.rs"] pub mod canonical;
#[path="../../../examples/probes/backend/rust/sha256.rs"] pub mod sha256;
#[path="../../../examples/probes/backend/rust/text_ir.rs"] pub mod text_ir;
#[path="../../../examples/probes/backend/rust/text_value.rs"] pub mod text_value;
#[path="../../../examples/probes/backend/rust/typed_text.rs"] pub mod typed_text;
#[path="../../../examples/probes/backend/rust/text_llvm.rs"] pub mod text_llvm;
fn source()->typed_text::CheckedSource{typed_text::checked_program(br#"{"schema":"bagaev-typed-text/1","entry":"main","functions":{"main":{"params":[],"result":"Int64","body":["text.bytes",["text","abc"]]}}}"#).unwrap()}
#[test]
fn canonical_binding_and_pins(){
 let p=source();let module=text_llvm::emit_program(&p).unwrap();let mut src=String::new();canonical::quote(std::str::from_utf8(p.canonical_bytes()).unwrap(),&mut src);
 let mut sig=String::new();canonical::quote(text_llvm::SIGNATURE,&mut sig);
 let desc=format!("{{\"execution_admission\":false,\"schema\":\"bagaev-text-llvm-binding/1\",\"signature\":{sig},\"source\":{src},\"source_pin\":\"{}\"}}",p.identity());
 let expected=format!("{{\"artifact_pin\":\"{}\",\"binding\":{desc},\"binding_pin\":\"{}\",\"module_bytes\":{},\"schema\":\"bagaev-text-llvm-module/1\"}}\n",sha256::digest(module.bytes()),sha256::digest(desc.as_bytes()),module.bytes().len());
 assert_eq!(module.binding_bytes(),expected.as_bytes());assert_eq!(module.identity(),sha256::digest(module.bytes()));
 let again=text_llvm::emit_program(&p).unwrap();assert_eq!(again.bytes(),module.bytes());assert_eq!(again.binding_bytes(),module.binding_bytes());
}
#[test]
fn emitter_bounds_are_environment_errors(){let p=source();assert!(matches!(text_llvm::emit_with_limits(&p,1,2*1024*1024),Err(text_llvm::EmitError::Bound)));assert!(matches!(text_llvm::emit_with_limits(&p,8*1024*1024,1),Err(text_llvm::EmitError::Bound)));}
