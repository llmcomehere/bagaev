//! Deterministic textual LLVM 21 AOT lowering of the complete checked kernel.
//! This library constructs bytes only. It neither executes nor admits an artifact.
use crate::option_ir::{BinaryOp, NodeId, NodeKind, Type};
use crate::typed_option::CheckedSource as CheckedProgram;
use crate::{canonical, sha256};
use std::fmt::{self, Write};

pub const MODULE_LIMIT: usize = 8 * 1024 * 1024;
pub const BINDING_LIMIT: usize = 2 * 1024 * 1024;
pub const TARGET: &str = "x86_64-unknown-linux-gnu";
pub const CPU: &str = "x86-64";
pub const SIGNATURE: &str = "void bagaev_option_kernel(const void *validated_values, void *output)";

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

fn type_code(ty: Type) -> u32 { match ty { Type::Int64 => 1, Type::Bool => 2, Type::Text=>3, Type::OptionInt64=>4 } }

/// Includes the whole semantic program, all signatures/locals/edges and all nodes.
/// Embedded in the module as data only; native evaluation never reads this data.
fn llvm_ty(ty:Type)->&'static str{match ty{Type::Text=>"%Text",Type::OptionInt64=>"%Option",_=>"i64"}}
fn zero(ty:Type)->&'static str{if matches!(ty,Type::Text|Type::OptionInt64){"zeroinitializer"}else{"0"}}
fn descriptor(program:&CheckedProgram,limit:usize)->Result<String>{
 let mut out=Text::new(limit);
 out.write_str("{\"execution_admission\":false,\"schema\":\"bagaev-option-llvm-binding/1\",\"signature\":")?;
 out.quote(SIGNATURE)?;out.write_str(",\"source\":")?;
 out.quote(std::str::from_utf8(program.canonical_bytes()).map_err(|_|EmitError::Interface)?)?;
 out.write_str(",\"source_pin\":")?;out.quote(program.identity())?;
 out.write_char('}')?;Ok(out.value)
}

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
    fn charge(&mut self, amount:&str,node:NodeId)->Result<()> {
        let work=self.value("load volatile i64, ptr %work, align 8")?;
        let remaining=self.value(&format!("sub i64 65536, {work}"))?;
        let full=self.value(&format!("icmp ugt i64 {amount}, {remaining}"))?;
        let refuse=self.fresh();let reached=self.fresh();
        writeln!(self.output,"  br i1 {full}, label %{refuse}, label %{reached}")?;
        self.label(&refuse)?;self.fail(2,node)?;self.label(&reached)?;
        let increment=self.value(&format!("add i64 {work}, {amount}"))?;
        writeln!(self.output,"  store volatile i64 {increment}, ptr %work, align 8")?;Ok(())
    }
    fn tick(&mut self,node:NodeId)->Result<()>{self.charge("1",node)}
    fn expression(&mut self, id: NodeId) -> Result<String> {
        let node=self.program.node(id).ok_or(EmitError::Interface)?;
        if node.function()!=self.function { return Err(EmitError::Interface); }
        // Clone only a bounded checked enum so recursive emission borrows no node.
        let kind=node.kind().clone(); let ty=llvm_ty(node.ty());
        writeln!(self.output,"  ; node {id}")?; self.tick(id)?;
        match kind {
            NodeKind::Int(n)=>Ok(n.to_string()), NodeKind::Bool(b)=>Ok(if b {"1"} else {"0"}.to_owned()),
            NodeKind::Arg{parameter}=>Ok(format!("%arg{parameter}")),
            NodeKind::Use{slot}=>self.value(&format!("load {ty}, ptr %local{slot}, align 8")),
            NodeKind::OptionNone=>Ok("zeroinitializer".to_owned()),
            NodeKind::OptionSome{operand}=>{
                let value=self.expression(operand)?;
                let present=self.value("insertvalue %Option zeroinitializer, i64 1, 0")?;
                self.value(&format!("insertvalue %Option {present}, i64 {value}, 1"))
            }
            NodeKind::OptionHas{operand}=>{let value=self.expression(operand)?;self.value(&format!("extractvalue %Option {value}, 0"))}
            NodeKind::OptionOr{option,fallback}=>{
                let value=self.expression(option)?;let flag=self.value(&format!("extractvalue %Option {value}, 0"))?;
                let present=self.value(&format!("icmp ne i64 {flag}, 0"))?;let yes=self.fresh();let no=self.fresh();let merge=self.fresh();
                writeln!(self.output,"  br i1 {present}, label %{yes}, label %{no}")?;
                self.label(&yes)?;let payload=self.value(&format!("extractvalue %Option {value}, 1"))?;let yes_exit=self.current.clone();self.branch(&merge)?;
                self.label(&no)?;let other=self.expression(fallback)?;let no_exit=self.current.clone();self.branch(&merge)?;
                self.label(&merge)?;self.value(&format!("phi i64 [ {payload}, %{yes_exit} ], [ {other}, %{no_exit} ]"))
            }
            NodeKind::Text(text)=>{
                self.charge(&text.len().to_string(),id)?;
                let a=self.value(&format!("insertvalue %Text zeroinitializer, ptr @text{id}, 0"))?;
                let b=self.value(&format!("insertvalue %Text {a}, i64 {}, 1",text.len()))?;
                self.value(&format!("insertvalue %Text {b}, i64 {}, 2",text.chars().count()))
            }
            NodeKind::TextLength{scalars,operand}=>{
                let value=self.expression(operand)?;
                self.value(&format!("extractvalue %Text {value}, {}",if scalars{2}else{1}))
            }
            NodeKind::TextBinary{equal,left,right}=>{
                let a=self.expression(left)?;let b=self.expression(right)?;
                let al=self.value(&format!("extractvalue %Text {a}, 1"))?;let bl=self.value(&format!("extractvalue %Text {b}, 1"))?;
                let cost=self.value(&format!("add i64 {al}, {bl}"))?;self.charge(&cost,id)?;
                let ap=self.value(&format!("extractvalue %Text {a}, 0"))?;let bp=self.value(&format!("extractvalue %Text {b}, 0"))?;
                let order=self.value(&format!("call i64 @text_compare(ptr {ap}, i64 {al}, ptr {bp}, i64 {bl})"))?;
                let bit=self.value(&format!("icmp {} i64 {order}, 0",if equal{"eq"}else{"slt"}))?;
                self.value(&format!("zext i1 {bit} to i64"))
            }
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
            NodeKind::Let{slot,value,body,declared}=>{
                let stored=llvm_ty(declared);
                let value=self.expression(value)?;
                writeln!(self.output,"  store {stored} {value}, ptr %local{slot}, align 8")?;
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
                self.value(&format!("phi {ty} [ {yes_value}, %{yes_exit} ], [ {no_value}, %{no_exit} ]"))
            }
            NodeKind::Call{function,arguments}=>{
                let mut args=String::from("ptr %work, ptr %status, ptr %location");
                for argument in arguments {
                    let value=self.expression(argument)?; write!(args,", {} {value}",llvm_ty(self.program.node(argument).ok_or(EmitError::Interface)?.ty()))?;
                }
                let value=self.value(&format!("call {ty} @probe_fn{function}({args})"))?;
                let status=self.value("load volatile i32, ptr %status, align 4")?;
                let failed=self.value(&format!("icmp ne i32 {status}, 0"))?;
                let next=self.fresh();
                writeln!(self.output,"  br i1 {failed}, label %failed, label %{next}")?;
                self.label(&next)?; Ok(value)
            }
            NodeKind::Loop{count,index_slot,accumulator_slot,initial,body,..}=>{
                let initial=self.expression(initial)?;
                writeln!(self.output,"  store i64 0, ptr %local{index_slot}, align 8\n  store {ty} {initial}, ptr %local{accumulator_slot}, align 8")?;
                let header=self.fresh(); let iteration=self.fresh(); let done=self.fresh();
                self.branch(&header)?; self.label(&header)?;
                let index=self.value(&format!("load i64, ptr %local{index_slot}, align 8"))?;
                let more=self.value(&format!("icmp ult i64 {index}, {count}"))?;
                writeln!(self.output,"  br i1 {more}, label %{iteration}, label %{done}")?;
                self.label(&iteration)?; let value=self.expression(body)?;
                writeln!(self.output,"  store {ty} {value}, ptr %local{accumulator_slot}, align 8")?;
                let next=self.value(&format!("add i64 {index}, 1"))?;
                writeln!(self.output,"  store i64 {next}, ptr %local{index_slot}, align 8")?;
                self.branch(&header)?; self.label(&done)?;
                self.value(&format!("load {ty}, ptr %local{accumulator_slot}, align 8"))
            }
        }
    }
}

