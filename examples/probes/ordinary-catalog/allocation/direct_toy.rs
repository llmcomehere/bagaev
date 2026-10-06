mod counter;
use std::alloc::{GlobalAlloc,Layout};
fn main(){
 let a=counter::Tracked;let l32=Layout::from_size_align(32,8).unwrap();let l16=Layout::from_size_align(16,8).unwrap();let l80=Layout::from_size_align(80,8).unwrap();let l8=Layout::from_size_align(8,8).unwrap();
 counter::reset_peak();let failed=counter::failed_resize_probe();let mut live=[0u64;5];
 unsafe{
  let mut p=a.alloc(l32);assert!(!p.is_null());std::ptr::write_bytes(p,0x5a,32);live[0]=counter::snapshot().live;
  let z=a.alloc_zeroed(l16);assert!(!z.is_null());assert!(std::slice::from_raw_parts(z,16).iter().all(|x|*x==0));live[1]=counter::snapshot().live;
  p=a.realloc(p,l32,80);assert!(!p.is_null());assert!(std::slice::from_raw_parts(p,32).iter().all(|x|*x==0x5a));live[2]=counter::snapshot().live;
  p=a.realloc(p,l80,8);assert!(!p.is_null());assert!(std::slice::from_raw_parts(p,8).iter().all(|x|*x==0x5a));live[3]=counter::snapshot().live;
  a.dealloc(p,l8);a.dealloc(z,l16);live[4]=counter::snapshot().live;
 }
 let s=counter::snapshot();println!("{{\"live\":{:?},\"peak\":{},\"alloc\":{},\"realloc\":{},\"dealloc\":{},\"failed_accounting_unchanged\":{}}}",live,s.peak,s.alloc,s.realloc,s.dealloc,failed);
}
