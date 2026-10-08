//! Detached output from separately trusted live recursive descriptors.
use crate::{variant_admission_v11::{Checked, Type, ListDefinition}, record_value::Kind, text_value::Text};
pub use crate::list_native_adapter::{NativeValue, NativeText, Output};
#[repr(C)]
pub struct KernelOutput { pub meta: Output, pub value: NativeValue }
const _: () = assert!(std::mem::size_of::<KernelOutput>() == 64 && std::mem::align_of::<KernelOutput>() == 8);
#[derive(Debug, Eq, PartialEq)]
pub struct Error(pub &'static str);
pub struct Owned { pub meta: Output, pub bytes: Vec<u8> }
fn value_error() -> Error { Error("NATIVE_VALUE") }
fn metadata_error() -> Error { Error("NATIVE_META") }
fn zero(v: NativeValue) -> bool { v.scalar == 0 && v.bytes.is_null() && v.len == 0 && v.scalars == 0 }
fn code(t: Type) -> u32 {
    match t { Type::Record(_) => 6, Type::RecordList(_) => 7, Type::Variant(_) => 8, Type::Primitive(k) => match k {
        Kind::Int64 => 1, Kind::Bool => 2, Kind::Text => 3,
        Kind::OptionInt64 => 4, Kind::TextList => 5, Kind::IntProjection => 0,
    }}
}
struct Writer { nodes: Vec<[u8; 32]>, text: Vec<u8> }
fn u32at(b: &mut [u8], p: usize, n: usize) { b[p..p+4].copy_from_slice(&(n as u32).to_le_bytes()); }
impl Writer {
    fn begin(&mut self, tag: usize, nominal: usize, scalar: i64, children: usize) -> Result<usize, Error> {
        if self.nodes.len() >= 4096 { return Err(Error("NATIVE_EXPORT")); }
        let i = self.nodes.len(); let mut n = [0; 32];
        u32at(&mut n,0,tag); u32at(&mut n,4,nominal);
        n[8..16].copy_from_slice(&scalar.to_le_bytes()); u32at(&mut n,20,children);
        self.nodes.push(n); Ok(i)
    }
    fn end(&mut self, at: usize) { let n = self.nodes.len(); u32at(&mut self.nodes[at],16,n); }
    // Caller guarantees readable live extent for nonempty text.
    unsafe fn text(&mut self, v: NativeText) -> Result<usize, Error> {
        if v.len > 1024 || v.scalars > 256 || v.len > 0 && v.bytes.is_null() { return Err(value_error()); }
        let bytes = if v.len == 0 { &[] } else { unsafe { std::slice::from_raw_parts(v.bytes, v.len as usize) } };
        let text = Text::from_bytes(bytes).map_err(|_| value_error())?;
        if text.scalar_len() as u64 != v.scalars { return Err(value_error()); }
        if self.text.len() + bytes.len() > 4_194_304 { return Err(Error("NATIVE_EXPORT")); }
        let at = self.begin(3,0,0,0)?;
        u32at(&mut self.nodes[at],24,self.text.len()); u32at(&mut self.nodes[at],28,bytes.len());
        self.text.extend_from_slice(bytes); self.end(at); Ok(bytes.len())
    }
    // Caller guarantees readable live extents for every recursively reached view.
    unsafe fn node(&mut self, defs: &[&[Type]], lists: &[ListDefinition], variants: &[&[Type]], ty: Type, v: NativeValue) -> Result<(), Error> {
        match ty {
            Type::Variant(id) => {
                let alternatives = variants[usize::from(id)];
                if v.len != 0 || v.scalars != 0 || v.scalar < 0 || v.scalar as u64 >= alternatives.len() as u64 { return Err(value_error()); }
                if v.bytes.is_null() || (v.bytes as usize) % 8 != 0 { return Err(value_error()); }
                let payload = unsafe { v.bytes.cast::<NativeValue>().read() };
                let at = self.begin(8,defs.len()+lists.len()+usize::from(id),v.scalar,1)?;
                unsafe { self.node(defs,lists,variants,alternatives[v.scalar as usize],payload) }?;
                self.end(at);
            }
            Type::RecordList(id) => {
                let list = lists[usize::from(id)];
                if v.scalar != 0 || v.scalars != 0 || v.len > u64::from(list.capacity) { return Err(value_error()); }
                if v.len > 0 && (v.bytes.is_null() || (v.bytes as usize) % 8 != 0) { return Err(value_error()); }
                let cells = if v.len == 0 { &[] } else { unsafe { std::slice::from_raw_parts(v.bytes.cast::<NativeValue>(), v.len as usize) } };
                let at = self.begin(7,defs.len()+usize::from(id),0,cells.len())?;
                for &cell in cells { unsafe { self.node(defs,lists,variants,Type::Record(list.element),cell) }?; }
                self.end(at);
            }
            Type::Record(id) => {
                if v.scalar != 0 || v.len != 0 || v.scalars != 0 { return Err(value_error()); }
                let fields = defs[usize::from(id)];
                if fields.is_empty() {
                    if !v.bytes.is_null() { return Err(value_error()); }
                    let at = self.begin(6,usize::from(id),0,0)?; self.end(at); return Ok(());
                }
                if v.bytes.is_null() || (v.bytes as usize) % 8 != 0 { return Err(value_error()); }
                let cells = unsafe { std::slice::from_raw_parts(v.bytes.cast::<NativeValue>(), fields.len()) };
                let at = self.begin(6,usize::from(id),0,fields.len())?;
                for (&field,&cell) in fields.iter().zip(cells) { unsafe { self.node(defs,lists,variants,field,cell) }?; }
                self.end(at);
            }
            Type::Primitive(Kind::Int64 | Kind::Bool) => {
                if !v.bytes.is_null() || v.len != 0 || v.scalars != 0 { return Err(value_error()); }
                let is_bool = ty == Type::Primitive(Kind::Bool);
                if is_bool && !matches!(v.scalar,0|1) { return Err(value_error()); }
                let at = self.begin(if is_bool {2} else {1},0,v.scalar,0)?; self.end(at);
            }
            Type::Primitive(Kind::OptionInt64) => {
                if !v.bytes.is_null() || v.scalars != 0 || v.len > 1 || v.len == 0 && v.scalar != 0 { return Err(value_error()); }
                let at = self.begin(if v.len == 0 {4} else {9},0,v.scalar,0)?; self.end(at);
            }
            Type::Primitive(Kind::Text) => {
                if v.scalar != 0 { return Err(value_error()); }
                unsafe { self.text(NativeText {bytes:v.bytes,len:v.len,scalars:v.scalars}) }?;
            }
            Type::Primitive(Kind::TextList) => {
                if v.scalar != 0 || v.len > 64 || v.scalars > 4096 { return Err(value_error()); }
                // Empty list views carry no readable extent; their pointer is opaque.
                if v.len > 0 && (v.bytes.is_null() || (v.bytes as usize)%8 != 0) { return Err(value_error()); }
                let items = if v.len == 0 { &[] } else { unsafe { std::slice::from_raw_parts(v.bytes.cast::<NativeText>(),v.len as usize) } };
                let at = self.begin(5,0,0,items.len())?;
                let mut total = 0; for &item in items { total += unsafe { self.text(item) }?; }
                if total as u64 != v.scalars { return Err(value_error()); }
                self.end(at);
            }
            Type::Primitive(Kind::IntProjection) => return Err(value_error()),
        }
        Ok(())
    }
}
/// # Safety
/// All nonempty output views must point to aligned, initialized, readable live
/// regions of their declared extent throughout this call, including nested views.
/// The caller binds exact admitted source/result and artifact; pointers cannot be
/// validated by these bounds checks. No concurrent mutation or retained reference.
pub unsafe fn export(checked: &Checked<'_, '_, '_, '_>, out: &KernelOutput, binding: &[u8;32]) -> Result<Owned,Error> {
    let m = out.meta; if m.work > 65536 { return Err(metadata_error()); }
    if m.status != 0 {
        if m.value_type != 0 || m.value != 0 || !zero(out.value) || !(1..=2048).contains(&m.location) || !matches!((m.status,m.reason),(1,9)|(2,10)|(4,11)|(5,12)|(7,14)|(8,15)) { return Err(metadata_error()); }
        return Ok(Owned {meta:m,bytes:m.bytes().to_vec()});
    }
    let result = checked.result();
    if m.reason != 0 || m.location != 0 || m.value_type != code(result) { return Err(metadata_error()); }
    let mut v = out.value;
    match result {
        Type::Record(id) | Type::RecordList(id) | Type::Variant(id) => if m.value != i64::from(id) { return Err(metadata_error()); },
        Type::Primitive(Kind::Int64 | Kind::Bool) => {
            if !zero(v) { return Err(metadata_error()); } v.scalar = m.value;
        }
        Type::Primitive(_) => if m.value != 0 { return Err(metadata_error()); },
    }
    let mut writer = Writer {nodes:Vec::new(),text:Vec::new()};
    unsafe { writer.node(checked.definitions(),checked.lists(),checked.variants(),result,v) }?;
    let size = 64 + writer.nodes.len()*32 + writer.text.len();
    if size > 4_325_440 { return Err(Error("NATIVE_EXPORT")); }
    let mut bytes = vec![0;64]; bytes[..8].copy_from_slice(b"BCMPRES4");
    u32at(&mut bytes,8,writer.nodes.len()); u32at(&mut bytes,12,writer.text.len());
    bytes[16..24].copy_from_slice(&m.work.to_le_bytes()); bytes[24..56].copy_from_slice(binding);
    for n in writer.nodes {bytes.extend_from_slice(&n);} bytes.extend_from_slice(&writer.text);
    Ok(Owned {meta:m,bytes})
}
