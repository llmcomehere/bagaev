//! Literal tests mechanically transcribed from the frozen text-value-cases/1.
//! Fixture SHA-256: 6613df4712977c093f06654e70e0a9dd0564a2865b6df478c1b530e0ae6bed24
#[path = "../../../examples/probes/backend/rust/text_value.rs"] pub mod text_value;
use text_value::Text;
#[test]
fn t_empty() {
 let input:Vec<u8>=vec![];let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),0);assert_eq!(text.scalar_len(),0);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_ascii() {
 let input:Vec<u8>=vec![65,98];let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),2);assert_eq!(text.scalar_len(),2);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_two_byte() {
 let input:Vec<u8>=vec![195,169];let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),2);assert_eq!(text.scalar_len(),1);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_three_byte() {
 let input:Vec<u8>=vec![226,130,172];let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),3);assert_eq!(text.scalar_len(),1);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_four_byte() {
 let input:Vec<u8>=vec![240,144,128,128];let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),4);assert_eq!(text.scalar_len(),1);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_combining() {
 let input:Vec<u8>=vec![101,204,129];let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),3);assert_eq!(text.scalar_len(),2);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_nul() {
 let input:Vec<u8>=vec![97,0,98];let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),3);assert_eq!(text.scalar_len(),3);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_controls() {
 let input:Vec<u8>=vec![0,10,31,127];let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),4);assert_eq!(text.scalar_len(),4);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_max_scalar() {
 let input:Vec<u8>=vec![244,143,191,191];let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),4);assert_eq!(text.scalar_len(),1);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_noncharacter() {
 let input:Vec<u8>=vec![239,191,190];let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),3);assert_eq!(text.scalar_len(),1);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_continuation() {
 let input:Vec<u8>=vec![128];let before=input.clone();
 assert_eq!(Text::from_bytes(&input).unwrap_err().code(),"TEXT_UTF8");
 assert_eq!(input,before);
}
#[test]
fn t_truncated() {
 let input:Vec<u8>=vec![226,130];let before=input.clone();
 assert_eq!(Text::from_bytes(&input).unwrap_err().code(),"TEXT_UTF8");
 assert_eq!(input,before);
}
#[test]
fn t_overlong() {
 let input:Vec<u8>=vec![192,128];let before=input.clone();
 assert_eq!(Text::from_bytes(&input).unwrap_err().code(),"TEXT_UTF8");
 assert_eq!(input,before);
}
#[test]
fn t_surrogate() {
 let input:Vec<u8>=vec![237,160,128];let before=input.clone();
 assert_eq!(Text::from_bytes(&input).unwrap_err().code(),"TEXT_UTF8");
 assert_eq!(input,before);
}
#[test]
fn t_too_high() {
 let input:Vec<u8>=vec![244,144,128,128];let before=input.clone();
 assert_eq!(Text::from_bytes(&input).unwrap_err().code(),"TEXT_UTF8");
 assert_eq!(input,before);
}
#[test]
fn t_bad_continuation() {
 let input:Vec<u8>=vec![195,65];let before=input.clone();
 assert_eq!(Text::from_bytes(&input).unwrap_err().code(),"TEXT_UTF8");
 assert_eq!(input,before);
}
#[test]
fn t_scalar_limit() {
 let input:Vec<u8>=vec![97].repeat(256);let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),256);assert_eq!(text.scalar_len(),256);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_scalar_over() {
 let input:Vec<u8>=vec![97].repeat(257);let before=input.clone();
 assert_eq!(Text::from_bytes(&input).unwrap_err().code(),"TEXT_SCALARS");
 assert_eq!(input,before);
}
#[test]
fn t_both_limits() {
 let input:Vec<u8>=vec![240,144,128,128].repeat(256);let before=input.clone();
 let text=Text::from_bytes(&input).unwrap();
 assert_eq!(text.byte_len(),1024);assert_eq!(text.scalar_len(),256);
 assert_eq!(text.bytes(),input.as_slice());assert_eq!(text.bytes().as_ptr(),input.as_ptr());
 assert_eq!(input,before);
}
#[test]
fn t_byte_over() {
 let input:Vec<u8>=vec![97].repeat(1025);let before=input.clone();
 assert_eq!(Text::from_bytes(&input).unwrap_err().code(),"TEXT_BYTES");
 assert_eq!(input,before);
}
#[test]
fn t_bytes_before_utf8() {
 let input:Vec<u8>=vec![255].repeat(1025);let before=input.clone();
 assert_eq!(Text::from_bytes(&input).unwrap_err().code(),"TEXT_BYTES");
 assert_eq!(input,before);
}
#[test]
fn t_utf8_before_scalars() {
 let input:Vec<u8>=vec![255].repeat(257);let before=input.clone();
 assert_eq!(Text::from_bytes(&input).unwrap_err().code(),"TEXT_UTF8");
 assert_eq!(input,before);
}
#[test]
fn c_empty() {
 let left:Vec<u8>=vec![];let right:Vec<u8>=vec![];
 let a=Text::from_bytes(&left).unwrap();let b=Text::from_bytes(&right).unwrap();
 assert_eq!(a.compare(b),0);assert_eq!(a.equal(b),true);
 assert_eq!(b.compare(a),0);assert_eq!(b.equal(a),true);
}
#[test]
fn c_equal() {
 let left:Vec<u8>=vec![195,169];let right:Vec<u8>=vec![195,169];
 let a=Text::from_bytes(&left).unwrap();let b=Text::from_bytes(&right).unwrap();
 assert_eq!(a.compare(b),0);assert_eq!(a.equal(b),true);
 assert_eq!(b.compare(a),0);assert_eq!(b.equal(a),true);
}
#[test]
fn c_prefix() {
 let left:Vec<u8>=vec![97];let right:Vec<u8>=vec![97,98];
 let a=Text::from_bytes(&left).unwrap();let b=Text::from_bytes(&right).unwrap();
 assert_eq!(a.compare(b),-1);assert_eq!(a.equal(b),false);
 assert_eq!(b.compare(a),1);assert_eq!(b.equal(a),false);
}
#[test]
fn c_reverse() {
 let left:Vec<u8>=vec![97,98];let right:Vec<u8>=vec![97];
 let a=Text::from_bytes(&left).unwrap();let b=Text::from_bytes(&right).unwrap();
 assert_eq!(a.compare(b),1);assert_eq!(a.equal(b),false);
 assert_eq!(b.compare(a),-1);assert_eq!(b.equal(a),false);
}
#[test]
fn c_nul() {
 let left:Vec<u8>=vec![97,0];let right:Vec<u8>=vec![97];
 let a=Text::from_bytes(&left).unwrap();let b=Text::from_bytes(&right).unwrap();
 assert_eq!(a.compare(b),1);assert_eq!(a.equal(b),false);
 assert_eq!(b.compare(a),-1);assert_eq!(b.equal(a),false);
}
#[test]
fn c_normalization() {
 let left:Vec<u8>=vec![195,169];let right:Vec<u8>=vec![101,204,129];
 let a=Text::from_bytes(&left).unwrap();let b=Text::from_bytes(&right).unwrap();
 assert_eq!(a.compare(b),1);assert_eq!(a.equal(b),false);
 assert_eq!(b.compare(a),-1);assert_eq!(b.equal(a),false);
}
#[test]
fn c_utf16_trap() {
 let left:Vec<u8>=vec![238,128,128];let right:Vec<u8>=vec![240,144,128,128];
 let a=Text::from_bytes(&left).unwrap();let b=Text::from_bytes(&right).unwrap();
 assert_eq!(a.compare(b),-1);assert_eq!(a.equal(b),false);
 assert_eq!(b.compare(a),1);assert_eq!(b.equal(a),false);
}
#[test]
fn c_case() {
 let left:Vec<u8>=vec![65];let right:Vec<u8>=vec![97];
 let a=Text::from_bytes(&left).unwrap();let b=Text::from_bytes(&right).unwrap();
 assert_eq!(a.compare(b),-1);assert_eq!(a.equal(b),false);
 assert_eq!(b.compare(a),1);assert_eq!(b.equal(a),false);
}