fn function(program: &CheckedProgram, index: usize, out: &mut Text) -> Result<()> {
    let function=&program.functions()[index];
    let result=llvm_ty(function.result());
    write!(out,"define internal {result} @probe_fn{index}(ptr %work, ptr %status, ptr %location")?;
    for i in 0..function.parameters().len() { write!(out,", {} %arg{i}",llvm_ty(function.parameters()[i].ty()))?; }
    out.write_str(") #0 {\nentry:\n")?;
    // Allocate all binders once at function entry, never on a loop back edge.
    for i in 0..function.locals().len() { writeln!(out,"  %local{i} = alloca {}, align 8",llvm_ty(function.locals()[i].ty()))?; }
    let mut emitter=FunctionEmitter{program,output:out,function:index,next:0,current:"entry".to_owned()};
    let value=emitter.expression(function.body())?;
    writeln!(emitter.output,"  ret {result} {value}\nfailed:\n  ret {result} {}\n}}\n",zero(function.result()))?; Ok(())
}

fn output_writer(out: &mut Text) -> Result<()> {
    out.write_str("define internal void @probe_write(ptr %out, i32 %status, i32 %type, i64 %value, i64 %work, i32 %reason, i32 %location) #0 {\nentry:\n")?;
    for (offset,ty,name,align) in [(0,"i32","status",4),(4,"i32","type",4),(8,"i64","value",8),(16,"i64","work",8),(24,"i32","reason",4),(28,"i32","location",4)] {
        writeln!(out,"  %o{offset} = getelementptr i8, ptr %out, i64 {offset}\n  store volatile {ty} %{name}, ptr %o{offset}, align {align}")?;
    }
    out.write_str("  ret void\n}\n\n")?; Ok(())
}

