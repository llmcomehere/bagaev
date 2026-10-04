//! Deterministic textual LLVM 21 AOT lowering of the complete checked kernel.
//! This library constructs bytes only. It neither executes nor admits an artifact.
use crate::ir::{BinaryOp, CheckedProgram, NodeId, NodeKind, Type};
use crate::{canonical, sha256};
use std::fmt::{self, Write};

pub const MODULE_LIMIT: usize = 8 * 1024 * 1024;
pub const BINDING_LIMIT: usize = 2 * 1024 * 1024;
pub const TARGET: &str = "x86_64-unknown-linux-gnu";
pub const CPU: &str = "x86-64";
pub const SIGNATURE: &str = "void bagaev_probe_entry(const int64_t arguments[8], void *output)";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EmitError { Bound, Interface }
impl From<fmt::Error> for EmitError { fn from(_: fmt::Error) -> Self { Self::Bound } }
type Result<T> = std::result::Result<T, EmitError>;

/// No unchecked constructor, serialized loader, mutation or execution interface.
#[derive(Debug)]
pub struct Module { bytes: Vec<u8>, binding: Vec<u8>, identity: String }
impl Module {
    pub fn bytes(&self) -> &[u8] { &self.bytes }
    /// Complete canonical module descriptor plus artifact pin, terminated by LF.
    pub fn binding_bytes(&self) -> &[u8] { &self.binding }
    pub fn identity(&self) -> &str { &self.identity }
}

struct Text { value: String, limit: usize }
impl Text {
    fn new(limit: usize) -> Self { Self { value: String::new(), limit } }
    fn quote(&mut self, value: &str) -> Result<()> {
        // Strings here are bounded checked IDs/pointers or fixed schema constants.
        let mut encoded = String::new(); canonical::quote(value, &mut encoded);
        self.write_str(&encoded)?; Ok(())
    }
}
impl Write for Text {
    fn write_str(&mut self, value: &str) -> fmt::Result {
        if value.len() > self.limit.saturating_sub(self.value.len()) { return Err(fmt::Error); }
        self.value.push_str(value); Ok(())
    }
}

fn type_code(ty: Type) -> u32 { match ty { Type::Int64 => 1, Type::Bool => 2 } }

