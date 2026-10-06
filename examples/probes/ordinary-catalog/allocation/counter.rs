use std::alloc::{GlobalAlloc,Layout,System};
use std::sync::atomic::{AtomicU64,Ordering};
static LIVE:AtomicU64=AtomicU64::new(0);static PEAK:AtomicU64=AtomicU64::new(0);
static ALLOC:AtomicU64=AtomicU64::new(0);static REALLOC:AtomicU64=AtomicU64::new(0);static DEALLOC:AtomicU64=AtomicU64::new(0);
fn add(a:&AtomicU64,n:u64)->u64{match a.fetch_update(Ordering::SeqCst,Ordering::SeqCst,|v|v.checked_add(n)){Ok(v)=>v+n,Err(_)=>std::process::abort()}}
fn sub(a:&AtomicU64,n:u64){if a.fetch_update(Ordering::SeqCst,Ordering::SeqCst,|v|v.checked_sub(n)).is_err(){std::process::abort()}}
fn peak(){PEAK.fetch_max(LIVE.load(Ordering::SeqCst),Ordering::SeqCst);}
fn resized(old:usize,new:usize,success:bool){if success{sub(&LIVE,old as u64);add(&LIVE,new as u64);peak();add(&REALLOC,1);}}
pub struct Tracked;
unsafe impl GlobalAlloc for Tracked{
 unsafe fn alloc(&self,l:Layout)->*mut u8{let p=unsafe{System.alloc(l)};if !p.is_null(){add(&LIVE,l.size() as u64);peak();add(&ALLOC,1);}p}
 unsafe fn alloc_zeroed(&self,l:Layout)->*mut u8{let p=unsafe{System.alloc_zeroed(l)};if !p.is_null(){add(&LIVE,l.size() as u64);peak();add(&ALLOC,1);}p}
 unsafe fn dealloc(&self,p:*mut u8,l:Layout){unsafe{System.dealloc(p,l)};sub(&LIVE,l.size() as u64);add(&DEALLOC,1);}
 unsafe fn realloc(&self,p:*mut u8,l:Layout,n:usize)->*mut u8{let q=unsafe{System.realloc(p,l,n)};resized(l.size(),n,!q.is_null());q}
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub struct Snapshot{pub live:u64,pub peak:u64,pub alloc:u64,pub realloc:u64,pub dealloc:u64}
pub fn snapshot()->Snapshot{Snapshot{live:LIVE.load(Ordering::SeqCst),peak:PEAK.load(Ordering::SeqCst),alloc:ALLOC.load(Ordering::SeqCst),realloc:REALLOC.load(Ordering::SeqCst),dealloc:DEALLOC.load(Ordering::SeqCst)}}
pub fn reset_peak(){PEAK.store(LIVE.load(Ordering::SeqCst),Ordering::SeqCst)}
pub fn failed_resize_probe()->bool{let before=snapshot();resized(32,80,false);snapshot()==before}
