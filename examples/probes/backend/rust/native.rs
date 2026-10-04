//! Safe preparation and decoding for one statically linked checked kernel.
//! No evaluator, loader, LLVM emitter, foreign call or execution authority here.
use crate::check::{self, FrontendError, Refusal};
use crate::ir::{CheckedInvocation, CheckedProgram, Scalar, Type};
use crate::{canonical, sha256};
use std::fmt::{self, Write};

pub const BINDING_LIMIT: usize = 2 * 1024 * 1024;
pub const WITNESS_LIMIT: usize = 8 * 1024 * 1024;
pub const TARGET: &str = "x86_64-unknown-linux-gnu";
pub const CPU: &str = "x86-64";
pub const SIGNATURE: &str = "void bagaev_probe_entry(const int64_t arguments[8], void *output)";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error { Bound, Interface, Binding, InputMutation, Encoding }
impl From<fmt::Error> for Error { fn from(_: fmt::Error) -> Self { Self::Bound } }
type Result<T> = std::result::Result<T, Error>;

struct Text { value: String, limit: usize }
impl Text {
    fn new(limit: usize) -> Self { Self { value: String::new(), limit } }
    fn quote(&mut self, value: &str) -> Result<()> {
        let mut encoded=String::new(); canonical::quote(value,&mut encoded);
        self.write_str(&encoded)?; Ok(())
    }
    fn hex(&mut self, value: &[u8]) -> Result<()> {
        self.write_char('"')?;
        for byte in value { write!(self,"{byte:02x}")?; }
        self.write_char('"')?; Ok(())
    }
}
impl Write for Text {
    fn write_str(&mut self, value: &str) -> fmt::Result {
        if value.len()>self.limit.saturating_sub(self.value.len()) { return Err(fmt::Error); }
        self.value.push_str(value); Ok(())
    }
}

