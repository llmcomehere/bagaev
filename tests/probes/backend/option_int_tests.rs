//! 17 pre-implementation wire cases plus three contract API tests.
#[path="../../../examples/probes/backend/rust/option_int.rs"] pub mod option_int;
use option_int::OptionInt64;
fn hex(s:&str)->Vec<u8>{assert!(s.len()%2==0);(0..s.len()).step_by(2).map(|i|u8::from_str_radix(&s[i..i+2],16).unwrap()).collect()}
#[test]
fn none(){let b=hex("00000000000000000000000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let v=r.unwrap();assert_eq!(v.is_some(),false);assert_eq!(v.value(),None);assert_eq!(v.encode().as_slice(),b);assert_eq!(b,before);}

#[test]
fn some_zero(){let b=hex("01000000000000000000000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let v=r.unwrap();assert_eq!(v.is_some(),true);assert_eq!(v.value(),Some(0));assert_eq!(v.encode().as_slice(),b);assert_eq!(b,before);}

#[test]
fn some_one(){let b=hex("01000000000000000100000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let v=r.unwrap();assert_eq!(v.is_some(),true);assert_eq!(v.value(),Some(1));assert_eq!(v.encode().as_slice(),b);assert_eq!(b,before);}

#[test]
fn some_min(){let b=hex("01000000000000000000000000000080");let before=b.clone();let r=OptionInt64::decode(&b);let v=r.unwrap();assert_eq!(v.is_some(),true);assert_eq!(v.value(),Some(-9223372036854775808));assert_eq!(v.encode().as_slice(),b);assert_eq!(b,before);}

#[test]
fn some_max(){let b=hex("0100000000000000ffffffffffffff7f");let before=b.clone();let r=OptionInt64::decode(&b);let v=r.unwrap();assert_eq!(v.is_some(),true);assert_eq!(v.value(),Some(9223372036854775807));assert_eq!(v.encode().as_slice(),b);assert_eq!(b,before);}

#[test]
fn empty(){let b=hex("");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_SIZE");assert_eq!(e.offset,0);assert_eq!(b,before);}

#[test]
fn short(){let b=hex("000000000000000000000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_SIZE");assert_eq!(e.offset,0);assert_eq!(b,before);}

#[test]
fn long(){let b=hex("0000000000000000000000000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_SIZE");assert_eq!(e.offset,0);assert_eq!(b,before);}

#[test]
fn flag_two(){let b=hex("02000000000000000000000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_FLAG");assert_eq!(e.offset,0);assert_eq!(b,before);}

#[test]
fn flag_ff(){let b=hex("ff000000000000000000000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_FLAG");assert_eq!(e.offset,0);assert_eq!(b,before);}

#[test]
fn padding_first(){let b=hex("00010000000000000000000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_PADDING");assert_eq!(e.offset,1);assert_eq!(b,before);}

#[test]
fn padding_last(){let b=hex("00000000000000010000000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_PADDING");assert_eq!(e.offset,7);assert_eq!(b,before);}

#[test]
fn none_one(){let b=hex("00000000000000000100000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_PAYLOAD");assert_eq!(e.offset,8);assert_eq!(b,before);}

#[test]
fn none_negative(){let b=hex("0000000000000000ffffffffffffffff");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_PAYLOAD");assert_eq!(e.offset,8);assert_eq!(b,before);}

#[test]
fn flag_before_padding(){let b=hex("02010000000000000000000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_FLAG");assert_eq!(e.offset,0);assert_eq!(b,before);}

#[test]
fn padding_before_payload(){let b=hex("00010000000000000100000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_PADDING");assert_eq!(e.offset,1);assert_eq!(b,before);}

#[test]
fn size_before_flag(){let b=hex("020000000000000000000000000000");let before=b.clone();let r=OptionInt64::decode(&b);let e=r.unwrap_err();assert_eq!(e.reason,"OPT_SIZE");assert_eq!(e.offset,0);assert_eq!(b,before);}

#[test] fn missing_fallback_called_once(){let mut calls=0;let v=OptionInt64::none().unwrap_or_else(||{calls+=1;17});assert_eq!(v,17);assert_eq!(calls,1);}
#[test] fn present_zero_never_calls_fallback(){let mut calls=0;let v=OptionInt64::some(0).unwrap_or_else(||{calls+=1;17});assert_eq!(v,0);assert_eq!(calls,0);}
#[test] fn equality_keeps_presence(){assert_ne!(OptionInt64::none(),OptionInt64::some(0));assert_eq!(OptionInt64::some(0),OptionInt64::some(0));assert_ne!(OptionInt64::some(0),OptionInt64::some(1));assert_eq!(OptionInt64::none(),OptionInt64::none());}
