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


pub mod composite_result_decode_v11;
pub mod native_result_json_v11;
#[cfg(test)]
mod tests{
 use super::*;
 fn source(result:&str,body:&str,records:&str)->Vec<u8>{format!("{{\"schema\":\"bagaev-typed-record/11\",\"records\":{},\"lists\":{{}},\"variants\":{{}},\"entry\":\"main\",\"functions\":{{\"main\":{{\"params\":[],\"result\":\"{}\",\"body\":{}}}}}}}",records,result,body).into_bytes()}
 fn node(tag:u32,nominal:u32,scalar:i64,end:u32,count:u32,offset:u32,len:u32)->[u8;32]{let mut n=[0;32];n[..4].copy_from_slice(&tag.to_le_bytes());n[4..8].copy_from_slice(&nominal.to_le_bytes());n[8..16].copy_from_slice(&scalar.to_le_bytes());for(i,v)in[end,count,offset,len].iter().enumerate(){n[16+4*i..20+4*i].copy_from_slice(&v.to_le_bytes());}n}
 fn wire(source:&[u8],nodes:&[[u8;32]],text:&[u8])->Vec<u8>{
  let p=typed_record::prepare_json_program_v11(source).unwrap();let hex=&p.source().identity()[7..];let mut w=vec![0;64];w[..8].copy_from_slice(b"BCMPRES4");w[8..12].copy_from_slice(&(nodes.len() as u32).to_le_bytes());w[12..16].copy_from_slice(&(text.len() as u32).to_le_bytes());w[16..24].copy_from_slice(&7u64.to_le_bytes());for i in 0..32{w[24+i]=u8::from_str_radix(&hex[2*i..2*i+2],16).unwrap();}for n in nodes{w.extend_from_slice(n);}w.extend_from_slice(text);w
 }
 fn value(source:&[u8],wire:&[u8])->String{
  let raw=native_result_json_v11::decode_success(source,wire).unwrap();let text=String::from_utf8(raw).unwrap();let at=text.find(",\"value\":").unwrap()+9;text[at..text.len()-1].to_owned()
 }
 #[test]
 fn primitive_values(){
  let s=source("Int64","[\"int\",-9223372036854775808]","{}");assert_eq!(value(&s,&wire(&s,&[node(1,0,i64::MIN,1,0,0,0)],b"")),"-9223372036854775808");
  let s=source("Bool","[\"bool\",true]","{}");assert_eq!(value(&s,&wire(&s,&[node(2,0,1,1,0,0,0)],b"")),"true");
  let s=source("OptionInt64","[\"none.int\"]","{}");assert_eq!(value(&s,&wire(&s,&[node(4,0,0,1,0,0,0)],b"")),"null");assert_eq!(value(&s,&wire(&s,&[node(9,0,-7,1,0,0,0)],b"")),"-7");
 }
 #[test]
 fn optional_omission_and_scalar_escaping(){
  let records=r#"{"D":{"a":{"type":"OptionInt64","omit_none":true},"b":"OptionInt64","c":"Text"}}"#;
  let s=source("D",r#"["record","D",["none.int"],["none.int"],["text",""]]"#,records);
  let text="\"\\\nЖ😀".as_bytes();let mut nodes=vec![node(6,0,0,4,3,0,0),node(4,0,0,2,0,0,0),node(4,0,0,3,0,0,0),node(3,0,0,4,0,0,text.len() as u32)];
  let mut quoted=String::new();canonical::quote(std::str::from_utf8(text).unwrap(),&mut quoted);
  assert_eq!(value(&s,&wire(&s,&nodes,text)),format!("{{\"b\":null,\"c\":{}}}",quoted));
  nodes[1]=node(9,0,12,2,0,0,0);assert_eq!(value(&s,&wire(&s,&nodes,text)),format!("{{\"a\":12,\"b\":null,\"c\":{}}}",quoted));
 }
 #[test]
 fn text_list_and_malformed_text(){
  let s=source("TextList",r#"["list.text",["text","a"],["text","b"]]"#,"{}");let nodes=[node(5,0,0,3,2,0,0),node(3,0,0,2,0,0,1),node(3,0,0,3,0,1,1)];let w=wire(&s,&nodes,b"ab");assert_eq!(value(&s,&w),"[\"a\",\"b\"]");
  let mut bad=w.clone();*bad.last_mut().unwrap()=255;assert!(matches!(native_result_json_v11::decode_success(&s,&bad),Err(native_result_json_v11::Error::Wire(_))));
  let mut bad=w.clone();bad[64+32+24..64+32+28].copy_from_slice(&1u32.to_le_bytes());assert!(native_result_json_v11::decode_success(&s,&bad).is_err());
  let mut bad=w.clone();bad[64+32+28..64+32+32].copy_from_slice(&256u32.to_le_bytes());assert!(native_result_json_v11::decode_success(&s,&bad).is_err());
 }
}
