//! Portable bounded input data for a optional-Int64 native probe boundary.
//! No function pointers, compiler invocation or execution admission.
use crate::text_value::Text;
pub const FRAME_SIZE: usize = 8272;
const SLOT_SIZE: usize = 1032;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Type { Int64, Bool, Text, OptionInt64 }
#[derive(Clone, Copy)]
pub enum Value<'a> { Int64(i64), Bool(bool), Text(Text<'a>), Optional(crate::option_int::OptionInt64) }
#[derive(Debug, PartialEq, Eq)]
pub struct Refusal { pub reason: &'static str, pub offset: usize }
pub struct Arguments<'a> { values: [Option<Value<'a>>; 8], len: usize }
impl<'a> Arguments<'a> {
    pub fn len(&self) -> usize { self.len }
    pub fn is_empty(&self) -> bool { self.len == 0 }
    pub fn get(&self, index: usize) -> Option<Value<'a>> {
        if index < self.len { self.values[index] } else { None }
    }
}
fn bad(reason: &'static str, offset: usize) -> Refusal { Refusal { reason, offset } }
fn word(bytes: &[u8], at: usize) -> u32 {
    u32::from_le_bytes([bytes[at], bytes[at+1], bytes[at+2], bytes[at+3]])
}
/// Decode borrowed values after checking the entire immutable frame.
/// The expected signature must come from the caller's checked program.
pub fn decode<'a>(bytes: &'a [u8], signature: &[Type]) -> Result<Arguments<'a>, Refusal> {
    if bytes.len() != FRAME_SIZE { return Err(bad("FRAME_SIZE", 0)); }
    for (i, expected) in b"BTXTIN2\0".iter().enumerate() {
        if bytes[i] != *expected { return Err(bad("FRAME_MAGIC", i)); }
    }
    if signature.len() > 8 { return Err(bad("SIGNATURE", 8)); }
    let count = word(bytes, 8) as usize;
    if count > 8 || count != signature.len() { return Err(bad("ARG_COUNT", 8)); }
    for (i, b) in bytes[12..16].iter().enumerate() {
        if *b != 0 { return Err(bad("RESERVED", 12+i)); }
    }
    let mut values = [None; 8];
    for index in 0..8 {
        let start = 16 + index * SLOT_SIZE;
        if index >= count {
            for (i, b) in bytes[start..start+SLOT_SIZE].iter().enumerate() {
                if *b != 0 { return Err(bad("UNUSED", start+i)); }
            }
            continue;
        }
        let tag = word(bytes, start);
        let expected = match signature[index] { Type::Int64=>1, Type::Bool=>2, Type::Text=>3, Type::OptionInt64=>4 };
        if tag != expected { return Err(bad("ARG_TAG", start)); }
        let len = word(bytes, start+4) as usize;
        if match signature[index] { Type::Int64=>len!=8, Type::Bool=>len!=1, Type::Text=>len>1024, Type::OptionInt64=>len!=16 } {
            return Err(bad("ARG_LENGTH", start+4));
        }
        let payload = &bytes[start+8..start+8+len];
        let value = match signature[index] {
            Type::OptionInt64=>Value::Optional(crate::option_int::OptionInt64::decode(payload).map_err(|e|bad("OPTION_VALUE",start+8+e.offset))?),
            Type::Int64 => Value::Int64(i64::from_le_bytes(payload.try_into().map_err(|_|bad("ARG_LENGTH", start+4))?)),
            Type::Bool => {
                if payload[0] > 1 { return Err(bad("BOOL_VALUE", start+8)); }
                Value::Bool(payload[0] == 1)
            }
            Type::Text => Value::Text(Text::from_bytes(payload).map_err(|_|bad("TEXT_VALUE", start+8))?),
        };
        for (i, b) in bytes[start+8+len..start+SLOT_SIZE].iter().enumerate() {
            if *b != 0 { return Err(bad("PADDING", start+8+len+i)); }
        }
        values[index] = Some(value);
    }
    Ok(Arguments { values, len: count })
}
