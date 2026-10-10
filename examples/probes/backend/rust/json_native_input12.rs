//! Explicit /12 immutable Json input with Boolean payload; never execution authority.
use crate::{transport::{self, Value}, text_value::Text, int_projection::{self,IntProjection}};
#[repr(C)]
#[derive(Clone,Copy)]
pub struct Node {
 pub kind:u64,pub count:u64,pub int_charge:u64,pub int_valid:u64,pub int_payload:i64,
 pub text:*const u8,pub text_bytes:u64,pub text_scalars:u64,
 pub entries:*const Entry,pub bool_payload:u64,
}
#[repr(C)]
#[derive(Clone,Copy)]
pub struct Entry {pub key:*const u8,pub key_bytes:u64,pub child:*const Node}
const _:()=assert!(std::mem::size_of::<Node>()==80 && std::mem::align_of::<Node>()==8 && std::mem::size_of::<Entry>()==24 && std::mem::align_of::<Entry>()==8);
const ZERO:Node=Node{kind:0,count:0,int_charge:0,int_valid:0,int_payload:0,text:std::ptr::null(),text_bytes:0,text_scalars:0,entries:std::ptr::null(),bool_payload:0};
#[derive(Debug,Eq,PartialEq)]
pub struct Error(pub &'static str);
pub struct Owned { nodes:Box<[Node]>, entries:Box<[Entry]>, bytes:Box<[u8]>, roots:Vec<usize> }
impl Owned {
 /// Pointer use requires the separately admitted kernel and this owner alive.
 pub fn root(&self,index:usize)->Option<*const Node>{self.roots.get(index).map(|&n|self.nodes.as_ptr().wrapping_add(n))}
 pub fn counts(&self)->(usize,usize,usize){(self.nodes.len(),self.entries.len(),self.bytes.len())}
}
fn append(pool:&mut Vec<u8>,text:&str)->usize{let at=pool.len();pool.extend_from_slice(text.as_bytes());pool.push(0);at}
pub fn prepare(inputs:&[&[u8]])->Result<Owned,Error>{
 if inputs.len()>8{return Err(Error("JSON_ARGS"));}
 let bytes=inputs.iter().try_fold(0usize,|n,b|n.checked_add(b.len())).ok_or(Error("JSON_BYTES"))?;
 if bytes>transport::FRAME_LIMIT{return Err(Error("JSON_BYTES"));}
 let mut documents=Vec::new();let mut count=0;
 for raw in inputs{
  let doc=transport::parse(raw).map_err(|_|Error("JSON_PARSE"))?;
  count+=doc.values.len();if count>16384{return Err(Error("JSON_VALUES"));}
  let mut pending=vec![(doc.root,1usize)];
  while let Some((id,depth))=pending.pop(){
   if depth>130{return Err(Error("JSON_DEPTH"));}
   match &doc.values[id]{Value::Array(v)=>pending.extend(v.iter().map(|&n|(n,depth+1))),Value::Object(v)=>pending.extend(v.values().map(|&n|(n,depth+1))),_=>{}}
  }
  documents.push(doc);
 }
 encode_admitted(&documents.iter().collect::<Vec<_>>())
}
// Crate-private: only parser-created or sealed invocation compact trees.
// This prepares data and does not admit a native kernel.
pub(crate) fn encode_admitted(documents:&[&transport::Document])->Result<Owned,Error>{
 if documents.len()>8{return Err(Error("JSON_ARGS"));}
 let count=documents.iter().map(|d|d.values.len()).sum::<usize>();
 if count>16384{return Err(Error("JSON_VALUES"));}
 let mut nodes=vec![ZERO;count].into_boxed_slice();let mut entry_specs=Vec::new();let mut node_specs=Vec::new();let mut pool=Vec::new();let mut roots=Vec::new();let mut base=0;
 for doc in documents{
  roots.push(base+doc.root);
  for (i,value) in doc.values.iter().enumerate(){
   let n=&mut nodes[base+i];let mut text_offset=None;let first=entry_specs.len();
   match value{
    Value::Null=>n.kind=1,Value::Bool(v)=>{n.kind=2;n.bool_payload=u64::from(*v);},
    Value::Integer(token)=>{n.kind=3;n.int_charge=token.len() as u64;if let IntProjection::Present(v)=int_projection::project_int(Some(value)){n.int_valid=1;n.int_payload=v;}},
    Value::Number(_)=>n.kind=4,
    Value::String(s)=>{n.kind=5;if s.0.len()<=256{if let Some(s)=s.scalar_string(){if let Ok(t)=Text::from_bytes(s.as_bytes()){n.text_bytes=t.byte_len() as u64;n.text_scalars=t.scalar_len() as u64;text_offset=Some(append(&mut pool,&s));}}}},
    Value::Array(items)=>{n.kind=6;n.count=items.len() as u64;for &id in items{entry_specs.push((None,0,base+id));}},
    Value::Object(items)=>{n.kind=7;n.count=items.len() as u64;for (key,&id) in items{let (offset,len)=if let Some(key)=key.scalar_string(){(Some(append(&mut pool,&key)),key.len() as u64)}else{(None,u64::MAX)};entry_specs.push((offset,len,base+id));}},
   }
   node_specs.push((base+i,text_offset,first,n.count));
  }
  base+=doc.values.len();
 }
 let bytes=pool.into_boxed_slice();let mut entries=Vec::with_capacity(entry_specs.len());
 for (key,len,child) in entry_specs{entries.push(Entry{key:key.map(|i|bytes.as_ptr().wrapping_add(i)).unwrap_or(std::ptr::null()),key_bytes:len,child:nodes.as_ptr().wrapping_add(child)});}
 let entries=entries.into_boxed_slice();
 for (id,text,first,len) in node_specs{let n=&mut nodes[id];n.text=text.map(|i|bytes.as_ptr().wrapping_add(i)).unwrap_or(std::ptr::null());if len>0{n.entries=entries.as_ptr().wrapping_add(first);}}
 Ok(Owned{nodes,entries,bytes,roots})
}

