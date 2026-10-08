//! Explicit prepared-reference conformance tests. No native dispatch.
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


#[cfg(test)]
mod tests {
 use super::*;
 fn invocation(source:&[u8],arguments:&[u8],version:u8)->Vec<u8>{
  let mut out=format!("{{\"schema\":\"bagaev-typed-record-invocation/{}\",\"program\":",version).into_bytes();
  out.extend_from_slice(source);out.extend_from_slice(b",\"arguments\":");out.extend_from_slice(arguments);out.push(b'}');out
 }
 fn simple(version:u8,parameter:&str)->Vec<u8>{
  format!("{{\"schema\":\"bagaev-typed-record/{}\",\"records\":{{}},\"lists\":{{}},\"variants\":{{}},\"entry\":\"main\",\"functions\":{{\"main\":{{\"params\":[[\"x\",\"{}\"]],\"result\":\"Int64\",\"body\":[\"int\",0]}}}}}}",version,parameter).into_bytes()
 }
 #[test]
 fn business_parity_and_ownership(){
  let cases:[(&[u8],&[u8],usize);2]=[
   (include_bytes!("../../inventory-batch/program.json"),include_bytes!("../../prepared-json11/original.arguments.jsonl"),32),
   (include_bytes!("../../inventory-batch-change/program.json"),include_bytes!("../../prepared-json11/total10.arguments.jsonl"),40)];
  let mut full=0;let mut prepared=0;
  for (source,lines,count) in cases {
   let mut disposable=source.to_vec();let p=typed_record::prepare_json_program_v11(&disposable).unwrap();disposable.fill(0);drop(disposable);
   let canonical=p.source().canonical_bytes().to_vec();let mut n=0;
   for (i,line) in lines.split(|x|*x==b'\n').filter(|x|!x.is_empty()).enumerate(){
    let expected=typed_record::process_v11(&invocation(source,line,11)).unwrap();full+=1;
    let mut raw=line.to_vec();let call=typed_record::prepare_json_arguments_v11(&p,&raw).unwrap();raw.fill(0);drop(raw);
    let actual=typed_record::evaluate_prepared_json_v11(&call).unwrap();prepared+=1;assert_eq!(actual,expected);
    if i==3{assert_eq!(typed_record::evaluate_prepared_json_v11(&call).unwrap(),expected);prepared+=1;}
    drop(call);assert_eq!(actual,expected);assert_eq!(p.source().canonical_bytes(),canonical);n+=1;
   }
   assert_eq!(n,count);
  }
  assert_eq!((full,prepared),(72,74));println!("business full={} prepared={}",full,prepared);
 }
 #[test]
 fn failure_parity_and_work_reset(){
  let fixtures:[&[u8];5]=[include_bytes!("../../native-source-locations/add-overflow.json"),include_bytes!("../../native-source-locations/subtract-underflow.json"),include_bytes!("../../native-source-locations/empty-index.json"),include_bytes!("../../native-source-locations/push-seventeenth.json"),include_bytes!("../../native-source-locations/work-limit.json")];
  for input in fixtures {
   let checked=typed_record::checked_json_invocation_v11(input).unwrap();let p=typed_record::prepare_json_program_v11(checked.program().canonical_bytes()).unwrap();drop(checked);
   let call=typed_record::prepare_json_arguments_v11(&p,b"[]").unwrap();let expected=typed_record::process_v11(input).unwrap();
   assert_eq!(typed_record::evaluate_prepared_json_v11(&call).unwrap(),expected);
   assert_eq!(typed_record::evaluate_prepared_json_v11(&call).unwrap(),expected);
  }
  println!("runtime-failure full=5 prepared=10");
 }
 #[test]
 fn admission_bounds_and_old_profile(){
  let source=simple(11,"Json");let p=typed_record::prepare_json_program_v11(&source).unwrap();
  assert!(typed_record::prepare_json_program_v11(&simple(10,"Json")).is_err());
  assert_eq!(typed_record::prepare_json_program_v11(&simple(11,"Int64")).err().unwrap(),"NATIVE_JSON_SIGNATURE");
  assert!(typed_record::prepare_json_program_v11(&vec![b' ';transport::FRAME_LIMIT+1]).is_err());
  assert_eq!(typed_record::prepare_json_arguments_v11(&p,b"{}").err().unwrap(),"PREPARED_ARGUMENT_ARRAY");
  assert_eq!(typed_record::prepare_json_arguments_v11(&p,b"[]").err().unwrap(),"PREPARED_ARGUMENT_ARITY");
  assert!(typed_record::prepare_json_arguments_v11(&p,b"[").is_err());
  let max=transport::FRAME_LIMIT-70-p.source().canonical_bytes().len();let mut raw=b"[0]".to_vec();raw.resize(max,b' ');
  assert!(typed_record::prepare_json_arguments_v11(&p,&raw).is_ok());raw.push(b' ');
  assert_eq!(typed_record::prepare_json_arguments_v11(&p,&raw).err().unwrap(),"PREPARED_FRAME_BOUNDS");
  let n=16380-p.source_values();let mut values=String::from("[[");values.push_str(&vec!["0";n].join(","));values.push_str("]]");
  assert!(typed_record::prepare_json_arguments_v11(&p,values.as_bytes()).is_ok());
  values.insert_str(values.len()-2,",0");assert_eq!(typed_record::prepare_json_arguments_v11(&p,values.as_bytes()).err().unwrap(),"PREPARED_VALUE_BOUNDS");
  let deep=format!("{}0{}","[".repeat(130),"]".repeat(130));assert!(typed_record::prepare_json_arguments_v11(&p,deep.as_bytes()).is_ok());
  let too_deep=format!("{}0{}","[".repeat(131),"]".repeat(131));assert!(typed_record::prepare_json_arguments_v11(&p,too_deep.as_bytes()).err().unwrap().contains("Bounds"));
  let old_source=simple(10,"Json");let old=typed_record::prepare_json_program_v10(&old_source).unwrap();let call=typed_record::prepare_json_arguments_v10(&old,b"[0]").unwrap();
  assert_eq!(typed_record::evaluate_prepared_json_v10(&call).unwrap(),typed_record::process_v10(&invocation(&old_source,b"[0]",10)).unwrap());
  println!("admission refusals=9 exact-boundary-successes=3 legacy-full=1 legacy-prepared=1");
 }
}
