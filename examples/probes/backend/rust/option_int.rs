//! Optional Int64 value precursor. No source-language or native admission implied.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct OptionInt64 { value: Option<i64> }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Refusal { pub reason: &'static str, pub offset: usize }
impl OptionInt64 {
    pub const fn none()->Self{Self{value:None}}
    pub const fn some(value:i64)->Self{Self{value:Some(value)}}
    pub fn is_some(self)->bool{self.value.is_some()}
    pub fn value(self)->Option<i64>{self.value}
    pub fn unwrap_or_else<F:FnOnce()->i64>(self,fallback:F)->i64{match self.value{Some(v)=>v,None=>fallback()}}
    pub fn decode(bytes:&[u8])->Result<Self,Refusal>{
        if bytes.len()!=16{return Err(Refusal{reason:"OPT_SIZE",offset:0});}
        if bytes[0]>1{return Err(Refusal{reason:"OPT_FLAG",offset:0});}
        for (i,b) in bytes[1..8].iter().enumerate(){if *b!=0{return Err(Refusal{reason:"OPT_PADDING",offset:i+1});}}
        let value=i64::from_le_bytes(bytes[8..16].try_into().map_err(|_|Refusal{reason:"OPT_SIZE",offset:0})?);
        if bytes[0]==0{if value!=0{return Err(Refusal{reason:"OPT_PAYLOAD",offset:8});}Ok(Self::none())}else{Ok(Self::some(value))}
    }
    pub fn encode(self)->[u8;16]{let mut bytes=[0;16];if let Some(v)=self.value{bytes[0]=1;bytes[8..16].copy_from_slice(&v.to_le_bytes());}bytes}
}
