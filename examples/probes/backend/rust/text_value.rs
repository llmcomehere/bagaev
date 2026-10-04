//! Bounded immutable UTF-8 value precursor, not a source-language or native ABI.
use std::cmp::Ordering;

pub const BYTE_LIMIT: usize = 1024;
pub const SCALAR_LIMIT: usize = 256;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TextError { Bytes, Utf8, Scalars }
impl TextError {
    pub fn code(self) -> &'static str {
        match self { Self::Bytes=>"TEXT_BYTES",Self::Utf8=>"TEXT_UTF8",Self::Scalars=>"TEXT_SCALARS" }
    }
}

/// Private fields prevent constructing unchecked values. The lifetime ties the
/// view to its immutable input; no allocation or repair is performed.
#[derive(Clone, Copy, Debug)]
pub struct Text<'a> { value: &'a str, scalars: usize }
impl<'a> Text<'a> {
    pub fn from_bytes(bytes: &'a [u8]) -> Result<Self,TextError> {
        if bytes.len()>BYTE_LIMIT { return Err(TextError::Bytes); }
        let value=std::str::from_utf8(bytes).map_err(|_|TextError::Utf8)?;
        let scalars=value.chars().count();
        if scalars>SCALAR_LIMIT { return Err(TextError::Scalars); }
        Ok(Self{value,scalars})
    }
    pub fn byte_len(self) -> usize { self.value.len() }
    pub fn scalar_len(self) -> usize { self.scalars }
    pub fn bytes(self) -> &'a [u8] { self.value.as_bytes() }
    pub fn equal(self,other:Text<'_>) -> bool { self.value==other.value }
    pub fn compare(self,other:Text<'_>) -> i8 {
        match self.value.as_bytes().cmp(other.value.as_bytes()) {
            Ordering::Less=>-1,Ordering::Equal=>0,Ordering::Greater=>1,
        }
    }
}
