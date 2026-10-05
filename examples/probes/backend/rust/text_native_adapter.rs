//! Experimental adapter for separately admitted, signature-matched Text kernels.
//! Transport bytes never select a function pointer or confer execution authority.
use crate::text_callframe::{self, Type, Value};
#[repr(C)]
#[derive(Clone, Copy)]
pub struct NativeValue { scalar: i64, bytes: *const u8, len: u64, scalars: u64 }
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Output { pub status:u32, pub value_type:u32, pub value:i64, pub work:u64, pub reason:u32, pub location:u32 }
impl Output {
    pub const fn zero() -> Self { Self { status:0,value_type:0,value:0,work:0,reason:0,location:0 } }
    pub fn bytes(self) -> [u8;32] {
        let mut b=[0;32];b[0..4].copy_from_slice(&self.status.to_le_bytes());b[4..8].copy_from_slice(&self.value_type.to_le_bytes());b[8..16].copy_from_slice(&self.value.to_le_bytes());b[16..24].copy_from_slice(&self.work.to_le_bytes());b[24..28].copy_from_slice(&self.reason.to_le_bytes());b[28..32].copy_from_slice(&self.location.to_le_bytes());b
    }
}
pub type Kernel = unsafe extern "C" fn(*const NativeValue, *mut Output);
// This probe deliberately targets the frozen x86-64 layout, not arbitrary hosts.
const _: () = assert!(std::mem::size_of::<NativeValue>()==32 && std::mem::align_of::<NativeValue>()==8);
const _: () = assert!(std::mem::size_of::<Output>()==32 && std::mem::align_of::<Output>()==8);
/// Validate an immutable frame, then invoke one separately admitted kernel.
///
/// # Safety
/// `kernel` must implement the exact checked `signature` and the bounded Text
/// kernel contract: synchronous call; read-only inputs; no retained references;
/// no reads outside eight descriptors or their valid Text payloads; only write
/// the supplied Output; complete initialization; no unwinding across the ABI.
/// A pointer from untrusted data must never be supplied as `kernel`.
pub unsafe fn evaluate(input:&[u8], signature:&[Type], kernel:Kernel)->Output {
    let args=match text_callframe::decode(input,signature) {
        Ok(v)=>v,
        Err(e)=>return Output { status:3,reason:8,location:0x80000000+e.offset as u32,..Output::zero() },
    };
    let mut values=[NativeValue { scalar:0,bytes:std::ptr::null(),len:0,scalars:0 };8];
    for (i,slot) in values.iter_mut().enumerate().take(args.len()) {
        *slot=match args.get(i).expect("validated complete argument list") {
            Value::Int64(v)=>NativeValue{scalar:v,..*slot},
            Value::Bool(v)=>NativeValue{scalar:i64::from(v),..*slot},
            Value::Text(v)=>NativeValue{scalar:0,bytes:v.bytes().as_ptr(),len:v.byte_len() as u64,scalars:v.scalar_len() as u64},
        };
    }
    let mut out=Output::zero();
    // SAFETY: input/args/values all live until return. The remaining obligations
    // concerning kernel behavior and signature are required from the caller.
    unsafe { kernel(values.as_ptr(),&mut out); }
    out
}
/// Implement the fixed outer entry for one statically selected checked kernel.
///
/// # Safety
/// In addition to `evaluate`'s obligations, input must reference exactly 8272
/// readable bytes, output must reference 32 writable bytes aligned to 8, and
/// the two regions must be disjoint and remain valid for the complete call.
/// No concurrent input mutation is allowed. Invalid pointers are not admitted
/// refusal cases: this low-level experiment cannot validate arbitrary pointers.
pub unsafe fn entry(input:*const u8,output:*mut Output,signature:&[Type],kernel:Kernel) {
    // SAFETY: caller guarantees the complete valid, immutable input extent.
    let frame=unsafe{std::slice::from_raw_parts(input,text_callframe::FRAME_SIZE)};
    // SAFETY: inherited exact-signature and admitted-kernel obligations.
    let result=unsafe{evaluate(frame,signature,kernel)};
    // SAFETY: caller supplies the complete aligned, disjoint output region.
    unsafe{output.write(result);}
}
