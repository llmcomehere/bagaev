#[path="../../../examples/probes/backend/rust/text_value.rs"] pub mod text_value;
#[path="../../../examples/probes/backend/rust/option_int.rs"] pub mod option_int;
#[path="../../../examples/probes/backend/rust/option_callframe.rs"] pub mod option_callframe;
#[path="../../../examples/probes/backend/rust/option_native_adapter.rs"] pub mod option_native_adapter;
use option_callframe::Type;
use option_native_adapter::{NativeValue,Output};
use std::sync::atomic::{AtomicUsize,Ordering};
static CALLS:AtomicUsize=AtomicUsize::new(0);
unsafe extern "C" fn witness(_input:*const NativeValue,output:*mut Output){CALLS.fetch_add(1,Ordering::SeqCst);unsafe{output.write(Output{status:0,value_type:1,value:42,work:0,reason:0,location:0});}}
fn hex(s:&str)->Vec<u8>{assert!(s.len()%2==0);(0..s.len()).step_by(2).map(|i|u8::from_str_radix(&s[i..i+2],16).unwrap()).collect()}
fn frame(slots:&[(u32,&str)])->Vec<u8>{let mut b=vec![0u8;8272];b[..8].copy_from_slice(b"BTXTIN2\0");b[8..12].copy_from_slice(&(slots.len() as u32).to_le_bytes());for (i,(tag,s)) in slots.iter().enumerate(){let p=hex(s);let at=16+1032*i;b[at..at+4].copy_from_slice(&tag.to_le_bytes());b[at+4..at+8].copy_from_slice(&(p.len() as u32).to_le_bytes());b[at+8..at+8+p.len()].copy_from_slice(&p);}b}



#[test]
fn all_frozen_admission_cases(){
{
let mut b=frame(&[(4,"00000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"FRAME-NONE");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"01000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"FRAME-SOME-ZERO");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"01000000000000000100000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"FRAME-SOME-ONE");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"01000000000000000000000000000080")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"FRAME-SOME-MIN");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"0100000000000000ffffffffffffff7f")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"FRAME-SOME-MAX");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483668},"FRAME-EMPTY");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483668},"FRAME-SHORT");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"0000000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483668},"FRAME-LONG");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"02000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483672},"FRAME-FLAG-TWO");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"ff000000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483672},"FRAME-FLAG-FF");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"00010000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483673},"FRAME-PADDING-FIRST");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"00000000000000010000000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483679},"FRAME-PADDING-LAST");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"00000000000000000100000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483680},"FRAME-NONE-ONE");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"0000000000000000ffffffffffffffff")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483680},"FRAME-NONE-NEGATIVE");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"02010000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483672},"FRAME-FLAG-BEFORE-PADDING");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"00010000000000000100000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483673},"FRAME-PADDING-BEFORE-PAYLOAD");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"020000000000000000000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483668},"FRAME-SIZE-BEFORE-FLAG");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[]);
b[6..7].copy_from_slice(&hex("31"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483654},"FRAME-OLD-MAGIC");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"01000000000000000000000000000000"),(4,"01000000000000000100000000000000"),(4,"01000000000000000200000000000000"),(4,"01000000000000000300000000000000"),(4,"01000000000000000400000000000000"),(4,"01000000000000000500000000000000"),(4,"01000000000000000600000000000000"),(4,"01000000000000000700000000000000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64,Type::OptionInt64,Type::OptionInt64,Type::OptionInt64,Type::OptionInt64,Type::OptionInt64,Type::OptionInt64,Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"FRAME-EIGHT");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[(4,"02000000000000000000000000000000")]);
b[40..41].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::OptionInt64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483672},"FRAME-OPTION-BEFORE-TAIL");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"EMPTY");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[(1,"0000000000000080"),(1,"ffffffffffffff7f")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Int64,Type::Int64];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"INT-EXTREMES");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[(2,"00"),(2,"01")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Bool,Type::Bool];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"BOOLS");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[(3,"")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Text];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"TEXT-EMPTY");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[(3,"610062")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Text];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"TEXT-NUL");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[(3,"f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880f09f9880")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Text];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:0,value_type:1,value:42,work:0,reason:0,location:0},"TEXT-MAX");assert_eq!(CALLS.load(Ordering::SeqCst),1);
assert_eq!(b,before);
}
{
let mut b=frame(&[]);
b.resize(8271,0);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483648},"FRAME-SHORT");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[]);
b.resize(8273,0);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483648},"FRAME-LONG");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[]);
b[2..3].copy_from_slice(&hex("00"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483650},"MAGIC");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool,Type::Bool];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483656},"SIGNATURE");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[]);
b[8..12].copy_from_slice(&hex("09000000"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483656},"COUNT");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Bool];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483656},"COUNT-MISMATCH");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[]);
b[14..15].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483662},"RESERVED");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(1,"00")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Bool];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483664},"TAG");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(2,"0000")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Bool];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483668},"LENGTH");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(2,"02")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Bool];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483672},"BOOL-BAD");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(3,"c080")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Text];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483672},"TEXT-UTF8");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(3,"6161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161")]);
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Text];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483672},"TEXT-SCALARS");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(3,"")]);
b[20..24].copy_from_slice(&hex("01040000"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Text];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483668},"TEXT-BYTES");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(3,"61")]);
b[25..26].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Text];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483673},"PADDING");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[]);
b[1048..1049].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147484696},"UNUSED");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(2,"02")]);
b[25..26].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Bool];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483672},"PAYLOAD-BEFORE-PADDING");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(1,"")]);
b[20..24].copy_from_slice(&hex("ffffffff"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Bool];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483664},"TAG-BEFORE-LENGTH");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[]);
b[8..12].copy_from_slice(&hex("01000000"));
b[12..13].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483656},"COUNT-BEFORE-RESERVED");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
{
let mut b=frame(&[(2,"00"),(2,"02")]);
b[25..26].copy_from_slice(&hex("01"));
b.shrink_to_fit();let before=b.clone();CALLS.store(0,Ordering::SeqCst);
let signature:&[Type]=&[Type::Bool,Type::Bool];
let out=unsafe{option_native_adapter::evaluate(&b,signature,witness)};
assert_eq!(out,Output{status:3,value_type:0,value:0,work:0,reason:8,location:2147483673},"SLOT-ORDER");assert_eq!(CALLS.load(Ordering::SeqCst),0);
assert_eq!(b,before);
}
}
