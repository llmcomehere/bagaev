//! Literal call-frame cases frozen before decoder implementation.
//! Fixture SHA256: 58863f3a65e9f6065b3608deac10626cbe9a2a2d49487d05df25ceb9b06cb5c9
#[path="../../../examples/probes/backend/rust/text_value.rs"] pub mod text_value;
#[path="../../../examples/probes/backend/rust/text_callframe.rs"] pub mod text_callframe;
use text_callframe::{decode,Type,Value};
fn hex(s:&str)->Vec<u8>{assert!(s.len()%2==0);(0..s.len()).step_by(2).map(|i|u8::from_str_radix(&s[i..i+2],16).unwrap()).collect()}
fn frame(slots:&[(u32,&str)])->Vec<u8>{let mut b=vec![0u8;8272];b[..8].copy_from_slice(b"BTXTIN1\0");b[8..12].copy_from_slice(&(slots.len() as u32).to_le_bytes());for (i,(tag,s)) in slots.iter().enumerate(){let p=hex(s);let at=16+1032*i;b[at..at+4].copy_from_slice(&tag.to_le_bytes());b[at+4..at+8].copy_from_slice(&(p.len() as u32).to_le_bytes());b[at+8..at+8+p.len()].copy_from_slice(&p);}b}

#[test]
fn empty(){
let mut b=frame(&[]);
b.shrink_to_fit();
let before=b.clone();
let signature=[];
let r=decode(&b,&signature);
let args=r.unwrap();
assert_eq!(args.len(),0);
assert_eq!(args.is_empty(),true);
assert!(args.get(0).is_none());
assert_eq!(b,before);
}
#[test]
fn int_extremes(){
let mut b=frame(&[(1,"0000000000000080"),(1,"ffffffffffffff7f")]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Int64,Type::Int64];
let r=decode(&b,&signature);
let args=r.unwrap();
assert_eq!(args.len(),2);
assert_eq!(args.is_empty(),false);
assert!(args.get(2).is_none());
match args.get(0){Some(Value::Int64(v))=>assert_eq!(v,-9223372036854775808),_=>panic!("wrong type")}
match args.get(1){Some(Value::Int64(v))=>assert_eq!(v,9223372036854775807),_=>panic!("wrong type")}
assert_eq!(b,before);
}
#[test]
fn bools(){
let mut b=frame(&[(2,"00"),(2,"01")]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Bool,Type::Bool];
let r=decode(&b,&signature);
let args=r.unwrap();
assert_eq!(args.len(),2);
assert_eq!(args.is_empty(),false);
assert!(args.get(2).is_none());
match args.get(0){Some(Value::Bool(v))=>assert_eq!(v,false),_=>panic!("wrong type")}
match args.get(1){Some(Value::Bool(v))=>assert_eq!(v,true),_=>panic!("wrong type")}
assert_eq!(b,before);
}
#[test]
fn text_empty(){
let mut b=frame(&[(3,"")]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Text];
let r=decode(&b,&signature);
let args=r.unwrap();
assert_eq!(args.len(),1);
assert_eq!(args.is_empty(),false);
assert!(args.get(1).is_none());
match args.get(0){Some(Value::Text(t))=>{assert_eq!(t.bytes(),hex(""));assert_eq!(t.scalar_len(),0);assert_eq!(t.bytes().as_ptr(),b[24..].as_ptr());},_=>panic!("wrong type")}
assert_eq!(b,before);
}
#[test]
fn text_nul(){
let mut b=frame(&[(3,"610062")]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Text];
let r=decode(&b,&signature);
let args=r.unwrap();
assert_eq!(args.len(),1);
assert_eq!(args.is_empty(),false);
assert!(args.get(1).is_none());
match args.get(0){Some(Value::Text(t))=>{assert_eq!(t.bytes(),hex("610062"));assert_eq!(t.scalar_len(),3);assert_eq!(t.bytes().as_ptr(),b[24..].as_ptr());},_=>panic!("wrong type")}
assert_eq!(b,before);
}
#[test]
fn text_max(){
let mut b=frame(&[(3,"f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880")]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Text];
let r=decode(&b,&signature);
let args=r.unwrap();
assert_eq!(args.len(),1);
assert_eq!(args.is_empty(),false);
assert!(args.get(1).is_none());
match args.get(0){Some(Value::Text(t))=>{assert_eq!(t.bytes(),hex("f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880"));assert_eq!(t.scalar_len(),256);assert_eq!(t.bytes().as_ptr(),b[24..].as_ptr());},_=>panic!("wrong type")}
assert_eq!(b,before);
}
#[test]
fn frame_short(){
let mut b=frame(&[]);
b.resize(8271,0);
b.shrink_to_fit();
let before=b.clone();
let signature=[];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"FRAME_SIZE");assert_eq!(e.offset,0);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn frame_long(){
let mut b=frame(&[]);
b.resize(8273,0);
b.shrink_to_fit();
let before=b.clone();
let signature=[];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"FRAME_SIZE");assert_eq!(e.offset,0);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn magic(){
let mut b=frame(&[]);
b[2..3].copy_from_slice(&hex("00"));
b.shrink_to_fit();
let before=b.clone();
let signature=[];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"FRAME_MAGIC");assert_eq!(e.offset,2);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn signature(){
let mut b=frame(&[]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"SIGNATURE");assert_eq!(e.offset,8);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn count(){
let mut b=frame(&[]);
b[8..12].copy_from_slice(&hex("09000000"));
b.shrink_to_fit();
let before=b.clone();
let signature=[];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"ARG_COUNT");assert_eq!(e.offset,8);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn count_mismatch(){
let mut b=frame(&[]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Bool];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"ARG_COUNT");assert_eq!(e.offset,8);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn reserved(){
let mut b=frame(&[]);
b[14..15].copy_from_slice(&hex("01"));
b.shrink_to_fit();
let before=b.clone();
let signature=[];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"RESERVED");assert_eq!(e.offset,14);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn tag(){
let mut b=frame(&[(1,"00")]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Bool];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"ARG_TAG");assert_eq!(e.offset,16);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn length(){
let mut b=frame(&[(2,"0000")]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Bool];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"ARG_LENGTH");assert_eq!(e.offset,20);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn bool_bad(){
let mut b=frame(&[(2,"02")]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Bool];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"BOOL_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn text_utf8(){
let mut b=frame(&[(3,"c080")]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Text];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"TEXT_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn text_scalars(){
let mut b=frame(&[(3,"6161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161")]);
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Text];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"TEXT_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn text_bytes(){
let mut b=frame(&[(3,"")]);
b[20..24].copy_from_slice(&hex("01040000"));
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Text];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"ARG_LENGTH");assert_eq!(e.offset,20);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn padding(){
let mut b=frame(&[(3,"61")]);
b[25..26].copy_from_slice(&hex("01"));
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Text];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"PADDING");assert_eq!(e.offset,25);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn unused(){
let mut b=frame(&[]);
b[1048..1049].copy_from_slice(&hex("01"));
b.shrink_to_fit();
let before=b.clone();
let signature=[];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"UNUSED");assert_eq!(e.offset,1048);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn payload_before_padding(){
let mut b=frame(&[(2,"02")]);
b[25..26].copy_from_slice(&hex("01"));
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Bool];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"BOOL_VALUE");assert_eq!(e.offset,24);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn tag_before_length(){
let mut b=frame(&[(1,"")]);
b[20..24].copy_from_slice(&hex("ffffffff"));
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Bool];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"ARG_TAG");assert_eq!(e.offset,16);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn count_before_reserved(){
let mut b=frame(&[]);
b[8..12].copy_from_slice(&hex("01000000"));
b[12..13].copy_from_slice(&hex("01"));
b.shrink_to_fit();
let before=b.clone();
let signature=[];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"ARG_COUNT");assert_eq!(e.offset,8);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
#[test]
fn slot_order(){
let mut b=frame(&[(2,"00"),(2,"02")]);
b[25..26].copy_from_slice(&hex("01"));
b.shrink_to_fit();
let before=b.clone();
let signature=[Type::Bool,Type::Bool];
let r=decode(&b,&signature);
match r {Err(e)=>{assert_eq!(e.reason,"PADDING");assert_eq!(e.offset,25);},Ok(_)=>panic!("expected refusal")}
assert_eq!(b,before);
}