fn entry(program:&CheckedProgram,out:&mut Text)->Result<()>{
 let function=&program.functions()[program.entry()];
 out.write_str("define ccc void @bagaev_option_kernel(ptr %arguments, ptr %output) #0 {\nentry:\n  %work = alloca i64, align 8\n  %status = alloca i32, align 4\n  %location = alloca i32, align 4\n  store volatile i64 0, ptr %work, align 8\n  store volatile i32 0, ptr %status, align 4\n  store volatile i32 0, ptr %location, align 4\n")?;
 for (i,p) in function.parameters().iter().enumerate(){
  if p.ty()==Type::OptionInt64{
   let at=32*i;let presence=at+16;
   writeln!(out,"  %payload_ptr{i} = getelementptr i8, ptr %arguments, i64 {at}\n  %payload{i} = load i64, ptr %payload_ptr{i}, align 8\n  %presence_ptr{i} = getelementptr i8, ptr %arguments, i64 {presence}\n  %presence{i} = load i64, ptr %presence_ptr{i}, align 8\n  %some{i} = insertvalue %Option zeroinitializer, i64 %presence{i}, 0\n  %arg{i} = insertvalue %Option %some{i}, i64 %payload{i}, 1")?;
  }else{
   let at=32*i+if p.ty()==Type::Text{8}else{0};let ty=llvm_ty(p.ty());
   writeln!(out,"  %p{i} = getelementptr i8, ptr %arguments, i64 {at}\n  %arg{i} = load {ty}, ptr %p{i}, align 8")?;
  }
 }
 write!(out,"  %result = call i64 @probe_fn{}(ptr %work, ptr %status, ptr %location",program.entry())?;
 for (i,p) in function.parameters().iter().enumerate(){write!(out,", {} %arg{i}",llvm_ty(p.ty()))?;}
 out.write_str(")\n  %s = load volatile i32, ptr %status, align 4\n  %w = load volatile i64, ptr %work, align 8\n  %l = load volatile i32, ptr %location, align 4\n  %ok = icmp eq i32 %s, 0\n  br i1 %ok, label %good, label %bad\ngood:\n")?;
 writeln!(out,"  call void @probe_write(ptr %output, i32 0, i32 {}, i64 %result, i64 %w, i32 0, i32 0)\n  ret void\nbad:\n  %ov = icmp eq i32 %s, 1\n  %r = select i1 %ov, i32 9, i32 10\n  call void @probe_write(ptr %output, i32 %s, i32 0, i64 0, i64 %w, i32 %r, i32 %l)\n  ret void\n}}",type_code(function.result()))?;Ok(())
}

