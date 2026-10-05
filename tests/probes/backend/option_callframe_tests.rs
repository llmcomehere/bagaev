//! 20 frozen optional-frame cases plus 25 explicit v2 adaptations of Text frames.
#[path="../../../examples/probes/backend/rust/text_value.rs"] pub mod text_value;
#[path="../../../examples/probes/backend/rust/option_int.rs"] pub mod option_int;
#[path="../../../examples/probes/backend/rust/option_callframe.rs"] pub mod option_callframe;
use option_callframe::{decode,Type,Value};
fn hex(s:&str)->Vec<u8>{assert!(s.len()%2==0);(0..s.len()).step_by(2).map(|i|u8::from_str_radix(&s[i..i+2],16).unwrap()).collect()}
fn frame(slots:&[(u32,&str)])->Vec<u8>{let mut b=vec![0u8;8272];b[..8].copy_from_slice(b"BTXTIN2\0");b[8..12].copy_from_slice(&(slots.len() as u32).to_le_bytes());for (i,(tag,s)) in slots.iter().enumerate(){let p=hex(s);let at=16+1032*i;b[at..at+4].copy_from_slice(&tag.to_le_bytes());b[at+4..at+8].copy_from_slice(&(p.len() as u32).to_le_bytes());b[at+8..at+8+p.len()].copy_from_slice(&p);}b}


