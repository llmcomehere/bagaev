//! Generic staged projection; it does not decide an application's refusal phase.
use crate::transport::Value;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum IntProjection { Missing, Present(i64), Invalid }
pub fn project_int(value: Option<&Value>) -> IntProjection {
    let token=match value {
        None=>return IntProjection::Missing,
        Some(Value::Integer(token))=>token,
        Some(_)=>return IntProjection::Invalid,
    };
    if token.is_empty() || token.len()>20 {return IntProjection::Invalid;}
    let bytes=token.as_bytes();
    let digits=if bytes[0]==b'-' {&bytes[1..]} else {bytes};
    if digits.is_empty() || !digits.iter().all(u8::is_ascii_digit)
        || (digits.len()>1 && digits[0]==b'0') {return IntProjection::Invalid;}
    match token.parse::<i64>() {Ok(n)=>IntProjection::Present(n),Err(_)=>IntProjection::Invalid}
}
