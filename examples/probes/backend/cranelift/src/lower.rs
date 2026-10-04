//! Pure AOT object construction for the fixed, already checked probe IR.
//! No JIT, foreign execution, file writes, network or admission.
use crate::ir::{BinaryOp, CheckedProgram, NodeId, NodeKind, Type};
use cranelift_codegen::ir::{self, types::I64, types::I32, AbiParam, InstBuilder, MemFlagsData, Value, Block, FuncRef};
use cranelift_codegen::ir::condcodes::IntCC;
use cranelift_codegen::settings::{self, Configurable};
use cranelift_frontend::{FunctionBuilder, FunctionBuilderContext, Variable};
use cranelift_module::{Module, Linkage, FuncId, DataDescription};
use cranelift_object::{ObjectBuilder, ObjectModule};

pub const TARGET: &str = "x86_64-unknown-linux-gnu";
const OBJECT_LIMIT: usize = 8 * 1024 * 1024;
#[derive(Clone,Copy)]
pub enum Mode { None, Speed, Size }
impl Mode { pub fn name(self)-> &'static str { match self { Self::None=>"none", Self::Speed=>"speed", Self::Size=>"speed_and_size" } } }
type Result<T> = std::result::Result<T,String>;
fn signature(module:&ObjectModule,n:usize,returns:bool)->ir::Signature {
    let mut s=module.make_signature();
    for _ in 0..n {s.params.push(AbiParam::new(I64));}
    if returns {s.returns.push(AbiParam::new(I64));}
    s
}
fn zero_output(b:&mut FunctionBuilder,ctx:Value) {
    let zero=b.ins().iconst(I64,0);
    for offset in [0,8,16,24] {b.ins().store(MemFlagsData::new(),zero,ctx,offset);}
}
fn error_output(b:&mut FunctionBuilder,ctx:Value,status:i64,reason:i64,location:i64) {
    for (offset,n) in [(0,status),(24,reason),(28,location)] {
        let v=b.ins().iconst(I32,n);b.ins().store(MemFlagsData::new(),v,ctx,offset);
    }
}
struct Emitter<'a,'b,'c> {
    p:&'a CheckedProgram,b:&'b mut FunctionBuilder<'c>,index:usize,
    ctx:Value,args:Vec<Value>,vars:Vec<Variable>,calls:Vec<FuncRef>,failed:Block,
}
impl Emitter<'_,'_,'_> {
    fn guard(&mut self,bad:Value,status:i64,reason:i64,location:i64) {
        let fail=self.b.create_block();let good=self.b.create_block();
        self.b.ins().brif(bad,fail,&[],good,&[]);
        self.b.switch_to_block(fail);error_output(self.b,self.ctx,status,reason,location);
        self.b.ins().jump(self.failed,&[]);self.b.switch_to_block(good);
    }
    fn expr(&mut self,id:NodeId)->Result<Value> {
        let node=self.p.node(id).ok_or("missing checked node")?;
        if node.function()!=self.index {return Err("foreign checked node".into());}
        let kind=node.kind().clone();
        let work=self.b.ins().load(I64,MemFlagsData::new(),self.ctx,16);
        let full=self.b.ins().icmp_imm_s(IntCC::UnsignedGreaterThanOrEqual,work,65536);
        self.guard(full,2,10,id as i64);
        let next=self.b.ins().iadd_imm_s(work,1);self.b.ins().store(MemFlagsData::new(),next,self.ctx,16);
        Ok(match kind {
            NodeKind::Int(n)=>self.b.ins().iconst(I64,n),
            NodeKind::Bool(v)=>self.b.ins().iconst(I64,if v {1}else{0}),
            NodeKind::Arg{parameter}=>self.args[parameter],
            NodeKind::Use{slot}=>self.b.use_var(self.vars[slot]),
            NodeKind::Not{operand}=>{let v=self.expr(operand)?;self.b.ins().bxor_imm_s(v,1)},
            NodeKind::Let{slot,value,body,..}=>{
                let v=self.expr(value)?;self.b.def_var(self.vars[slot],v);self.expr(body)?
            },
            NodeKind::Binary{op,left,right}=>{
                let a=self.expr(left)?;let z=self.expr(right)?;
                match op {
                    BinaryOp::Add|BinaryOp::Sub|BinaryOp::Mul=>{
                        let (v,overflow)=match op {
                            BinaryOp::Add=>self.b.ins().sadd_overflow(a,z),
                            BinaryOp::Sub=>self.b.ins().ssub_overflow(a,z),
                            _=>self.b.ins().smul_overflow(a,z),
                        };
                        self.guard(overflow,1,9,id as i64);v
                    },
                    _=>{
                        let cc=match op {BinaryOp::Eq=>IntCC::Equal,BinaryOp::Lt=>IntCC::SignedLessThan,_=>IntCC::SignedLessThanOrEqual};
                        let v=self.b.ins().icmp(cc,a,z);self.b.ins().uextend(I64,v)
                    }
                }
            },
            NodeKind::If{condition,yes,no}=>{
                let c=self.expr(condition)?;let y=self.b.create_block();let n=self.b.create_block();let end=self.b.create_block();
                self.b.append_block_param(end,I64);self.b.ins().brif(c,y,&[],n,&[]);
                self.b.switch_to_block(y);let a=self.expr(yes)?;self.b.ins().jump(end,&[a.into()]);
                self.b.switch_to_block(n);let z=self.expr(no)?;self.b.ins().jump(end,&[z.into()]);
                self.b.switch_to_block(end);self.b.block_params(end)[0]
            },
            NodeKind::Call{function,arguments}=>{
                let mut values=vec![self.ctx];for id in arguments {values.push(self.expr(id)?);}
                let inst=self.b.ins().call(self.calls[function],&values);let v=self.b.inst_results(inst)[0];
                let status=self.b.ins().load(I32,MemFlagsData::new(),self.ctx,0);
                let bad=self.b.ins().icmp_imm_s(IntCC::NotEqual,status,0);let good=self.b.create_block();
                self.b.ins().brif(bad,self.failed,&[],good,&[]);self.b.switch_to_block(good);v
            },
            NodeKind::Loop{count,index_slot,accumulator_slot,initial,body,..}=>{
                let initial=self.expr(initial)?;let start=self.b.ins().iconst(I64,0);
                let head=self.b.create_block();let body_block=self.b.create_block();let end=self.b.create_block();
                self.b.append_block_param(head,I64);self.b.append_block_param(head,I64);self.b.append_block_param(end,I64);
                self.b.ins().jump(head,&[start.into(),initial.into()]);self.b.switch_to_block(head);
                let index=self.b.block_params(head)[0];let acc=self.b.block_params(head)[1];
                let more=self.b.ins().icmp_imm_s(IntCC::UnsignedLessThan,index,count as i64);
                self.b.ins().brif(more,body_block,&[],end,&[acc.into()]);self.b.switch_to_block(body_block);
                self.b.def_var(self.vars[index_slot],index);self.b.def_var(self.vars[accumulator_slot],acc);
                let value=self.expr(body)?;let next=self.b.ins().iadd_imm_s(index,1);
                self.b.ins().jump(head,&[next.into(),value.into()]);self.b.switch_to_block(end);self.b.block_params(end)[0]
            }
        })
    }
}
fn emit_function(module:&mut ObjectModule,p:&CheckedProgram,index:usize,ids:&[FuncId])->Result<()> {
    let f=&p.functions()[index];let mut ctx=module.make_context();ctx.func.signature=signature(module,1+f.parameters().len(),true);
    let refs=ids.iter().map(|&id|module.declare_func_in_func(id,&mut ctx.func)).collect();
    let mut bc=FunctionBuilderContext::new();
    {
        let mut b=FunctionBuilder::new(&mut ctx.func,&mut bc);let entry=b.create_block();let failed=b.create_block();
        b.append_block_params_for_function_params(entry);b.switch_to_block(entry);
        let args=b.block_params(entry).to_vec();let vars=f.locals().iter().map(|_|b.declare_var(I64)).collect();
        let mut e=Emitter{p,b:&mut b,index,ctx:args[0],args:args[1..].to_vec(),vars,calls:refs,failed};
        let result=e.expr(f.body())?;e.b.ins().return_(&[result]);e.b.switch_to_block(failed);
        let zero=e.b.ins().iconst(I64,0);e.b.ins().return_(&[zero]);
        b.seal_all_blocks();b.finalize(module.target_config());
    }
    module.define_function(ids[index],&mut ctx).map_err(|e|e.to_string())?;Ok(())
}
fn emit_entry(module:&mut ObjectModule,p:&CheckedProgram,ids:&[FuncId])->Result<()> {
    let sig=signature(module,2,false);let id=module.declare_function("bagaev_probe_entry",Linkage::Export,&sig).map_err(|e|e.to_string())?;
    let mut ctx=module.make_context();ctx.func.signature=sig;let call=module.declare_func_in_func(ids[p.entry()],&mut ctx.func);
    let f=&p.functions()[p.entry()];let mut bc=FunctionBuilderContext::new();
    {
        let mut b=FunctionBuilder::new(&mut ctx.func,&mut bc);let entry=b.create_block();b.append_block_params_for_function_params(entry);b.switch_to_block(entry);
        let input=b.block_params(entry)[0];let output=b.block_params(entry)[1];let mut args=Vec::new();
        for i in 0..8 {args.push(b.ins().load(I64,MemFlagsData::new(),input,i*8));}
        zero_output(&mut b,output);
        for (i,&value) in args.iter().enumerate() {
            let bad=match f.parameters().get(i).map(|p|p.ty()) {
                Some(Type::Int64)=>continue,
                Some(Type::Bool)=>b.ins().icmp_imm_s(IntCC::UnsignedGreaterThan,value,1),
                None=>b.ins().icmp_imm_s(IntCC::NotEqual,value,0),
            };
            let fail=b.create_block();let good=b.create_block();b.ins().brif(bad,fail,&[],good,&[]);
            b.switch_to_block(fail);error_output(&mut b,output,3,8,2147483649+i as i64);b.ins().return_(&[]);b.switch_to_block(good);
        }
        let mut values=vec![output];values.extend_from_slice(&args[..f.parameters().len()]);let inst=b.ins().call(call,&values);let result=b.inst_results(inst)[0];
        let status=b.ins().load(I32,MemFlagsData::new(),output,0);let ok=b.ins().icmp_imm_s(IntCC::Equal,status,0);
        let success=b.create_block();let end=b.create_block();b.ins().brif(ok,success,&[],end,&[]);b.switch_to_block(success);
        let ty=b.ins().iconst(I32,match f.result(){Type::Int64=>1,Type::Bool=>2});
        b.ins().store(MemFlagsData::new(),ty,output,4);b.ins().store(MemFlagsData::new(),result,output,8);b.ins().jump(end,&[]);
        b.switch_to_block(end);b.ins().return_(&[]);b.seal_all_blocks();b.finalize(module.target_config());
    }
    module.define_function(id,&mut ctx).map_err(|e|e.to_string())?;Ok(())
}
/// Returns an ELF object for the fixed x86-64 Linux ABI. Does not link or execute.
pub fn object(program:&CheckedProgram,mode:Mode)->Result<Vec<u8>> {
    let mut flags=settings::builder();flags.set("opt_level",mode.name()).map_err(|e|e.to_string())?;
    flags.set("is_pic","true").map_err(|e|e.to_string())?;
    let isa=cranelift_codegen::isa::lookup_by_name(TARGET).map_err(|e|e.to_string())?.finish(settings::Flags::new(flags)).map_err(|e|e.to_string())?;
    let mut module=ObjectModule::new(ObjectBuilder::new(isa,"bagaev-cranelift-probe",cranelift_module::default_libcall_names()).map_err(|e|e.to_string())?);
    let mut ids=Vec::new();for (i,f) in program.functions().iter().enumerate(){
        let sig=signature(&module,1+f.parameters().len(),true);ids.push(module.declare_function(&format!("probe_fn{i}"),Linkage::Local,&sig).map_err(|e|e.to_string())?);
    }
    for i in 0..ids.len(){emit_function(&mut module,program,i,&ids)?;}
    emit_entry(&mut module,program,&ids)?;
    let mut data=DataDescription::new();data.define(program.canonical_bytes().to_vec().into_boxed_slice());
    let symbol=module.declare_data("bagaev_probe_program",Linkage::Export,false,false).map_err(|e|e.to_string())?;
    module.define_data(symbol,&data).map_err(|e|e.to_string())?;
    let bytes=module.finish().emit().map_err(|e|e.to_string())?;
    if bytes.len()>OBJECT_LIMIT{return Err("object output bound".into());}Ok(bytes)
}
