mod counter;
#[global_allocator]static ALLOCATOR:counter::Tracked=counter::Tracked;
use std::hint::black_box;
fn snap(s:counter::Snapshot){print!("{{\"live\":{},\"peak\":{},\"alloc\":{},\"realloc\":{},\"dealloc\":{}}}",s.live,s.peak,s.alloc,s.realloc,s.dealloc);}
fn main(){
 assert!(counter::failed_resize_probe());let base=counter::snapshot();counter::reset_peak();let mut marks=[base;4];
 let mut a=Vec::<u8>::with_capacity(64);a.push(1);black_box(a.as_slice());marks[1]=counter::snapshot();counter::reset_peak();
 let mut z=Vec::<u8>::with_capacity(128);z.push(2);black_box(z.as_slice());drop(a);let mut t=Vec::<u8>::with_capacity(16);t.push(3);black_box(t.as_slice());drop(t);marks[2]=counter::snapshot();counter::reset_peak();
 drop(z);marks[3]=counter::snapshot();print!("{{\"marks\":[");for(i,m)in marks.iter().enumerate(){if i>0{print!(",");}snap(*m);}println!("]}}");
}