fn emit(program: &CheckedProgram, module_limit: usize, binding_limit: usize) -> Result<Module> {
    let description=descriptor(program,binding_limit)?;
    let mut out=Text::new(module_limit);
    out.write_str("; bagaev-option-llvm/1: fixed typed kernel, data binding is not authority\nsource_filename = \"bagaev-probe-llvm\"\ntarget datalayout = \"e-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128\"\n")?;
    writeln!(out,"target triple = \"{TARGET}\"\n")?;
    // Literal byte escaping avoids LLVM syntax injection and preserves exact UTF-8.
    write!(out,"@bagaev_probe_binding = constant [{} x i8] c\"",description.len())?;
    for byte in description.bytes() { write!(out,"\\{byte:02X}")?; }
    writeln!(out,"\", align 1\n@bagaev_probe_binding_length = constant i64 {}, align 8\n",description.len())?;
    for op in ["sadd","ssub","smul"] {
        writeln!(out,"declare {{ i64, i1 }} @llvm.{op}.with.overflow.i64(i64, i64)")?;
    }
    out.write_str("%Text = type { ptr, i64, i64 }\n%Option = type { i64, i64 }\n")?;
    out.write_str(include_str!("text_compare.ll"))?;
    for node in program.nodes(){if let NodeKind::Text(value)=node.kind(){write!(out,"@text{} = private constant [{} x i8] c\"",node.id(),value.len())?;for b in value.bytes(){write!(out,"\\{b:02X}")?;}out.write_str("\", align 1\n")?;}}
    out.write_char('\n')?; output_writer(&mut out)?;
    for index in 0..program.functions().len() { function(program,index,&mut out)?; }
    entry(program,&mut out)?;
    writeln!(out,"attributes #0 = {{ \"target-cpu\"=\"{CPU}\" }}")?;
    let bytes=out.value.into_bytes(); let identity=sha256::digest(&bytes);
    let mut binding=Text::new(binding_limit);
    binding.write_str("{\"artifact_pin\":")?; binding.quote(&identity)?;
    write!(binding,",\"binding\":{description},\"binding_pin\":")?;
    binding.quote(&sha256::digest(description.as_bytes()))?;
    write!(binding,",\"module_bytes\":{},\"schema\":\"bagaev-option-llvm-module/1\"}}\n",bytes.len())?;
    Ok(Module{bytes,binding:binding.value.into_bytes(),identity})
}

pub fn emit_program(program: &CheckedProgram) -> Result<Module> {
    emit(program,MODULE_LIMIT,BINDING_LIMIT)
}

#[cfg(test)]
pub(crate) fn emit_with_limits(program: &CheckedProgram, module: usize, binding: usize) -> Result<Module> {
    emit(program,module,binding)
}
