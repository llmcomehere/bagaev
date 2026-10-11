//! Explicit source-once reference12 checks. No native dispatch.
pub mod transport; pub mod check; pub mod ir; pub mod canonical; pub mod sha256;
pub mod record_ir; pub mod option_int; pub mod text_value; pub mod text_list;
pub mod typed_record; pub mod text_inspection; pub mod int_projection;
pub mod record_value; pub mod type_graph; pub mod json_view;

#[cfg(test)]
mod tests {
 use super::*;
 fn source(version:u8,parameter:&str)->Vec<u8>{
  format!(r#"{{"schema":"bagaev-typed-record/{}","records":{{}},"lists":{{}},"variants":{{}},"entry":"main","functions":{{"main":{{"params":[["x","{}"]],"result":"Bool","body":["json.bool_or",["arg","x"],["bool",false]]}}}}}}"#,version,parameter).into_bytes()
 }
 fn invocation(source:&[u8],args:&[u8])->Vec<u8>{
  let mut v=b"{\"schema\":\"bagaev-typed-record-invocation/12\",\"program\":".to_vec();
  v.extend_from_slice(source);v.extend_from_slice(b",\"arguments\":");v.extend_from_slice(args);v.push(b'}');v
 }
 #[test]
 fn parity_ownership_and_reset(){
  let original=source(12,"Json");let mut disposable=original.clone();
  let p=typed_record::prepare_json_program_v12(&disposable).unwrap();disposable.fill(0);drop(disposable);
  let canonical=p.source().canonical_bytes().to_vec();
  for raw in ["[true]","[false]","[null]","[0]","[-0]","[0.0]","[1e0]","[\"true\"]","[{}]","[[]]"] {
   let expected=typed_record::process_v12(&invocation(&original,raw.as_bytes())).unwrap();
   let mut data=raw.as_bytes().to_vec();let call=typed_record::prepare_json_arguments_v12(&p,&data).unwrap();data.fill(0);drop(data);
   let owned=typed_record::evaluate_prepared_json_v12(&call).unwrap();assert_eq!(owned,expected);
   assert_eq!(typed_record::evaluate_prepared_json_v12(&call).unwrap(),expected);drop(call);
   assert_eq!(owned,expected);assert_eq!(p.source().canonical_bytes(),canonical);
  }
 }
 #[test]
 fn lazy_failure_parity(){
  let src=String::from_utf8(source(12,"Json")).unwrap().replace("[\"bool\",false]", "[\"eq\",[\"add\",[\"int\",9223372036854775807],[\"int\",1]],[\"int\",0]]");
  let p=typed_record::prepare_json_program_v12(src.as_bytes()).unwrap();
  for raw in ["[true]","[false]","[null]"] {
   let expected=typed_record::process_v12(&invocation(src.as_bytes(),raw.as_bytes())).unwrap();
   let call=typed_record::prepare_json_arguments_v12(&p,raw.as_bytes()).unwrap();
   assert_eq!(typed_record::evaluate_prepared_json_v12(&call).unwrap(),expected);
   assert_eq!(typed_record::evaluate_prepared_json_v12(&call).unwrap(),expected);
   assert!(String::from_utf8(expected).unwrap().contains(if raw=="[null]" {"integer-overflow"} else {"success"}));
  }
 }
 #[test]
 fn explicit_version_and_input_bounds(){
  let src=source(12,"Json");let p=typed_record::prepare_json_program_v12(&src).unwrap();
  assert!(typed_record::prepare_json_program_v12(&source(11,"Json")).is_err());
  assert!(typed_record::prepare_json_program_v11(&src).is_err());
  let non_json=String::from_utf8(source(12,"Int64")).unwrap().replace("[\"json.bool_or\",[\"arg\",\"x\"],[\"bool\",false]]", "[\"bool\",false]");
  assert_eq!(typed_record::prepare_json_program_v12(non_json.as_bytes()).err().unwrap(),"NATIVE_JSON_SIGNATURE");
  assert!(typed_record::prepare_json_program_v12(&vec![b' ';transport::FRAME_LIMIT+1]).is_err());
  for raw in [b"{}".as_slice(),b"[]",b"[",b"[true,false]",b"[{\"x\":0,\"x\":1}]"] {assert!(typed_record::prepare_json_arguments_v12(&p,raw).is_err());}
  let max=transport::FRAME_LIMIT-70-p.source().canonical_bytes().len();let mut raw=b"[0]".to_vec();raw.resize(max,b' ');
  assert!(typed_record::prepare_json_arguments_v12(&p,&raw).is_ok());raw.push(b' ');
  assert_eq!(typed_record::prepare_json_arguments_v12(&p,&raw).err().unwrap(),"PREPARED_FRAME_BOUNDS");
  let deep=format!("{}0{}","[".repeat(130),"]".repeat(130));
  assert!(typed_record::prepare_json_arguments_v12(&p,deep.as_bytes()).is_ok());
  let deeper=format!("{}0{}","[".repeat(131),"]".repeat(131));
  assert!(typed_record::prepare_json_arguments_v12(&p,deeper.as_bytes()).err().unwrap().contains("Bounds"));
  let n=16380-p.source_values();let mut raw=format!("[[{}]]",vec!["0";n].join(","));
  assert!(typed_record::prepare_json_arguments_v12(&p,raw.as_bytes()).is_ok());raw.insert_str(raw.len()-2,",0");
  assert_eq!(typed_record::prepare_json_arguments_v12(&p,raw.as_bytes()).err().unwrap(),"PREPARED_VALUE_BOUNDS");
 }
 #[test]
 fn work_limit_and_lazy_reset_literal_oracle(){
  // Inner loop costs1026; outer setup and projection cost4. 63 rounds=64642.
  for (count,arg,status,work,value,ty,location,reason) in [
   (63,"null","success",64642,"false","\"Bool\"","null","null"),
   (64,"null","work-limit",65536,"null","null","\"/program/functions/main/body/2/5/5\"","\"RR_WORK\""),
   (64,"true","success",2,"true","\"Bool\"","null","null")
  ] {
   let fallback=format!(r#"["loop",{},"i","a",["bool",false],["loop",1024,"j","b",["bool",false],["use","b"]]]"#,count);
   let src=String::from_utf8(source(12,"Json")).unwrap().replace("[\"bool\",false]",&fallback);
   let p=typed_record::prepare_json_program_v12(src.as_bytes()).unwrap();drop(src);
   let args=format!("[{}]",arg);let call=typed_record::prepare_json_arguments_v12(&p,args.as_bytes()).unwrap();drop(args);
   let expected=format!("{{\"location\":{},\"reason\":{},\"schema\":\"bagaev-typed-record-result/12\",\"status\":\"{}\",\"value\":{},\"value_type\":{},\"work\":{}}}\n",location,reason,status,value,ty,work).into_bytes();
   assert_eq!(typed_record::evaluate_prepared_json_v12(&call).unwrap(),expected);
   assert_eq!(typed_record::evaluate_prepared_json_v12(&call).unwrap(),expected);
  }
 }
}