/// Includes the whole semantic program, all signatures/locals/edges and all nodes.
/// Embedded in the module as data only; native evaluation never reads this data.
fn descriptor(program: &CheckedProgram, limit: usize) -> Result<String> {
    let mut out = Text::new(limit);
    out.write_str("{\"abi\":{\"alignment\":8,\"argument_bytes\":64,\"argument_location_base\":2147483649,\"byte_order\":\"little-endian\",\"calling_convention\":\"system-C\",\"fields\":[")?;
    for (i, (name, offset, width, ty)) in [
        ("status",0,4,"uint32"),("value_type",4,4,"uint32"),("value",8,8,"int64"),
        ("work",16,8,"uint64"),("reason",24,4,"uint32"),("location",28,4,"uint32"),
    ].iter().enumerate() {
        if i>0 { out.write_char(',')?; }
        out.write_str("{\"name\":")?; out.quote(name)?;
        write!(out, ",\"offset\":{offset},\"type\":")?; out.quote(ty)?;
        write!(out, ",\"width\":{width}}}")?;
    }
    out.write_str("],\"output_bytes\":32,\"reason_codes\":{\"IR_ARGUMENT\":8,\"IR_BOUNDS\":4,\"IR_CYCLE\":6,\"IR_JSON\":1,\"IR_OVERFLOW\":9,\"IR_REFERENCE\":5,\"IR_SHAPE\":3,\"IR_TYPE\":7,\"IR_VERSION\":2,\"IR_WORK\":10,\"success\":0},\"regions_disjoint\":true,\"signature\":")?;
    out.quote(SIGNATURE)?;
    out.write_str(",\"status_codes\":{\"integer-overflow\":1,\"invalid-ir\":3,\"success\":0,\"work-limit\":2},\"symbol\":\"bagaev_probe_entry\",\"type_codes\":{\"Bool\":2,\"Int64\":1,\"absent\":0}},\"cpu\":")?;
    out.quote(CPU)?; write!(out, ",\"entry\":{},\"functions\":[",program.entry())?;
    for (i,function) in program.functions().iter().enumerate() {
        if i>0 { out.write_char(',')?; }
        write!(out, "{{\"body\":{},\"callees\":[",function.body())?;
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
    out.write_str(std::str::from_utf8(program.canonical_bytes()).map_err(|_|EmitError::Interface)?)?;
    out.write_str(",\"program_pin\":")?; out.quote(program.identity())?;
    out.write_str(",\"schema\":\"bagaev-probe-llvm-binding/1\",\"semantic\":\"bagaev-probe-ir/1\",\"target\":")?;
    out.quote(TARGET)?; out.write_str(",\"work_limit\":65536}")?;
    Ok(out.value)
}

/// One builder per checked function. SSA names and blocks never use source names.
struct FunctionEmitter<'a, 'b> {
    program: &'a CheckedProgram, output: &'b mut Text,
    function: usize, next: usize, current: String,
}
impl FunctionEmitter<'_, '_> {
    fn fresh(&mut self) -> String { let n=self.next; self.next+=1; format!("t{n}") }
    fn value(&mut self, rhs: &str) -> Result<String> {
        let name=self.fresh(); writeln!(self.output,"  %{name} = {rhs}")?; Ok(format!("%{name}"))
    }
    fn label(&mut self, name: &str) -> Result<()> {
        writeln!(self.output,"{name}:")?; self.current=name.to_owned(); Ok(())
    }
    fn branch(&mut self, target: &str) -> Result<()> {
        writeln!(self.output,"  br label %{target}")?; Ok(())
    }
    fn fail(&mut self, status: u32, node: NodeId) -> Result<()> {
        writeln!(self.output,"  store volatile i32 {status}, ptr %status, align 4\n  store volatile i32 {node}, ptr %location, align 4")?;
        self.branch("failed")
    }
    fn tick(&mut self, node: NodeId) -> Result<()> {
        let work=self.value("load volatile i64, ptr %work, align 8")?;
        let full=self.value(&format!("icmp uge i64 {work}, 65536"))?;
        let refuse=self.fresh(); let reached=self.fresh();
        writeln!(self.output,"  br i1 {full}, label %{refuse}, label %{reached}")?;
        self.label(&refuse)?; self.fail(2,node)?; self.label(&reached)?;
        // Plain add has modular defined semantics; reachable range is 0..65535.
        let increment=self.value(&format!("add i64 {work}, 1"))?;
        writeln!(self.output,"  store volatile i64 {increment}, ptr %work, align 8")?; Ok(())
    }
    fn expression(&mut self, id: NodeId) -> Result<String> {
        let node=self.program.node(id).ok_or(EmitError::Interface)?;
        if node.function()!=self.function { return Err(EmitError::Interface); }
        // Clone only a bounded checked enum so recursive emission borrows no node.
        let kind=node.kind().clone();
        writeln!(self.output,"  ; node {id}")?; self.tick(id)?;
        match kind {
            NodeKind::Int(n)=>Ok(n.to_string()), NodeKind::Bool(b)=>Ok(if b {"1"} else {"0"}.to_owned()),
            NodeKind::Arg{parameter}=>Ok(format!("%arg{parameter}")),
            NodeKind::Use{slot}=>self.value(&format!("load i64, ptr %local{slot}, align 8")),
            NodeKind::Binary{op,left,right}=>{
                let left=self.expression(left)?; let right=self.expression(right)?;
                match op {
                    BinaryOp::Add|BinaryOp::Sub|BinaryOp::Mul=>{
                        let intrinsic=match op {BinaryOp::Add=>"sadd",BinaryOp::Sub=>"ssub",_=>"smul"};
                        let pair=self.value(&format!("call {{ i64, i1 }} @llvm.{intrinsic}.with.overflow.i64(i64 {left}, i64 {right})"))?;
                        let overflow=self.value(&format!("extractvalue {{ i64, i1 }} {pair}, 1"))?;
                        let refuse=self.fresh(); let normal=self.fresh();
                        writeln!(self.output,"  br i1 {overflow}, label %{refuse}, label %{normal}")?;
                        self.label(&refuse)?; self.fail(1,id)?; self.label(&normal)?;
                        self.value(&format!("extractvalue {{ i64, i1 }} {pair}, 0"))
                    }
                    BinaryOp::Eq|BinaryOp::Lt|BinaryOp::Le=>{
                        let predicate=match op {BinaryOp::Eq=>"eq",BinaryOp::Lt=>"slt",_=>"sle"};
                        let bit=self.value(&format!("icmp {predicate} i64 {left}, {right}"))?;
                        self.value(&format!("zext i1 {bit} to i64"))
                    }
                }
            }
            NodeKind::Not{operand}=>{
                let value=self.expression(operand)?; self.value(&format!("xor i64 {value}, 1"))
            }
            NodeKind::Let{slot,value,body,..}=>{
                let value=self.expression(value)?;
                writeln!(self.output,"  store i64 {value}, ptr %local{slot}, align 8")?;
                self.expression(body)
            }
            NodeKind::If{condition,yes,no}=>{
                let value=self.expression(condition)?;
                let condition=self.value(&format!("icmp ne i64 {value}, 0"))?;
                let yes_label=self.fresh(); let no_label=self.fresh(); let merge=self.fresh();
                writeln!(self.output,"  br i1 {condition}, label %{yes_label}, label %{no_label}")?;
                self.label(&yes_label)?; let yes_value=self.expression(yes)?;
                let yes_exit=self.current.clone(); self.branch(&merge)?;
                self.label(&no_label)?; let no_value=self.expression(no)?;
                let no_exit=self.current.clone(); self.branch(&merge)?;
                self.label(&merge)?;
                self.value(&format!("phi i64 [ {yes_value}, %{yes_exit} ], [ {no_value}, %{no_exit} ]"))
            }
            NodeKind::Call{function,arguments}=>{
                let mut args=String::from("ptr %work, ptr %status, ptr %location");
                for argument in arguments {
                    let value=self.expression(argument)?; write!(args,", i64 {value}")?;
                }
                let value=self.value(&format!("call i64 @probe_fn{function}({args})"))?;
                let status=self.value("load volatile i32, ptr %status, align 4")?;
                let failed=self.value(&format!("icmp ne i32 {status}, 0"))?;
                let next=self.fresh();
                writeln!(self.output,"  br i1 {failed}, label %failed, label %{next}")?;
                self.label(&next)?; Ok(value)
            }
            NodeKind::Loop{count,index_slot,accumulator_slot,initial,body,..}=>{
                let initial=self.expression(initial)?;
                writeln!(self.output,"  store i64 0, ptr %local{index_slot}, align 8\n  store i64 {initial}, ptr %local{accumulator_slot}, align 8")?;
                let header=self.fresh(); let iteration=self.fresh(); let done=self.fresh();
                self.branch(&header)?; self.label(&header)?;
                let index=self.value(&format!("load i64, ptr %local{index_slot}, align 8"))?;
                let more=self.value(&format!("icmp ult i64 {index}, {count}"))?;
                writeln!(self.output,"  br i1 {more}, label %{iteration}, label %{done}")?;
                self.label(&iteration)?; let value=self.expression(body)?;
                writeln!(self.output,"  store i64 {value}, ptr %local{accumulator_slot}, align 8")?;
                let next=self.value(&format!("add i64 {index}, 1"))?;
                writeln!(self.output,"  store i64 {next}, ptr %local{index_slot}, align 8")?;
                self.branch(&header)?; self.label(&done)?;
                self.value(&format!("load i64, ptr %local{accumulator_slot}, align 8"))
            }
        }
    }
}

fn function(program: &CheckedProgram, index: usize, out: &mut Text) -> Result<()> {
    let function=&program.functions()[index];
    write!(out,"define internal i64 @probe_fn{index}(ptr %work, ptr %status, ptr %location")?;
    for i in 0..function.parameters().len() { write!(out,", i64 %arg{i}")?; }
    out.write_str(") #0 {\nentry:\n")?;
    // Allocate all binders once at function entry, never on a loop back edge.
    for i in 0..function.locals().len() { writeln!(out,"  %local{i} = alloca i64, align 8")?; }
    let mut emitter=FunctionEmitter{program,output:out,function:index,next:0,current:"entry".to_owned()};
    let value=emitter.expression(function.body())?;
    writeln!(emitter.output,"  ret i64 {value}\nfailed:\n  ret i64 0\n}}\n")?; Ok(())
}

fn output_writer(out: &mut Text) -> Result<()> {
    out.write_str("define internal void @probe_write(ptr %out, i32 %status, i32 %type, i64 %value, i64 %work, i32 %reason, i32 %location) #0 {\nentry:\n")?;
    for (offset,ty,name,align) in [(0,"i32","status",4),(4,"i32","type",4),(8,"i64","value",8),(16,"i64","work",8),(24,"i32","reason",4),(28,"i32","location",4)] {
        writeln!(out,"  %o{offset} = getelementptr i8, ptr %out, i64 {offset}\n  store volatile {ty} %{name}, ptr %o{offset}, align {align}")?;
    }
    out.write_str("  ret void\n}\n\n")?; Ok(())
}

fn entry(program: &CheckedProgram, out: &mut Text) -> Result<()> {
    let function=&program.functions()[program.entry()];
    out.write_str("define ccc void @bagaev_probe_entry(ptr %arguments, ptr %output) #0 {\nentry:\n  %work = alloca i64, align 8\n  %status = alloca i32, align 4\n  %location = alloca i32, align 4\n")?;
    // Volatile native-width accesses retain all eight reads, even inactive slots.
    // All output stores are volatile too, retaining their order after these loads.
    for i in 0..8 {
        writeln!(out,"  %input{i} = getelementptr i8, ptr %arguments, i64 {}\n  %arg{i} = load volatile i64, ptr %input{i}, align 8",8*i)?;
    }
    out.write_str("  store volatile i64 0, ptr %work, align 8\n  store volatile i32 0, ptr %status, align 4\n  store volatile i32 0, ptr %location, align 4\n")?;
    for i in 0..8 {
        let active=function.parameters().get(i).map(|p|p.ty());
        let test=match active { Some(Type::Int64)=>continue, Some(Type::Bool)=>format!("icmp ule i64 %arg{i}, 1"), None=>format!("icmp eq i64 %arg{i}, 0") };
        writeln!(out,"  %valid{i} = {test}\n  br i1 %valid{i}, label %slot{i}_ok, label %slot{i}_bad\nslot{i}_bad:\n  call void @probe_write(ptr %output, i32 3, i32 0, i64 0, i64 0, i32 8, i32 {})\n  ret void\nslot{i}_ok:",2147483649u32+i as u32)?;
    }
    write!(out,"  %result = call i64 @probe_fn{}(ptr %work, ptr %status, ptr %location",program.entry())?;
    for i in 0..function.parameters().len() { write!(out,", i64 %arg{i}")?; }
    out.write_str(")\n  %final_status = load volatile i32, ptr %status, align 4\n  %final_work = load volatile i64, ptr %work, align 8\n  %final_location = load volatile i32, ptr %location, align 4\n  %success = icmp eq i32 %final_status, 0\n  br i1 %success, label %success_result, label %failure_result\nsuccess_result:\n")?;
    writeln!(out,"  call void @probe_write(ptr %output, i32 0, i32 {}, i64 %result, i64 %final_work, i32 0, i32 0)\n  ret void\nfailure_result:\n  %is_overflow = icmp eq i32 %final_status, 1\n  %reason = select i1 %is_overflow, i32 9, i32 10\n  call void @probe_write(ptr %output, i32 %final_status, i32 0, i64 0, i64 %final_work, i32 %reason, i32 %final_location)\n  ret void\n}}\n",type_code(function.result()))?;
    Ok(())
}

fn emit(program: &CheckedProgram, module_limit: usize, binding_limit: usize) -> Result<Module> {
    let description=descriptor(program,binding_limit)?;
    let mut out=Text::new(module_limit);
    out.write_str("; bagaev-probe-llvm/1: fixed typed kernel, data binding is not authority\nsource_filename = \"bagaev-probe-llvm\"\ntarget datalayout = \"e-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128\"\n")?;
    writeln!(out,"target triple = \"{TARGET}\"\n")?;
    // Literal byte escaping avoids LLVM syntax injection and preserves exact UTF-8.
    write!(out,"@bagaev_probe_binding = constant [{} x i8] c\"",description.len())?;
    for byte in description.bytes() { write!(out,"\\{byte:02X}")?; }
    writeln!(out,"\", align 1\n@bagaev_probe_binding_length = constant i64 {}, align 8\n",description.len())?;
    for op in ["sadd","ssub","smul"] {
        writeln!(out,"declare {{ i64, i1 }} @llvm.{op}.with.overflow.i64(i64, i64)")?;
    }
    out.write_char('\n')?; output_writer(&mut out)?;
    for index in 0..program.functions().len() { function(program,index,&mut out)?; }
    entry(program,&mut out)?;
    writeln!(out,"attributes #0 = {{ \"target-cpu\"=\"{CPU}\" }}")?;
    let bytes=out.value.into_bytes(); let identity=sha256::digest(&bytes);
    let mut binding=Text::new(binding_limit);
    binding.write_str("{\"artifact_pin\":")?; binding.quote(&identity)?;
    write!(binding,",\"binding\":{description},\"binding_pin\":")?;
    binding.quote(&sha256::digest(description.as_bytes()))?;
    write!(binding,",\"module_bytes\":{},\"schema\":\"bagaev-probe-llvm-module/1\"}}\n",bytes.len())?;
    Ok(Module{bytes,binding:binding.value.into_bytes(),identity})
}

pub fn emit_program(program: &CheckedProgram) -> Result<Module> {
    emit(program,MODULE_LIMIT,BINDING_LIMIT)
}

#[cfg(test)]
pub(crate) fn emit_with_limits(program: &CheckedProgram, module: usize, binding: usize) -> Result<Module> {
    emit(program,module,binding)
}
