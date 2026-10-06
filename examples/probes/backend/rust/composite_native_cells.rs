//! Shared caller-owned native cell arena descriptor; no allocation or authority.
use crate::list_native_adapter::NativeValue;
#[repr(C)]
pub struct Cells {pub base:*mut NativeValue,pub capacity:u64,pub used:u64}
const _:()=assert!(std::mem::size_of::<Cells>()==24&&std::mem::align_of::<Cells>()==8);