/// Independently reconstruct the producer's canonical embedded DATA descriptor.
/// Equality is over every byte, not merely H(program). No 1MiB JSON reparse:
/// the producer permits up to 2MiB and the same checked API drives both maps.
pub fn expected_binding(program: &CheckedProgram) -> Result<Vec<u8>> {
    let mut out=Text::new(BINDING_LIMIT);
    out.write_str("{\"abi\":{\"alignment\":8,\"argument_bytes\":64,\"argument_location_base\":2147483649,\"byte_order\":\"little-endian\",\"calling_convention\":\"system-C\",\"fields\":[")?;
    for (i,(name,offset,width,ty)) in [
        ("status",0,4,"uint32"),("value_type",4,4,"uint32"),("value",8,8,"int64"),
        ("work",16,8,"uint64"),("reason",24,4,"uint32"),("location",28,4,"uint32"),
    ].iter().enumerate() {
        if i>0 { out.write_char(',')?; }
        out.write_str("{\"name\":")?; out.quote(name)?;
        write!(out,",\"offset\":{offset},\"type\":")?; out.quote(ty)?;
        write!(out,",\"width\":{width}}}")?;
    }
    out.write_str("],\"output_bytes\":32,\"reason_codes\":{\"IR_ARGUMENT\":8,\"IR_BOUNDS\":4,\"IR_CYCLE\":6,\"IR_JSON\":1,\"IR_OVERFLOW\":9,\"IR_REFERENCE\":5,\"IR_SHAPE\":3,\"IR_TYPE\":7,\"IR_VERSION\":2,\"IR_WORK\":10,\"success\":0},\"regions_disjoint\":true,\"signature\":")?;
    out.quote(SIGNATURE)?;
    out.write_str(",\"status_codes\":{\"integer-overflow\":1,\"invalid-ir\":3,\"success\":0,\"work-limit\":2},\"symbol\":\"bagaev_probe_entry\",\"type_codes\":{\"Bool\":2,\"Int64\":1,\"absent\":0}},\"cpu\":")?;
    out.quote(CPU)?; write!(out,",\"entry\":{},\"functions\":[",program.entry())?;
    for (i,function) in program.functions().iter().enumerate() {
        if i>0 { out.write_char(',')?; }
        write!(out,"{{\"body\":{},\"callees\":[",function.body())?;
        for (j,callee) in function.callees().iter().enumerate() {
            if j>0 { out.write_char(',')?; } write!(out,"{callee}")?;
        }
        write!(out,"],\"index\":{i},\"locals\":[")?;
        for (j,local) in function.locals().iter().enumerate() {
            if j>0 { out.write_char(',')?; }
            out.write_str("{\"name\":")?; out.quote(local.name())?;
            write!(out,",\"slot\":{j},\"type\":")?; out.quote(local.ty().name())?; out.write_char('}')?;
        }
        out.write_str("],\"name\":")?; out.quote(function.name())?; out.write_str(",\"parameters\":[")?;
        for (j,parameter) in function.parameters().iter().enumerate() {
            if j>0 { out.write_char(',')?; }
            out.write_str("{\"name\":")?; out.quote(parameter.name())?;
            write!(out,",\"slot\":{j},\"type\":")?; out.quote(parameter.ty().name())?; out.write_char('}')?;
        }
        out.write_str("],\"result\":")?; out.quote(function.result().name())?; out.write_char('}')?;
    }
    out.write_str("],\"llvm\":\"21.1\",\"nodes\":[")?;
    for (i,node) in program.nodes().iter().enumerate() {
        if i>0 { out.write_char(',')?; }
        out.write_str("{\"children\":[")?;
        for (j,child) in node.kind().children().iter().enumerate() {
            if j>0 { out.write_char(',')?; } write!(out,"{child}")?;
        }
        write!(out,"],\"function\":{},\"id\":{},\"op\":",node.function(),node.id())?;
        out.quote(node.kind().name())?; out.write_str(",\"pointer\":")?; out.quote(node.pointer())?;
        out.write_str(",\"type\":")?; out.quote(node.ty().name())?; out.write_char('}')?;
    }
    out.write_str("],\"program\":")?;
    out.write_str(std::str::from_utf8(program.canonical_bytes()).map_err(|_|Error::Interface)?)?;
    out.write_str(",\"program_pin\":")?; out.quote(program.identity())?;
    out.write_str(",\"schema\":\"bagaev-probe-llvm-binding/1\",\"semantic\":\"bagaev-probe-ir/1\",\"target\":")?;
    out.quote(TARGET)?; out.write_str(",\"work_limit\":65536}")?;
    Ok(out.value.into_bytes())
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Prefill { Zero, Ones }
impl Prefill {
    pub fn name(self) -> &'static str { match self { Self::Zero=>"00",Self::Ones=>"ff" } }
    pub fn byte(self) -> u8 { match self { Self::Zero=>0,Self::Ones=>255 } }
}

/// Only complete frontend checking can construct the checked variant.
pub enum Checked { Invocation(CheckedInvocation), Refusal(Observation) }
pub fn check_frame(bytes: &[u8], prefill: Prefill) -> Result<Checked> {
    match check::check_invocation_bytes(bytes) {
        Ok(invocation)=>Ok(Checked::Invocation(invocation)),
        Err(FrontendError::Refusal(error))=>Ok(Checked::Refusal(static_refusal(&error,prefill)?)),
        Err(FrontendError::Environment(_))=>Err(Error::Interface),
    }
}

/// No unchecked constructor and no binding deserializer. Checked data is owned
/// and immutable until the one call and complete decoding have finished.
pub struct BoundInvocation { invocation: CheckedInvocation, binding_pin: String }
impl BoundInvocation {
    pub fn program(&self) -> &CheckedProgram { self.invocation.program() }
    pub fn binding_pin(&self) -> &str { &self.binding_pin }
    pub fn regions(&self, prefill: Prefill) -> (Arguments, Output) {
        let mut bytes=[0u8;64];
        for (i,value) in self.invocation.arguments().iter().enumerate() {
            let slot=match value { Scalar::Int64(n)=>*n,Scalar::Bool(b)=>i64::from(*b) };
            bytes[i*8..i*8+8].copy_from_slice(&slot.to_le_bytes());
        }
        (Arguments { bytes },Output { bytes:[prefill.byte();32] })
    }
}

pub fn bind(invocation: CheckedInvocation, linked: &[u8]) -> Result<BoundInvocation> {
    if linked.is_empty() || linked.len()>BINDING_LIMIT { return Err(Error::Binding); }
    let expected=expected_binding(invocation.program())?;
    if linked!=expected.as_slice() { return Err(Error::Binding); }
    Ok(BoundInvocation { invocation,binding_pin:sha256::digest(linked) })
}

/// Single contiguous byte arrays with explicit8 alignment; never cast to a Rust
/// struct or dereference an i64 pointer. Raw pointers derive from MUTABLE borrows
/// so an incorrect native write is detectable without a live shared input borrow.
#[repr(C, align(8))]
pub struct Arguments { bytes: [u8;64] }
#[repr(C, align(8))]
pub struct Output { bytes: [u8;32] }
impl Arguments {
    pub fn bytes(&self) -> &[u8;64] { &self.bytes }
    pub fn as_mut_ptr(&mut self) -> *mut u8 { self.bytes.as_mut_ptr() }
}
impl Output {
    pub fn bytes(&self) -> &[u8;32] { &self.bytes }
    pub fn as_mut_ptr(&mut self) -> *mut u8 { self.bytes.as_mut_ptr() }
}

#[derive(Clone, Debug)]
pub struct Capture { pub before:[u8;64],pub after:[u8;64],pub output:[u8;32] }

/// These bytes are an observation, never proof of conformance or admission.
pub struct Observation { result: Vec<u8>, witness: Vec<u8> }
impl Observation {
    pub fn result_bytes(&self) -> &[u8] { &self.result }
    pub fn witness_bytes(&self) -> &[u8] { &self.witness }
}

fn witness(result: Vec<u8>, bound: Option<&BoundInvocation>, capture: Option<&Capture>, prefill: Prefill) -> Result<Observation> {
    let mut out=Text::new(WITNESS_LIMIT);
    out.write_str("{\"binding_pin\":")?;
    match bound { Some(b)=>out.quote(b.binding_pin())?,None=>out.write_str("null")? }
    write!(out,",\"entry_call_count\":{},\"input_after_hex\":",if capture.is_some() {1} else {0})?;
    match capture { Some(c)=>out.hex(&c.after)?,None=>out.write_str("null")? }
    out.write_str(",\"input_before_hex\":")?;
    match capture { Some(c)=>out.hex(&c.before)?,None=>out.write_str("null")? }
    out.write_str(",\"output_hex\":")?;
    match capture { Some(c)=>out.hex(&c.output)?,None=>out.write_str("null")? }
    out.write_str(",\"prefill\":")?; out.quote(prefill.name())?;
    out.write_str(",\"program_pin\":")?;
    match bound { Some(b)=>out.quote(b.program().identity())?,None=>out.write_str("null")? }
    write!(out,",\"result_wire_bytes\":{},\"result_wire_hex\":",result.len())?;
    out.hex(&result)?;
    out.write_str(",\"schema\":\"bagaev-probe-native-witness/1\"}\n")?;
    Ok(Observation { result,witness:out.value.into_bytes() })
}

pub fn static_refusal(error: &Refusal, prefill: Prefill) -> Result<Observation> {
    witness(canonical::refusal_bytes(error),None,None,prefill)
}

fn u32_at(bytes: &[u8;32], offset: usize) -> u32 {
    u32::from_le_bytes(bytes[offset..offset+4].try_into().expect("fixed ABI offset"))
}
fn u64_at(bytes: &[u8;32], offset: usize) -> u64 {
    u64::from_le_bytes(bytes[offset..offset+8].try_into().expect("fixed ABI offset"))
}

/// Validate wire encoding only. Do not infer work, result, reached nodes or
/// operation semantics by interpreting the checked AST. Wrong WELL-FORMED native
/// observations must reach independent conformance unchanged.
pub fn decode(bound: &BoundInvocation, capture: Capture, prefill: Prefill) -> Result<Observation> {
    let (expected,_)=bound.regions(prefill);
    if capture.before!=*expected.bytes() || capture.after!=capture.before { return Err(Error::InputMutation); }
    let bytes=&capture.output;
    let status=u32_at(bytes,0); let ty=u32_at(bytes,4);
    let value=i64::from_le_bytes(bytes[8..16].try_into().expect("fixed ABI offset"));
    let work=u64_at(bytes,16); let reason=u32_at(bytes,24); let location=u32_at(bytes,28);
    if work>65536 { return Err(Error::Encoding); }
    let mut out=Text::new(WITNESS_LIMIT);
    out.write_str("{\"location\":")?;
    let (status_name,reason_name)=match status {
        0=>{
            let declared=bound.program().functions()[bound.program().entry()].result();
            let expected_type=match declared { Type::Int64=>1,Type::Bool=>2 };
            if reason!=0 || location!=0 || ty!=expected_type || (ty==2 && value!=0 && value!=1) { return Err(Error::Encoding); }
            out.write_str("null")?; ("success",None)
        }
        1|2=>{
            if ty!=0 || value!=0 || reason!=(if status==1 {9} else {10})
                || (status==2 && work!=65536) { return Err(Error::Encoding); }
            let id=u16::try_from(location).map_err(|_|Error::Encoding)?;
            let node=bound.program().node(id).ok_or(Error::Encoding)?;
            out.quote(&format!("/program{}",node.pointer()))?;
            if status==1 { ("integer-overflow",Some("IR_OVERFLOW")) } else { ("work-limit",Some("IR_WORK")) }
        }
        3=>{
            if ty!=0 || value!=0 || work!=0 || reason!=8 || !(0x80000001..=0x80000008).contains(&location) { return Err(Error::Encoding); }
            out.quote(&format!("/arguments/{}",location-0x80000001))?;
            ("invalid-ir",Some("IR_ARGUMENT"))
        }
        _=>return Err(Error::Encoding),
    };
    out.write_str(",\"reason\":")?;
    match reason_name { Some(reason)=>out.quote(reason)?,None=>out.write_str("null")? }
    out.write_str(",\"schema\":\"bagaev-probe-result/1\",\"status\":")?; out.quote(status_name)?;
    out.write_str(",\"value\":")?;
    if status!=0 { out.write_str("null")?; }
    else if ty==2 { out.write_str(if value==0 {"false"} else {"true"})?; }
    else { write!(out,"{value}")?; }
    out.write_str(",\"value_type\":")?;
    if status!=0 { out.write_str("null")?; }
    else { out.quote(if ty==2 {"Bool"} else {"Int64"})?; }
    write!(out,",\"work\":{work}}}\n")?;
    witness(out.value.into_bytes(),Some(bound),Some(&capture),prefill)
}