#[test]
fn case_0_frame_none(){
let mut b=frame(&[(4,"00000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),1);assert!(a.get(1).is_none());
match a.get(0){Some(Value::Optional(v))=>{assert_eq!(v.value(),None);assert_eq!(v.is_some(),false);},_=>panic!("wrong type")}
assert_eq!(b,before);}

#[test]
fn case_1_frame_some_zero(){
let mut b=frame(&[(4,"01000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),1);assert!(a.get(1).is_none());
match a.get(0){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(0));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
assert_eq!(b,before);}

#[test]
fn case_2_frame_some_one(){
let mut b=frame(&[(4,"01000000000000000100000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),1);assert!(a.get(1).is_none());
match a.get(0){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(1));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
assert_eq!(b,before);}

#[test]
fn case_3_frame_some_min(){
let mut b=frame(&[(4,"01000000000000000000000000000080")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),1);assert!(a.get(1).is_none());
match a.get(0){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(-9223372036854775808));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
assert_eq!(b,before);}

#[test]
fn case_4_frame_some_max(){
let mut b=frame(&[(4,"0100000000000000ffffffffffffff7f")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),1);assert!(a.get(1).is_none());
match a.get(0){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(9223372036854775807));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
assert_eq!(b,before);}

#[test]
fn case_5_frame_empty(){
let mut b=frame(&[(4,"")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"ARG_LENGTH");assert_eq!(e.offset,20);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_6_frame_short(){
let mut b=frame(&[(4,"000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"ARG_LENGTH");assert_eq!(e.offset,20);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_7_frame_long(){
let mut b=frame(&[(4,"0000000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"ARG_LENGTH");assert_eq!(e.offset,20);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_8_frame_flag_two(){
let mut b=frame(&[(4,"02000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"OPTION_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_9_frame_flag_ff(){
let mut b=frame(&[(4,"ff000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"OPTION_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_10_frame_padding_first(){
let mut b=frame(&[(4,"00010000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"OPTION_VALUE");assert_eq!(e.offset,25);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_11_frame_padding_last(){
let mut b=frame(&[(4,"00000000000000010000000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"OPTION_VALUE");assert_eq!(e.offset,31);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_12_frame_none_one(){
let mut b=frame(&[(4,"00000000000000000100000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"OPTION_VALUE");assert_eq!(e.offset,32);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_13_frame_none_negative(){
let mut b=frame(&[(4,"0000000000000000ffffffffffffffff")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"OPTION_VALUE");assert_eq!(e.offset,32);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_14_frame_flag_before_padding(){
let mut b=frame(&[(4,"02010000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"OPTION_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_15_frame_padding_before_payload(){
let mut b=frame(&[(4,"00010000000000000100000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"OPTION_VALUE");assert_eq!(e.offset,25);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_16_frame_size_before_flag(){
let mut b=frame(&[(4,"020000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"ARG_LENGTH");assert_eq!(e.offset,20);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_17_frame_old_magic(){
let mut b=frame(&[]);
b[6..7].copy_from_slice(&hex("31"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"FRAME_MAGIC");assert_eq!(e.offset,6);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_18_frame_eight(){
let mut b=frame(&[(4,"01000000000000000000000000000000"),(4,"01000000000000000100000000000000"),(4,"01000000000000000200000000000000"),(4,"01000000000000000300000000000000"),(4,"01000000000000000400000000000000"),(4,"01000000000000000500000000000000"),(4,"01000000000000000600000000000000"),(4,"01000000000000000700000000000000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64,Type::OptionInt64,Type::OptionInt64,Type::OptionInt64,Type::OptionInt64,Type::OptionInt64,Type::OptionInt64,Type::OptionInt64];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),8);assert!(a.get(8).is_none());
match a.get(0){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(0));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
match a.get(1){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(1));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
match a.get(2){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(2));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
match a.get(3){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(3));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
match a.get(4){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(4));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
match a.get(5){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(5));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
match a.get(6){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(6));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
match a.get(7){Some(Value::Optional(v))=>{assert_eq!(v.value(),Some(7));assert_eq!(v.is_some(),true);},_=>panic!("wrong type")}
assert_eq!(b,before);}

#[test]
fn case_19_frame_option_before_tail(){
let mut b=frame(&[(4,"02000000000000000000000000000000")]);
b[40..41].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::OptionInt64];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"OPTION_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_20_empty(){
let mut b=frame(&[]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),0);assert!(a.get(0).is_none());
assert_eq!(b,before);}

#[test]
fn case_21_int_extremes(){
let mut b=frame(&[(1,"0000000000000080"),(1,"ffffffffffffff7f")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Int64,Type::Int64];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),2);assert!(a.get(2).is_none());
match a.get(0){Some(Value::Int64(v))=>assert_eq!(v,-9223372036854775808),_=>panic!("wrong type")}
match a.get(1){Some(Value::Int64(v))=>assert_eq!(v,9223372036854775807),_=>panic!("wrong type")}
assert_eq!(b,before);}

#[test]
fn case_22_bools(){
let mut b=frame(&[(2,"00"),(2,"01")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Bool,Type::Bool];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),2);assert!(a.get(2).is_none());
match a.get(0){Some(Value::Bool(v))=>assert_eq!(v,false),_=>panic!("wrong type")}
match a.get(1){Some(Value::Bool(v))=>assert_eq!(v,true),_=>panic!("wrong type")}
assert_eq!(b,before);}

#[test]
fn case_23_text_empty(){
let mut b=frame(&[(3,"")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Text];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),1);assert!(a.get(1).is_none());
match a.get(0){Some(Value::Text(v))=>{assert_eq!(v.bytes(),hex(""));assert_eq!(v.scalar_len(),0);assert_eq!(v.bytes().as_ptr(),b[24..].as_ptr());},_=>panic!("wrong type")}
assert_eq!(b,before);}

#[test]
fn case_24_text_nul(){
let mut b=frame(&[(3,"610062")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Text];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),1);assert!(a.get(1).is_none());
match a.get(0){Some(Value::Text(v))=>{assert_eq!(v.bytes(),hex("610062"));assert_eq!(v.scalar_len(),3);assert_eq!(v.bytes().as_ptr(),b[24..].as_ptr());},_=>panic!("wrong type")}
assert_eq!(b,before);}

#[test]
fn case_25_text_max(){
let mut b=frame(&[(3,"f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Text];let result=decode(&b,signature);
let a=result.unwrap();assert_eq!(a.len(),1);assert!(a.get(1).is_none());
match a.get(0){Some(Value::Text(v))=>{assert_eq!(v.bytes(),hex("f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880"));assert_eq!(v.scalar_len(),256);assert_eq!(v.bytes().as_ptr(),b[24..].as_ptr());},_=>panic!("wrong type")}
assert_eq!(b,before);}

#[test]
fn case_26_frame_short(){
let mut b=frame(&[]);
b.resize(8271,0);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"FRAME_SIZE");assert_eq!(e.offset,0);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_27_frame_long(){
let mut b=frame(&[]);
b.resize(8273,0);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"FRAME_SIZE");assert_eq!(e.offset,0);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_28_magic(){
let mut b=frame(&[]);
b[2..3].copy_from_slice(&hex("00"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"FRAME_MAGIC");assert_eq!(e.offset,2);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_29_signature(){
let mut b=frame(&[]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"SIGNATURE");assert_eq!(e.offset,8);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_30_count(){
let mut b=frame(&[]);
b[8..12].copy_from_slice(&hex("09000000"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"ARG_COUNT");assert_eq!(e.offset,8);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_31_count_mismatch(){
let mut b=frame(&[]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Bool];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"ARG_COUNT");assert_eq!(e.offset,8);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_32_reserved(){
let mut b=frame(&[]);
b[14..15].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"RESERVED");assert_eq!(e.offset,14);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_33_tag(){
let mut b=frame(&[(1,"00")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Bool];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"ARG_TAG");assert_eq!(e.offset,16);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_34_length(){
let mut b=frame(&[(2,"0000")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Bool];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"ARG_LENGTH");assert_eq!(e.offset,20);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_35_bool_bad(){
let mut b=frame(&[(2,"02")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Bool];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"BOOL_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_36_text_utf8(){
let mut b=frame(&[(3,"c080")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Text];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"TEXT_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_37_text_scalars(){
let mut b=frame(&[(3,"6161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161")]);
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Text];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"TEXT_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_38_text_bytes(){
let mut b=frame(&[(3,"")]);
b[20..24].copy_from_slice(&hex("01040000"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Text];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"ARG_LENGTH");assert_eq!(e.offset,20);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_39_padding(){
let mut b=frame(&[(3,"61")]);
b[25..26].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Text];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"PADDING");assert_eq!(e.offset,25);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_40_unused(){
let mut b=frame(&[]);
b[1048..1049].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"UNUSED");assert_eq!(e.offset,1048);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_41_payload_before_padding(){
let mut b=frame(&[(2,"02")]);
b[25..26].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Bool];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"BOOL_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_42_tag_before_length(){
let mut b=frame(&[(1,"")]);
b[20..24].copy_from_slice(&hex("ffffffff"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Bool];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"ARG_TAG");assert_eq!(e.offset,16);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_43_count_before_reserved(){
let mut b=frame(&[]);
b[8..12].copy_from_slice(&hex("01000000"));
b[12..13].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"ARG_COUNT");assert_eq!(e.offset,8);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}

#[test]
fn case_44_slot_order(){
let mut b=frame(&[(2,"00"),(2,"02")]);
b[25..26].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();let signature:&[Type]=&[Type::Bool,Type::Bool];let result=decode(&b,signature);
match result{Err(e)=>{assert_eq!(e.reason,"PADDING");assert_eq!(e.offset,25);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);}
