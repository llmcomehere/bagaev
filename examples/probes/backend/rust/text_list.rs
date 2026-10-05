//! Immutable bounded Text-list value precursor, not a source-language/native ABI.
use crate::text_value::Text;
pub const ITEM_LIMIT:usize=64;
pub const BYTE_LIMIT:usize=4096;
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub struct Refusal { pub reason:&'static str, pub index:usize }
pub struct TextList<'items,'text>{items:&'items [Text<'text>],total_bytes:usize}
pub struct SortedUniqueText<'text>{items:[Option<Text<'text>>;ITEM_LIMIT],len:usize}
impl<'items,'text> TextList<'items,'text>{
 pub fn new(items:&'items [Text<'text>])->Result<Self,Refusal>{
  if items.len()>ITEM_LIMIT{return Err(Refusal{reason:"LIST_ITEMS",index:ITEM_LIMIT});}
  let mut total=0;
  for (i,item) in items.iter().enumerate(){total+=item.byte_len();if total>BYTE_LIMIT{return Err(Refusal{reason:"LIST_BYTES",index:i});}}
  Ok(Self{items,total_bytes:total})
 }
 pub fn len(&self)->usize{self.items.len()}
 pub fn is_empty(&self)->bool{self.items.is_empty()}
 pub fn total_bytes(&self)->usize{self.total_bytes}
 pub fn get(&self,index:usize)->Option<Text<'text>>{self.items.get(index).copied()}
 pub fn contains(&self,value:Text<'_>)->bool{self.items.iter().any(|item|item.equal(value))}
 pub fn is_strictly_increasing(&self)->bool{self.items.windows(2).all(|pair|pair[0].compare(pair[1])<0)}
 pub fn unique_sorted(&self)->SortedUniqueText<'text>{
  let mut out=SortedUniqueText{items:[None;ITEM_LIMIT],len:0};
  for item in self.items.iter().copied(){
   let mut at=0;let mut duplicate=false;
   while at<out.len{
    let order=out.items[at].expect("initialized prefix").compare(item);
    if order==0{duplicate=true;break;}
    if order>0{break;}at+=1;
   }
   if duplicate{continue;}
   for index in (at..out.len).rev(){out.items[index+1]=out.items[index];}
   out.items[at]=Some(item);out.len+=1;
  }
  out
 }
}
impl<'text> SortedUniqueText<'text>{
 pub fn len(&self)->usize{self.len}
 pub fn is_empty(&self)->bool{self.len==0}
 pub fn get(&self,index:usize)->Option<Text<'text>>{if index<self.len{self.items[index]}else{None}}
}
