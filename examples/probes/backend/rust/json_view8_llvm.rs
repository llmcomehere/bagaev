//! Deterministic textual LLVM 21 AOT lowering of the complete checked kernel.
//! This library constructs bytes only. It neither executes nor admits an artifact.
use crate::record_ir::{BinaryOp, NodeId, NodeKind, Type};
use crate::typed_record::CheckedSource as CheckedProgram;
use crate::{canonical, sha256};
use std::fmt::{self, Write};

pub const MODULE_LIMIT: usize = 8 * 1024 * 1024;
pub const BINDING_LIMIT: usize = 2 * 1024 * 1024;
pub const TARGET: &str = "x86_64-unknown-linux-gnu";
pub const CPU: &str = "x86-64";
pub const SIGNATURE: &str = "void bagaev_json_view8_kernel(const void *validated_values, void *arena, void *cells, void *output)";

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

fn type_code(ty: Type) -> u32 { match ty { Type::Int64 => 1, Type::Bool => 2, Type::Text=>3, Type::OptionInt64=>4, Type::TextList=>5,Type::Record(_)=>6,Type::RecordList(_)=>7,Type::Variant(_)=>8,_=>0 } }

/// Includes the whole semantic program, all signatures/locals/edges and all nodes.
/// Embedded in the module as data only; native evaluation never reads this data.
fn llvm_ty(ty:Type)->String{match ty{Type::Json=>"ptr".into(),Type::Variant(_)=>"%Variant".into(),Type::Record(_)=>"%Record".into(),Type::RecordList(_)=>"%Records".into(),Type::TextList=>"%List".into(),Type::Text=>"%Text".into(),Type::OptionInt64=>"%Option".into(),_=>"i64".into()}}
fn zero(ty:Type)->&'static str{if ty==Type::Json{return "null";}if matches!(ty,Type::Text|Type::OptionInt64|Type::TextList|Type::Record(_)|Type::RecordList(_)|Type::Variant(_)){"zeroinitializer"}else{"0"}}
fn descriptor(program:&CheckedProgram,limit:usize)->Result<String>{
 let mut out=Text::new(limit);
 out.write_str("{\"cell_capacity\":65536,\"execution_admission\":false,\"schema\":\"bagaev-json-view8-llvm-binding/1\",\"scratch_capacity\":65536,\"signature\":")?;
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
    fn refuse_if(&mut self, condition:&str,status:u32,node:NodeId)->Result<()> {
        let bad=self.fresh();let good=self.fresh();
        writeln!(self.output,"  br i1 {condition}, label %{bad}, label %{good}")?;
        self.label(&bad)?;self.fail(status,node)?;self.label(&good)
    }
    fn allocate(&mut self,n:&str,node:NodeId)->Result<String>{
        let ptr=self.value(&format!("call ptr @list_alloc(ptr %arena, i64 {n})"))?;
        let bad=self.value(&format!("icmp eq ptr {ptr}, null"))?;self.refuse_if(&bad,6,node)?;Ok(ptr)
    }
    fn list_value(&mut self,ptr:&str,n:&str,bytes:&str)->Result<String>{
        let a=self.value(&format!("insertvalue %List zeroinitializer, ptr {ptr}, 0"))?;
        let b=self.value(&format!("insertvalue %List {a}, i64 {n}, 1"))?;
        self.value(&format!("insertvalue %List {b}, i64 {bytes}, 2"))
    }
    fn store_cell(&mut self,cell:&str,ty:Type,value:&str)->Result<()>{
        writeln!(self.output,"  store %Cell zeroinitializer, ptr {cell}, align 8")?;
        match ty{
            Type::Int64|Type::Bool=>writeln!(self.output,"  store i64 {value}, ptr {cell}, align 8")?,
            Type::Text|Type::TextList=>{let ptr=self.value(&format!("getelementptr i8, ptr {cell}, i64 8"))?;writeln!(self.output,"  store {} {value}, ptr {ptr}, align 8",llvm_ty(ty))?;},
            Type::OptionInt64=>{
                let presence=self.value(&format!("extractvalue %Option {value}, 0"))?;let payload=self.value(&format!("extractvalue %Option {value}, 1"))?;let ptr=self.value(&format!("getelementptr i8, ptr {cell}, i64 16"))?;
                writeln!(self.output,"  store i64 {payload}, ptr {cell}, align 8
  store i64 {presence}, ptr {ptr}, align 8")?;
            },
            Type::Variant(_)=>{
                let tag=self.value(&format!("extractvalue %Variant {value}, 0"))?;
                let pointer=self.value(&format!("extractvalue %Variant {value}, 1"))?;
                let pp=self.value(&format!("getelementptr i8, ptr {cell}, i64 8"))?;
                writeln!(self.output,"  store i64 {tag}, ptr {cell}, align 8\n  store ptr {pointer}, ptr {pp}, align 8")?;
            },
            Type::RecordList(_)=>{
                let pointer=self.value(&format!("extractvalue %Records {value}, 0"))?;
                let count=self.value(&format!("extractvalue %Records {value}, 1"))?;
                let pp=self.value(&format!("getelementptr i8, ptr {cell}, i64 8"))?;
                let np=self.value(&format!("getelementptr i8, ptr {cell}, i64 16"))?;
                writeln!(self.output,"  store ptr {pointer}, ptr {pp}, align 8\n  store i64 {count}, ptr {np}, align 8")?;
            },
            Type::Record(_)=>{let pointer=self.value(&format!("extractvalue %Record {value}, 0"))?;let ptr=self.value(&format!("getelementptr i8, ptr {cell}, i64 8"))?;writeln!(self.output,"  store ptr {pointer}, ptr {ptr}, align 8")?;},
            _=>return Err(EmitError::Interface),
        }Ok(())
    }
    fn load_cell(&mut self,cell:&str,ty:Type)->Result<String>{
        match ty{
            Type::Int64|Type::Bool=>self.value(&format!("load i64, ptr {cell}, align 8")),
            Type::Text|Type::TextList=>{let ptr=self.value(&format!("getelementptr i8, ptr {cell}, i64 8"))?;self.value(&format!("load {}, ptr {ptr}, align 8",llvm_ty(ty)))},
            Type::OptionInt64=>{
                let payload=self.value(&format!("load i64, ptr {cell}, align 8"))?;let ptr=self.value(&format!("getelementptr i8, ptr {cell}, i64 16"))?;let presence=self.value(&format!("load i64, ptr {ptr}, align 8"))?;
                let v=self.value(&format!("insertvalue %Option zeroinitializer, i64 {presence}, 0"))?;self.value(&format!("insertvalue %Option {v}, i64 {payload}, 1"))
            },
            Type::Variant(_)=>{
                let tag=self.value(&format!("load i64, ptr {cell}, align 8"))?;
                let pp=self.value(&format!("getelementptr i8, ptr {cell}, i64 8"))?;
                let pointer=self.value(&format!("load ptr, ptr {pp}, align 8"))?;
                self.variant_value(&tag,&pointer)
            },
            Type::RecordList(_)=>{
                let pp=self.value(&format!("getelementptr i8, ptr {cell}, i64 8"))?;
                let np=self.value(&format!("getelementptr i8, ptr {cell}, i64 16"))?;
                let pointer=self.value(&format!("load ptr, ptr {pp}, align 8"))?;
                let count=self.value(&format!("load i64, ptr {np}, align 8"))?;
                self.records_value(&pointer,&count)
            },
            Type::Record(_)=>{let ptr=self.value(&format!("getelementptr i8, ptr {cell}, i64 8"))?;let value=self.value(&format!("load ptr, ptr {ptr}, align 8"))?;self.value(&format!("insertvalue %Record zeroinitializer, ptr {value}, 0"))},
            _=>Err(EmitError::Interface),
        }
    }
    fn variant_value(&mut self,tag:&str,pointer:&str)->Result<String>{
        let a=self.value(&format!("insertvalue %Variant zeroinitializer, i64 {tag}, 0"))?;
        self.value(&format!("insertvalue %Variant {a}, ptr {pointer}, 1"))
    }
    fn records_value(&mut self,ptr:&str,count:&str)->Result<String>{
        let a=self.value(&format!("insertvalue %Records zeroinitializer, ptr {ptr}, 0"))?;
        self.value(&format!("insertvalue %Records {a}, i64 {count}, 1"))
    }
    fn expression(&mut self, id: NodeId) -> Result<String> {
        let node=self.program.node(id).ok_or(EmitError::Interface)?;
        if node.function()!=self.function { return Err(EmitError::Interface); }
        // Clone only a bounded checked enum so recursive emission borrows no node.
        let kind=node.kind().clone(); let ty=llvm_ty(node.ty());
        writeln!(self.output,"  ; node {id}")?; self.tick(id)?;
        match kind {
            NodeKind::JsonBoolOr{..}=>Err(EmitError::Interface),
            NodeKind::RecordsPush{..}=>Err(EmitError::Interface),
            NodeKind::ListPush{..}=>Err(EmitError::Interface),
            NodeKind::Variant{definition,alternative,value}=>{
                let payload_type=self.program.variant_definitions().get(definition).and_then(|v|v.alternatives().get(alternative)).ok_or(EmitError::Interface)?.1;
                let value=self.expression(value)?;
                let pointer=self.value("call ptr @cells_alloc(ptr %cells, i64 1)")?;
                let bad=self.value(&format!("icmp eq ptr {pointer}, null"))?;self.refuse_if(&bad,6,id)?;
                self.store_cell(&pointer,payload_type,&value)?;
                self.variant_value(&alternative.to_string(),&pointer)
            },
            NodeKind::Match{variant,cases}=>{
                let definition=match self.program.node(variant).ok_or(EmitError::Interface)?.ty(){Type::Variant(n)=>usize::from(n),_=>return Err(EmitError::Interface)};
                let alts=self.program.variant_definitions().get(definition).ok_or(EmitError::Interface)?.alternatives().to_vec();
                let value=self.expression(variant)?;
                let tag=self.value(&format!("extractvalue %Variant {value}, 0"))?;
                let pointer=self.value(&format!("extractvalue %Variant {value}, 1"))?;
                let bad=self.fresh();let merge=self.fresh();let mut arms=Vec::new();
                for case in cases{
                    let at=alts.iter().position(|(name,_)|*name==case.name).ok_or(EmitError::Interface)?;
                    arms.push((case,at,self.fresh()));
                }
                writeln!(self.output,"  switch i64 {tag}, label %{bad} [")?;
                for (_,at,label) in &arms {writeln!(self.output,"    i64 {at}, label %{label}")?;}
                self.output.write_str("  ]\n")?;
                self.label(&bad)?;self.fail(6,id)?;
                let mut results=Vec::new();
                for(case,at,label)in arms{
                    self.label(&label)?;let payload_type=alts[at].1;
                    let payload=self.load_cell(&pointer,payload_type)?;
                    writeln!(self.output,"  store {} {payload}, ptr %local{}, align 8",llvm_ty(payload_type),case.slot)?;
                    let value=self.expression(case.body)?;let predecessor=self.current.clone();self.branch(&merge)?;results.push((value,predecessor));
                }
                self.label(&merge)?;
                let mut phi=format!("phi {ty} ");for(i,(value,pred))in results.iter().enumerate(){if i>0{phi.push_str(", ");}write!(phi,"[ {value}, %{pred} ]")?;}
                self.value(&phi)
            },
            NodeKind::RecordList{definition,values}=>{
                let element=self.program.list_definitions().get(definition).ok_or(EmitError::Interface)?.element();
                let mut evaluated=Vec::new();for child in values{evaluated.push(self.expression(child)?);}
                let n=evaluated.len();
                if n==0{return self.records_value("null","0");}
                let pointer=self.value(&format!("call ptr @cells_alloc(ptr %cells, i64 {n})"))?;
                let bad=self.value(&format!("icmp eq ptr {pointer}, null"))?;self.refuse_if(&bad,6,id)?;
                for(i,value)in evaluated.iter().enumerate(){let cell=self.value(&format!("getelementptr %Cell, ptr {pointer}, i64 {i}"))?;self.store_cell(&cell,Type::Record(element as u8),value)?;}
                self.records_value(&pointer,&n.to_string())
            },
            NodeKind::RecordsLength{list}=>{let value=self.expression(list)?;self.value(&format!("extractvalue %Records {value}, 1"))},
            NodeKind::RecordsAt{list,index}=>{
                let definition=match self.program.node(list).ok_or(EmitError::Interface)?.ty(){Type::RecordList(n)=>usize::from(n),_=>return Err(EmitError::Interface)};
                let element=self.program.list_definitions().get(definition).ok_or(EmitError::Interface)?.element();
                let value=self.expression(list)?;let at=self.expression(index)?;
                let n=self.value(&format!("extractvalue %Records {value}, 1"))?;
                let negative=self.value(&format!("icmp slt i64 {at}, 0"))?;let outside=self.value(&format!("icmp uge i64 {at}, {n}"))?;
                let bad=self.value(&format!("or i1 {negative}, {outside}"))?;self.refuse_if(&bad,5,id)?;
                let pointer=self.value(&format!("extractvalue %Records {value}, 0"))?;
                let cell=self.value(&format!("getelementptr %Cell, ptr {pointer}, i64 {at}"))?;
                self.load_cell(&cell,Type::Record(element as u8))
            },
            NodeKind::Record{definition,values}=>{
                let fields=self.program.record_definitions().get(definition).ok_or(EmitError::Interface)?.fields().to_vec();
                if fields.len()!=values.len(){return Err(EmitError::Interface);}
                if fields.is_empty(){return self.value("insertvalue %Record zeroinitializer, ptr null, 0");}
                let mut evaluated=Vec::new();for child in values{evaluated.push(self.expression(child)?);}
                let pointer=self.value(&format!("call ptr @cells_alloc(ptr %cells, i64 {})",fields.len()))?;
                let bad=self.value(&format!("icmp eq ptr {pointer}, null"))?;self.refuse_if(&bad,6,id)?;
                for(i,((_,ty),value))in fields.iter().zip(&evaluated).enumerate(){let cell=self.value(&format!("getelementptr %Cell, ptr {pointer}, i64 {i}"))?;self.store_cell(&cell,*ty,value)?;}
                self.value(&format!("insertvalue %Record zeroinitializer, ptr {pointer}, 0"))
            },
            NodeKind::Field{record,name}=>{
                let definition=match self.program.node(record).ok_or(EmitError::Interface)?.ty(){Type::Record(n)=>usize::from(n),_=>return Err(EmitError::Interface)};
                let index=self.program.record_definitions().get(definition).ok_or(EmitError::Interface)?.fields().iter().position(|(n,_)|*n==name).ok_or(EmitError::Interface)?;
                let field_type=self.program.node(id).ok_or(EmitError::Interface)?.ty();
                let record=self.expression(record)?;let pointer=self.value(&format!("extractvalue %Record {record}, 0"))?;let cell=self.value(&format!("getelementptr %Cell, ptr {pointer}, i64 {index}"))?;self.load_cell(&cell,field_type)
            },
            NodeKind::JsonKind{operand}=>{let v=self.expression(operand)?;self.value(&format!("call %Text @json_kind(ptr {v})"))},
            NodeKind::JsonLen{operand}=>{let v=self.expression(operand)?;self.value(&format!("call %Option @json_length(ptr {v})"))},
            NodeKind::JsonInt{operand}=>{let v=self.expression(operand)?;let cost=self.value(&format!("call i64 @json_word(ptr {v}, i64 16)"))?;self.charge(&cost,id)?;self.value(&format!("call %Option @json_integer(ptr {v})"))},
            NodeKind::JsonIsText{operand}=>{let v=self.expression(operand)?;let p=self.value(&format!("call ptr @json_pointer(ptr {v}, i64 40)"))?;let valid=self.value(&format!("icmp ne ptr {p}, null"))?;self.value(&format!("zext i1 {valid} to i64"))},
            NodeKind::JsonField{object,key}=>{let v=self.expression(object)?;let count=self.value(&format!("call i64 @json_object_count(ptr {v})"))?;let cost=self.value(&format!("mul i64 {count}, {}",key.len()+1))?;self.charge(&cost,id)?;self.value(&format!("call ptr @json_field(ptr {v}, ptr @json_key{id}, i64 {})",key.len()))},
            NodeKind::JsonAt{array,index}=>{let v=self.expression(array)?;let i=self.expression(index)?;self.value(&format!("call ptr @json_at(ptr {v}, i64 {i})"))},
            NodeKind::JsonTextOr{json,fallback}=>{
                let v=self.expression(json)?;let p=self.value(&format!("call ptr @json_pointer(ptr {v}, i64 40)"))?;let valid=self.value(&format!("icmp ne ptr {p}, null"))?;
                let yes=self.fresh();let no=self.fresh();let merge=self.fresh();writeln!(self.output,"  br i1 {valid}, label %{yes}, label %{no}")?;
                self.label(&yes)?;let cost=self.value(&format!("call i64 @json_word(ptr {v}, i64 48)"))?;self.charge(&cost,id)?;let value=self.value(&format!("call %Text @json_text(ptr {v})"))?;let yes_exit=self.current.clone();self.branch(&merge)?;
                self.label(&no)?;let other=self.expression(fallback)?;let no_exit=self.current.clone();self.branch(&merge)?;
                self.label(&merge)?;self.value(&format!("phi %Text [ {value}, %{yes_exit} ], [ {other}, %{no_exit} ]"))
            },
            NodeKind::Int(n)=>Ok(n.to_string()), NodeKind::Bool(b)=>Ok(if b {"1"} else {"0"}.to_owned()),
            NodeKind::Arg{parameter}=>Ok(format!("%arg{parameter}")),
            NodeKind::Use{slot}=>self.value(&format!("load {ty}, ptr %local{slot}, align 8")),
            NodeKind::List(items)=>{
                let mut values=Vec::new();let mut sum=String::from("0");
                for item in items{let v=self.expression(item)?;let len=self.value(&format!("extractvalue %Text {v}, 1"))?;sum=self.value(&format!("add i64 {sum}, {len}"))?;values.push(v);}
                let too_large=self.value(&format!("icmp ugt i64 {sum}, 4096"))?;self.refuse_if(&too_large,4,id)?;
                let n=values.len().to_string();let ptr=self.allocate(&n,id)?;
                for (i,v) in values.iter().enumerate(){let at=self.value(&format!("getelementptr %Text, ptr {ptr}, i64 {i}"))?;writeln!(self.output,"  store %Text {v}, ptr {at}, align 8")?;}
                self.list_value(&ptr,&n,&sum)
            }
            NodeKind::ListLength{operand}=>{let v=self.expression(operand)?;self.value(&format!("extractvalue %List {v}, 1"))}
            NodeKind::ListAt{list,index}=>{
                let v=self.expression(list)?;let i=self.expression(index)?;let n=self.value(&format!("extractvalue %List {v}, 1"))?;
                let bad=self.value(&format!("icmp uge i64 {i}, {n}"))?;self.refuse_if(&bad,5,id)?;
                let ptr=self.value(&format!("extractvalue %List {v}, 0"))?;let at=self.value(&format!("getelementptr %Text, ptr {ptr}, i64 {i}"))?;self.value(&format!("load %Text, ptr {at}, align 8"))
            }
            NodeKind::ListContains{list,value}=>{
                let v=self.expression(list)?;let q=self.expression(value)?;
                let n=self.value(&format!("extractvalue %List {v}, 1"))?;let bytes=self.value(&format!("extractvalue %List {v}, 2"))?;let qbytes=self.value(&format!("extractvalue %Text {q}, 1"))?;
                let product=self.value(&format!("mul i64 {n}, {qbytes}"))?;let first=self.value(&format!("add i64 {n}, {bytes}"))?;let cost=self.value(&format!("add i64 {first}, {product}"))?;self.charge(&cost,id)?;
                self.value(&format!("call i64 @list_contains(%List {v}, %Text {q})"))
            }
            NodeKind::ListIncreasing{operand}=>{
                let v=self.expression(operand)?;let n=self.value(&format!("extractvalue %List {v}, 1"))?;let bytes=self.value(&format!("extractvalue %List {v}, 2"))?;
                let twice=self.value(&format!("mul i64 2, {bytes}"))?;let cost=self.value(&format!("add i64 {n}, {twice}"))?;self.charge(&cost,id)?;self.value(&format!("call i64 @list_increasing(%List {v})"))
            }
            NodeKind::ListUnique{operand}=>{
                let v=self.expression(operand)?;let n=self.value(&format!("extractvalue %List {v}, 1"))?;let bytes=self.value(&format!("extractvalue %List {v}, 2"))?;
                let square=self.value(&format!("mul i64 {n}, {n}"))?;let product=self.value(&format!("mul i64 {n}, {bytes}"))?;let twice=self.value(&format!("mul i64 2, {product}"))?;let cost=self.value(&format!("add i64 {square}, {twice}"))?;self.charge(&cost,id)?;
                let ptr=self.allocate(&n,id)?;self.value(&format!("call %List @list_unique(%List {v}, ptr {ptr})"))
            }
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
            NodeKind::TextByteAt{text,index}=>{
                let text=self.expression(text)?;let index=self.expression(index)?;
                let len=self.value(&format!("extractvalue %Text {text}, 1"))?;
                let inside=self.value(&format!("icmp ult i64 {index}, {len}"))?;
                let yes=self.fresh();let no=self.fresh();let merge=self.fresh();
                writeln!(self.output,"  br i1 {inside}, label %{yes}, label %{no}")?;
                self.label(&yes)?;
                let ptr=self.value(&format!("extractvalue %Text {text}, 0"))?;
                let at=self.value(&format!("getelementptr i8, ptr {ptr}, i64 {index}"))?;
                let byte=self.value(&format!("load i8, ptr {at}, align 1"))?;
                let wide=self.value(&format!("zext i8 {byte} to i64"))?;
                let present=self.value("insertvalue %Option zeroinitializer, i64 1, 0")?;
                let value=self.value(&format!("insertvalue %Option {present}, i64 {wide}, 1"))?;
                let yes_exit=self.current.clone();self.branch(&merge)?;
                self.label(&no)?;let no_exit=self.current.clone();self.branch(&merge)?;
                self.label(&merge)?;
                self.value(&format!("phi %Option [ {value}, %{yes_exit} ], [ zeroinitializer, %{no_exit} ]"))
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
                let mut args=String::from("ptr %work, ptr %status, ptr %location, ptr %arena, ptr %cells");
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
    write!(out,"define internal {result} @probe_fn{index}(ptr %work, ptr %status, ptr %location, ptr %arena, ptr %cells")?;
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
 out.write_str("define ccc void @bagaev_json_view8_kernel(ptr %arguments, ptr %arena, ptr %cells, ptr %output) #0 {\nentry:\n  call void @llvm.memset.p0.i64(ptr %output, i8 0, i64 64, i1 false)\n  %work = alloca i64, align 8\n  %status = alloca i32, align 4\n  %location = alloca i32, align 4\n  store volatile i64 0, ptr %work, align 8\n  store volatile i32 0, ptr %status, align 4\n  store volatile i32 0, ptr %location, align 4\n")?;
 for (i,p) in function.parameters().iter().enumerate(){
  if p.ty()==Type::OptionInt64{
   let at=32*i;let presence=at+16;
   writeln!(out,"  %payload_ptr{i} = getelementptr i8, ptr %arguments, i64 {at}\n  %payload{i} = load i64, ptr %payload_ptr{i}, align 8\n  %presence_ptr{i} = getelementptr i8, ptr %arguments, i64 {presence}\n  %presence{i} = load i64, ptr %presence_ptr{i}, align 8\n  %some{i} = insertvalue %Option zeroinitializer, i64 %presence{i}, 0\n  %arg{i} = insertvalue %Option %some{i}, i64 %payload{i}, 1")?;
  }else{
   let at=32*i+if matches!(p.ty(),Type::Text|Type::TextList|Type::Record(_)|Type::RecordList(_)|Type::Json){8}else{0};let ty=llvm_ty(p.ty());
   writeln!(out,"  %p{i} = getelementptr i8, ptr %arguments, i64 {at}\n  %arg{i} = load {ty}, ptr %p{i}, align 8")?;
  }
 }
 let result_ty=llvm_ty(function.result());
 write!(out,"  %result = call {result_ty} @probe_fn{}(ptr %work, ptr %status, ptr %location, ptr %arena, ptr %cells",program.entry())?;
 for (i,p) in function.parameters().iter().enumerate(){write!(out,", {} %arg{i}",llvm_ty(p.ty()))?;}
 out.write_str(")\n  %s = load volatile i32, ptr %status, align 4\n  %w = load volatile i64, ptr %work, align 8\n  %l = load volatile i32, ptr %location, align 4\n  %ok = icmp eq i32 %s, 0\n  br i1 %ok, label %good, label %bad\ngood:\n")?;
 let inline=match function.result(){Type::Int64|Type::Bool=>"%result".to_owned(),Type::Record(n)|Type::RecordList(n)|Type::Variant(n)=>n.to_string(),_=>"0".to_owned()};
 match function.result(){
  Type::Variant(_)=>{writeln!(out,"  %variant_out = getelementptr i8, ptr %output, i64 32\n  store %Variant %result, ptr %variant_out, align 8")?;}
  Type::Record(_)=>{out.write_str("  %record_pointer = extractvalue %Record %result, 0\n  %record_out = getelementptr i8, ptr %output, i64 40\n  store ptr %record_pointer, ptr %record_out, align 8\n")?;}
  Type::Text|Type::TextList|Type::RecordList(_)=>{writeln!(out,"  %compound = getelementptr i8, ptr %output, i64 40\n  store {result_ty} %result, ptr %compound, align 8")?;}
  Type::OptionInt64=>{out.write_str("  %compound_payload = extractvalue %Option %result, 1\n  %compound_presence = extractvalue %Option %result, 0\n  %payload_out = getelementptr i8, ptr %output, i64 32\n  %presence_out = getelementptr i8, ptr %output, i64 48\n  store i64 %compound_payload, ptr %payload_out, align 8\n  store i64 %compound_presence, ptr %presence_out, align 8\n")?;}
  _=>{}
 }
 writeln!(out,"  call void @probe_write(ptr %output, i32 0, i32 {}, i64 {inline}, i64 %w, i32 0, i32 0)\n  ret void\nbad:\n  %ov = icmp eq i32 %s, 1\n  %is_work = icmp eq i32 %s, 2\n  %is_bound = icmp eq i32 %s, 4\n  %is_index = icmp eq i32 %s, 5\n  %r1 = select i1 %is_index, i32 12, i32 13\n  %r2 = select i1 %is_bound, i32 11, i32 %r1\n  %r3 = select i1 %is_work, i32 10, i32 %r2\n  %r = select i1 %ov, i32 9, i32 %r3\n  call void @probe_write(ptr %output, i32 %s, i32 0, i64 0, i64 %w, i32 %r, i32 %l)\n  ret void\n}}",type_code(function.result()))?;Ok(())
}

fn emit(program: &CheckedProgram, module_limit: usize, binding_limit: usize) -> Result<Module> {
    if program.profile()>8{return Err(EmitError::Interface);}
    if program.nodes().len()>2048||program.functions().len()>32{return Err(EmitError::Interface);}
    let entry_fn=&program.functions()[program.entry()];
    if entry_fn.result()==Type::Json||entry_fn.parameters().iter().any(|p|p.ty()!=Type::Json){return Err(EmitError::Interface);}
    let description=descriptor(program,binding_limit)?;
    let mut out=Text::new(module_limit);
    out.write_str("; bagaev-json-view8-llvm/1: fixed typed kernel, data binding is not authority\nsource_filename = \"bagaev-probe-llvm\"\ntarget datalayout = \"e-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128\"\n")?;
    writeln!(out,"target triple = \"{TARGET}\"\n")?;
    // Literal byte escaping avoids LLVM syntax injection and preserves exact UTF-8.
    write!(out,"@bagaev_probe_binding = constant [{} x i8] c\"",description.len())?;
    for byte in description.bytes() { write!(out,"\\{byte:02X}")?; }
    writeln!(out,"\", align 1\n@bagaev_probe_binding_length = constant i64 {}, align 8\n",description.len())?;
    for op in ["sadd","ssub","smul"] {
        writeln!(out,"declare {{ i64, i1 }} @llvm.{op}.with.overflow.i64(i64, i64)")?;
    }
    out.write_str("declare void @llvm.memset.p0.i64(ptr nocapture writeonly, i8, i64, i1 immarg)\n")?;
    out.write_str("%List = type { ptr, i64, i64 }\n%Text = type { ptr, i64, i64 }\n%Option = type { i64, i64 }\n")?;
    out.write_str("%Record = type { ptr }\n%Variant = type { i64, ptr }\n%Records = type { ptr, i64 }\n%Cell = type { i64, ptr, i64, i64 }\n")?;
    out.write_str(include_str!("text_compare.ll"))?;
    out.write_str(include_str!("list_helpers.ll"))?;
    out.write_str(include_str!("record_cells_helpers.ll"))?;
    out.write_str(include_str!("json_view_helpers.ll"))?;
    for node in program.nodes(){if let NodeKind::JsonField{key,..}=node.kind(){write!(out,"@json_key{} = private constant [{} x i8] c\"",node.id(),key.len())?;for b in key.bytes(){write!(out,"\\{b:02X}")?;}out.write_str("\", align 1\n")?;}}
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
    write!(binding,",\"module_bytes\":{},\"schema\":\"bagaev-json-view8-llvm-module/1\"}}\n",bytes.len())?;
    Ok(Module{bytes,binding:binding.value.into_bytes(),identity})
}

pub fn emit_program(program: &CheckedProgram) -> Result<Module> {
    emit(program,MODULE_LIMIT,BINDING_LIMIT)
}

#[cfg(test)]
pub(crate) fn emit_with_limits(program: &CheckedProgram, module: usize, binding: usize) -> Result<Module> {
    emit(program,module,binding)
}
