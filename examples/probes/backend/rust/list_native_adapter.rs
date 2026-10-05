//! Experimental adapter for separately admitted, signature-matched list kernels.
//! Transport bytes never select a function pointer or confer execution authority.
use crate::list_callframe::{self, Type, Value};
#[repr(C)]
#[derive(Clone, Copy)]
pub struct NativeValue { pub scalar: i64, pub bytes: *const u8, pub len: u64, pub scalars: u64 }
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Output { pub status:u32, pub value_type:u32, pub value:i64, pub work:u64, pub reason:u32, pub location:u32 }
impl Output {
    pub const fn zero() -> Self { Self { status:0,value_type:0,value:0,work:0,reason:0,location:0 } }
    pub fn bytes(self) -> [u8;32] {
        let mut b=[0;32];b[0..4].copy_from_slice(&self.status.to_le_bytes());b[4..8].copy_from_slice(&self.value_type.to_le_bytes());b[8..16].copy_from_slice(&self.value.to_le_bytes());b[16..24].copy_from_slice(&self.work.to_le_bytes());b[24..28].copy_from_slice(&self.reason.to_le_bytes());b[28..32].copy_from_slice(&self.location.to_le_bytes());b
    }
}
#[repr(C)]
#[derive(Clone, Copy)]
pub struct NativeText { pub bytes: *const u8, pub len: u64, pub scalars: u64 }
impl NativeText { pub const fn zero()->Self {Self{bytes:std::ptr::null(),len:0,scalars:0}} }
#[repr(C)]
pub struct Arena { pub base:*mut NativeText, pub capacity:u64, pub used:u64 }
pub const SCRATCH_CAPACITY:usize=65536;
pub type Kernel = unsafe extern "C" fn(*const NativeValue, *mut Arena, *mut Output);
const _: () = assert!(std::mem::size_of::<NativeText>()==24 && std::mem::align_of::<NativeText>()==8);
const _: () = assert!(std::mem::size_of::<Arena>()==24 && std::mem::align_of::<Arena>()==8);
// This probe deliberately targets the frozen x86-64 layout, not arbitrary hosts.
const _: () = assert!(std::mem::size_of::<NativeValue>()==32 && std::mem::align_of::<NativeValue>()==8);
const _: () = assert!(std::mem::size_of::<Output>()==32 && std::mem::align_of::<Output>()==8);
/// Validate an immutable frame, then invoke one separately admitted kernel.
///
/// # Safety
/// `kernel` must implement the exact checked `signature` and the bounded Text-list
/// kernel contract: synchronous call; read-only inputs and input descriptors; no retained references;
/// no reads outside eight values, their count-bounded list descriptors, valid Text
/// payloads or initialized scratch slots; only write
/// the supplied Output and admitted scratch/header; complete output initialization;
/// bounded arena writes, valid borrowed Text lifetimes, no unwinding across the ABI.
/// Scratch must not alias input, input descriptors or output; safe slice borrowing
/// supplies its alignment/lifetime, but cannot prove arbitrary kernel behavior.
/// A pointer from untrusted data must never be supplied as `kernel`.
pub unsafe fn evaluate(input:&[u8], signature:&[Type], scratch:&mut [NativeText], kernel:Kernel)->Output {
    let args=match list_callframe::decode(input,signature) {
        Ok(v)=>v,
        Err(e)=>return Output { status:3,reason:8,location:0x80000000+e.offset as u32,..Output::zero() },
    };
    if scratch.len()!=SCRATCH_CAPACITY {return Output{status:3,reason:8,location:0x90000000,..Output::zero()};}
    let mut input_lists=[[NativeText::zero();64];8];
    let mut arena=Arena{base:scratch.as_mut_ptr(),capacity:SCRATCH_CAPACITY as u64,used:0};
    let mut values=[NativeValue { scalar:0,bytes:std::ptr::null(),len:0,scalars:0 };8];
    for (i,slot) in values.iter_mut().enumerate().take(args.len()) {
        *slot=match args.get(i).expect("validated complete argument list") {
            Value::List(v)=>{
                let mut total=0u64;
                for j in 0..v.len(){let text=v.get(j).expect("validated list prefix");input_lists[i][j]=NativeText{bytes:text.bytes().as_ptr(),len:text.byte_len() as u64,scalars:text.scalar_len() as u64};total+=text.byte_len() as u64;}
                NativeValue{scalar:0,bytes:input_lists[i].as_ptr().cast(),len:v.len() as u64,scalars:total}
            },
            Value::Optional(v)=>NativeValue{scalar:v.value().unwrap_or(0),bytes:std::ptr::null(),len:u64::from(v.is_some()),scalars:0},
            Value::Int64(v)=>NativeValue{scalar:v,..*slot},
            Value::Bool(v)=>NativeValue{scalar:i64::from(v),..*slot},
            Value::Text(v)=>NativeValue{scalar:0,bytes:v.bytes().as_ptr(),len:v.byte_len() as u64,scalars:v.scalar_len() as u64},
        };
    }
    let mut out=Output::zero();
    // SAFETY: input/args/values all live until return. The remaining obligations
    // concerning kernel behavior and signature are required from the caller.
    unsafe { kernel(values.as_ptr(),&mut arena,&mut out); }
    out
}
