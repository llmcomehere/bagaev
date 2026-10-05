//! Portable bounded input data for a Text-list native probe boundary.
//! No function pointers, compiler invocation or execution admission.
use crate::text_value::Text;
pub const FRAME_SIZE: usize = 37008;
const SLOT_SIZE: usize = 4624;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Type { Int64, Bool, Text, OptionInt64, TextList }
#[derive(Clone, Copy)]
pub enum Value<'a> { Int64(i64), Bool(bool), Text(Text<'a>), Optional(crate::option_int::OptionInt64), List(ListValue<'a>) }
#[derive(Clone, Copy)]
pub struct ListValue<'a> { items: [Option<Text<'a>>; 64], len: usize }
impl<'a> ListValue<'a> {
    pub fn len(&self) -> usize { self.len }
    pub fn is_empty(&self) -> bool { self.len == 0 }
    pub fn get(&self, index: usize) -> Option<Text<'a>> {
        if index < self.len { self.items[index] } else { None }
    }
}
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
    for (i, expected) in b"BTXTIN3\0".iter().enumerate() {
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
        let expected = match signature[index] { Type::Int64=>1, Type::Bool=>2, Type::Text=>3, Type::OptionInt64=>4, Type::TextList=>5 };
        if tag != expected { return Err(bad("ARG_TAG", start)); }
        let len = word(bytes, start+4) as usize;
        if match signature[index] { Type::Int64=>len!=8, Type::Bool=>len!=1, Type::Text=>len>1024, Type::OptionInt64=>len!=16, Type::TextList=>len!=4616 } {
            return Err(bad("ARG_LENGTH", start+4));
        }
        let payload = &bytes[start+8..start+8+len];
        let value = match signature[index] {
            Type::TextList=>Value::List(decode_list(payload,start+8)?),
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

fn decode_list<'a>(payload: &'a [u8], base: usize) -> Result<ListValue<'a>, Refusal> {
    let count = word(payload, 0) as usize;
    if count > 64 { return Err(bad("LIST_COUNT", base)); }
    for (i, b) in payload[4..8].iter().enumerate() {
        if *b != 0 { return Err(bad("LIST_RESERVED", base+4+i)); }
    }
    let mut items = [None; 64];
    let mut used = 0;
    for (i, item) in items.iter_mut().enumerate().take(count) {
        let descriptor = 8+i*8;
        let offset = word(payload, descriptor) as usize;
        if offset != used { return Err(bad("LIST_OFFSET", base+descriptor)); }
        let len = word(payload, descriptor+4) as usize;
        if len > 1024 { return Err(bad("LIST_LENGTH", base+descriptor+4)); }
        // used <=4096 and len<=1024: sum cannot overflow on supported targets.
        if used+len > 4096 { return Err(bad("LIST_BYTES", base+descriptor+4)); }
        *item = Some(Text::from_bytes(&payload[520+used..520+used+len])
            .map_err(|_|bad("LIST_TEXT", base+520+used))?);
        used += len;
    }
    for (i, b) in payload[8+count*8..520].iter().enumerate() {
        if *b != 0 { return Err(bad("LIST_UNUSED", base+8+count*8+i)); }
    }
    for (i, b) in payload[520+used..].iter().enumerate() {
        if *b != 0 { return Err(bad("LIST_PADDING", base+520+used+i)); }
    }
    Ok(ListValue { items, len: count })
}
