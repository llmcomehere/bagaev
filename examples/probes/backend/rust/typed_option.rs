//! Experimental typed optional Int64 checker and reference evaluator; separate profile.
//! Reuses its transport and IR data shapes; no filesystem, execution or admission.
use std::collections::BTreeMap;
use crate::canonical;
use crate::option_ir::{BinaryOp, Function, Local, Node, NodeId, NodeKind, Parameter, Type};
use crate::sha256;
use crate::transport::{self, Document, JsonString, TransportError, Value, ValueId};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Reason { Json, Version, Shape, Bounds, Reference, Cycle, Type, Argument }
impl Reason {
    pub fn name(self) -> &'static str {
        match self {
            Self::Json=>"OI_JSON",Self::Version=>"OI_VERSION",Self::Shape=>"OI_SHAPE",
            Self::Bounds=>"OI_BOUNDS",Self::Reference=>"OI_REFERENCE",Self::Cycle=>"OI_CYCLE",
            Self::Type=>"OI_TYPE",Self::Argument=>"OI_ARGUMENT",
        }
    }
}
#[derive(Clone, Debug, Eq, PartialEq)]
struct Refusal { reason: Reason, location: String }
impl Refusal {
    pub fn reason(&self) -> Reason { self.reason }
    pub fn location(&self) -> &str { &self.location }
    fn new(reason: Reason, path: &str) -> Self { Self { reason, location: path.to_owned() } }
}
#[derive(Debug)]
enum FrontendError { Refusal(Refusal), Environment(&'static str) }
impl From<Refusal> for FrontendError { fn from(e: Refusal) -> Self { Self::Refusal(e) } }
type CheckResult<T> = Result<T, Refusal>;

/// Fields and construction stay private in this module. No deserialize/unchecked API.
#[derive(Debug)]
pub struct CheckedSource {
    functions: Vec<Function>, nodes: Vec<Node>, entry: usize,
    canonical: Vec<u8>, identity: String,
}
impl CheckedSource {
    pub fn functions(&self)->&[Function]{&self.functions}
    pub fn nodes(&self)->&[Node]{&self.nodes}
    pub fn entry(&self)->usize{self.entry}
    pub fn node(&self, id: NodeId) -> Option<&Node> { self.nodes.get(usize::from(id).checked_sub(1)?) }
    pub fn canonical_bytes(&self) -> &[u8] { &self.canonical }
    pub fn identity(&self) -> &str { &self.identity }
}
fn child(path: &str, key: &str) -> String {
    format!("{path}/{}",key.replace('~',"~0").replace('/',"~1"))
}
fn index(path: &str, n: usize) -> String { format!("{path}/{n}") }
fn fail<T>(reason: Reason, path: &str) -> CheckResult<T> { Err(Refusal::new(reason,path)) }
fn object<'a>(doc: &'a Document, id: ValueId, path: &str) -> CheckResult<&'a BTreeMap<JsonString,ValueId>> {
    match &doc.values[id] { Value::Object(map)=>Ok(map), _=>fail(Reason::Shape,path) }
}
fn exact<'a>(doc: &'a Document, id: ValueId, keys: &[&str], path: &str) -> CheckResult<&'a BTreeMap<JsonString,ValueId>> {
    let map = object(doc,id,path)?;
    if map.len()!=keys.len() || !keys.iter().all(|key|map.contains_key(&JsonString::from_str(key))) {
        return fail(Reason::Shape,path);
    }
    Ok(map)
}
fn field(map: &BTreeMap<JsonString,ValueId>, name: &str) -> ValueId {
    *map.get(&JsonString::from_str(name)).expect("field after exact envelope check")
}
fn array<'a>(doc: &'a Document, id: ValueId, path: &str) -> CheckResult<&'a [ValueId]> {
    match &doc.values[id] { Value::Array(items)=>Ok(items), _=>fail(Reason::Shape,path) }
}
fn string(doc: &Document, id: ValueId, path: &str) -> CheckResult<String> {
    match &doc.values[id] {
        Value::String(text)=>text.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,path)),
        _=>fail(Reason::Shape,path),
    }
}
fn identifier(doc: &Document, id: ValueId, path: &str) -> CheckResult<String> {
    let name=string(doc,id,path)?;
    if valid_id(&name) { Ok(name) } else { fail(Reason::Shape,path) }
}
fn valid_id(name: &str) -> bool {
    let bytes=name.as_bytes();
    (1..=64).contains(&bytes.len()) && bytes[0].is_ascii_alphabetic()
        && bytes[1..].iter().all(|b|b.is_ascii_alphanumeric() || matches!(*b,b'.'|b'_'|b'-'))
}
fn ty(doc: &Document, id: ValueId, path: &str) -> CheckResult<Type> {
    match string(doc,id,path)?.as_str() {
        "Int64"=>Ok(Type::Int64),"Bool"=>Ok(Type::Bool),"Text"=>Ok(Type::Text),"OptionInt64"=>Ok(Type::OptionInt64),_=>fail(Reason::Shape,path),
    }
}
fn integer(doc: &Document, id: ValueId, path: &str) -> CheckResult<i64> {
    match &doc.values[id] {
        Value::Integer(token)=>token.parse().map_err(|_|Refusal::new(Reason::Bounds,path)),
        _=>fail(Reason::Shape,path),
    }
}
fn schema(doc: &Document, map: &BTreeMap<JsonString,ValueId>, expected: &str, path: &str) -> CheckResult<()> {
    let path=child(path,"schema");
    if string(doc,field(map,"schema"),&path)? != expected { return fail(Reason::Version,&path); }
    Ok(())
}

/// Bounds walk is iterative and does not inspect semantic shapes or tags.
fn json_bounds(doc: &Document, root: ValueId, max_depth: usize, max_values: usize, prefix: &str) -> CheckResult<()> {
    let mut stack=vec![(root,1usize,prefix.to_owned())];
    let mut count=0;
    while let Some((id,depth,path))=stack.pop() {
        count+=1;
        if depth>max_depth || count>max_values { return fail(Reason::Bounds,&path); }
        match &doc.values[id] {
            Value::Array(items)=>for (i,&value) in items.iter().enumerate().rev() {
                stack.push((value,depth+1,index(&path,i)));
            },
            Value::Object(items)=>for (key,&value) in items.iter().rev() {
                // A non-scalar key has only a containing-object semantic location.
                // It is still traversed here, never prematurely refused as shape.
                let next=key.scalar_string().map(|key|child(&path,&key)).unwrap_or_else(||path.clone());
                stack.push((value,depth+1,next));
            },
            _=>{},
        }
    }
    Ok(())
}

#[derive(Clone, Copy)]
struct Binding { slot: usize, ty: Type, parameter: bool }
type Scope = BTreeMap<String,Binding>;
enum RawKind {
    Ready(NodeKind),
    Arg(Option<Binding>), Use(Option<Binding>),
    Call { name: String, arguments: Vec<NodeId> },
}
struct RawNode { function: usize, pointer: String, ty: Option<Type>, kind: RawKind }
struct Builder { functions: Vec<Function>, nodes: Vec<RawNode> }

impl Builder {
    fn local(&mut self, function: usize, name: String, ty: Type) -> Binding {
        let slot=self.functions[function].locals.len();
        self.functions[function].locals.push(Local {name,ty});
        Binding {slot,ty,parameter:false}
    }
    fn fresh(doc: &Document, value: ValueId, path: &str, scope: &Scope) -> CheckResult<String> {
        let name=identifier(doc,value,path)?;
        if scope.contains_key(&name) { return fail(Reason::Shape,path); }
        Ok(name)
    }
    /// Recursion can reach at most 33 calls: check before descent, limit 32.
    /// Parser nesting is unrelated and never consumes this call stack.
    fn expression(&mut self, doc: &Document, value: ValueId, path: String,
                  depth: usize, function: usize, scope: &Scope) -> CheckResult<NodeId> {
        if depth>32 || self.nodes.len()==512 { return fail(Reason::Bounds,&path); }
        let items=array(doc,value,&path)?;
        if items.is_empty() { return fail(Reason::Shape,&path); }
        // Non-string op is an expression-shape failure. A surrogate string is
        // the offending scalar, not malformed JSON or an invented op spelling.
        let op=match &doc.values[items[0]] {
            Value::String(s)=>s.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,&index(&path,0)))?,
            _=>return fail(Reason::Shape,&path),
        };
        let arity=match op.as_str() {
            "none.int"=>Some(1),"some.int"|"option.is_some"=>Some(2),"option.or"=>Some(3),
            "int"|"bool"|"arg"|"use"|"not"|"text"|"text.bytes"|"text.scalars"=>Some(2),
            "add"|"sub"|"mul"|"eq"|"lt"|"le"|"text.eq"|"text.lt"=>Some(3),
            "if"=>Some(4),"let"=>Some(4),"loop"=>Some(6),
            "call" if items.len()>=2=>None,
            _=>return fail(Reason::Shape,&path),
        };
        if arity.is_some_and(|n|items.len()!=n) { return fail(Reason::Shape,&path); }
        let id=(self.nodes.len()+1) as NodeId;
        self.nodes.push(RawNode {function,pointer:path.clone(),ty:None,kind:RawKind::Ready(NodeKind::Int(0))});
        let mut result_type=None;
        let kind=match op.as_str() {
            "none.int"=>{result_type=Some(Type::OptionInt64);RawKind::Ready(NodeKind::OptionNone)}
            "some.int"|"option.is_some"=>{let operand=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;RawKind::Ready(if op=="some.int"{NodeKind::OptionSome{operand}}else{NodeKind::OptionHas{operand}})}
            "option.or"=>{let option=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;let fallback=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;RawKind::Ready(NodeKind::OptionOr{option,fallback})}

            "int"=>{
                let n=integer(doc,items[1],&index(&path,1))?;
                result_type=Some(Type::Int64); RawKind::Ready(NodeKind::Int(n))
            }
            "bool"=>{
                let b=match &doc.values[items[1]] { Value::Bool(b)=>*b,_=>return fail(Reason::Shape,&index(&path,1)) };
                result_type=Some(Type::Bool); RawKind::Ready(NodeKind::Bool(b))
            }
            "text"=>{
                let text=string(doc,items[1],&index(&path,1))?;
                if text.len()>1024 || text.chars().count()>256 {return fail(Reason::Bounds,&index(&path,1));}
                result_type=Some(Type::Text);RawKind::Ready(NodeKind::Text(text))
            }
            "text.eq"|"text.lt"=>{
                let left=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;
                let right=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;
                RawKind::Ready(NodeKind::TextBinary{equal:op=="text.eq",left,right})
            }
            "text.bytes"|"text.scalars"=>{
                let operand=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;
                RawKind::Ready(NodeKind::TextLength{scalars:op=="text.scalars",operand})
            }
            "arg"|"use"=>{
                let name=identifier(doc,items[1],&index(&path,1))?;
                let binding=scope.get(&name).copied().filter(|b|b.parameter==(op=="arg"));
                if op=="arg" { RawKind::Arg(binding) } else { RawKind::Use(binding) }
            }
            "add"|"sub"|"mul"|"eq"|"lt"|"le"=>{
                let left=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;
                let right=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;
                let op=match op.as_str() {"add"=>BinaryOp::Add,"sub"=>BinaryOp::Sub,"mul"=>BinaryOp::Mul,
                    "eq"=>BinaryOp::Eq,"lt"=>BinaryOp::Lt,_=>BinaryOp::Le};
                RawKind::Ready(NodeKind::Binary{op,left,right})
            }
            "not"=>{
                let operand=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;
                RawKind::Ready(NodeKind::Not{operand})
            }
            "if"=>{
                let condition=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;
                let yes=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;
                let no=self.expression(doc,items[3],index(&path,3),depth+1,function,scope)?;
                RawKind::Ready(NodeKind::If{condition,yes,no})
            }
            "let"=>{
                let name=Self::fresh(doc,items[1],&index(&path,1),scope)?;
                // Private structural placeholder. Types are assigned only in infer.
                let declared=Type::Int64;
                let binding=self.local(function,name.clone(),declared);
                let initial=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;
                let mut body_scope=scope.clone(); body_scope.insert(name,binding);
                let body=self.expression(doc,items[3],index(&path,3),depth+1,function,&body_scope)?;
                RawKind::Ready(NodeKind::Let{slot:binding.slot,declared,value:initial,body})
            }
            "call"=>{
                let name=identifier(doc,items[1],&index(&path,1))?;
                let mut arguments=Vec::new();
                for (i,&argument) in items.iter().enumerate().skip(2) {
                    arguments.push(self.expression(doc,argument,index(&path,i),depth+1,function,scope)?);
                }
                RawKind::Call{name,arguments}
            }
            "loop"=>{
                let count=integer(doc,items[1],&index(&path,1))?;
                if !(0..=1024).contains(&count) { return fail(Reason::Bounds,&index(&path,1)); }
                let index_name=Self::fresh(doc,items[2],&index(&path,2),scope)?;
                let accumulator_name=Self::fresh(doc,items[3],&index(&path,3),scope)?;
                if index_name==accumulator_name { return fail(Reason::Shape,&index(&path,3)); }
                let declared=Type::Int64; // private structural placeholder
                let index_binding=self.local(function,index_name.clone(),Type::Int64);
                let accumulator=self.local(function,accumulator_name.clone(),declared);
                let initial=self.expression(doc,items[4],index(&path,4),depth+1,function,scope)?;
                let mut body_scope=scope.clone(); body_scope.insert(index_name,index_binding);
                body_scope.insert(accumulator_name,accumulator);
                let body=self.expression(doc,items[5],index(&path,5),depth+1,function,&body_scope)?;
                RawKind::Ready(NodeKind::Loop{count:count as u16,index_slot:index_binding.slot,
                    accumulator_slot:accumulator.slot,declared,initial,body})
            }
            _=>unreachable!("operation checked before metadata"),
        };
        let node=&mut self.nodes[usize::from(id)-1]; node.kind=kind; node.ty=result_type;
        Ok(id)
    }

    fn references(&mut self, entry_name: &str) -> CheckResult<usize> {
        let names:BTreeMap<String,usize>=self.functions.iter().enumerate().map(|(i,f)|(f.name.clone(),i)).collect();
        let entry=*names.get(entry_name).ok_or_else(||Refusal::new(Reason::Reference,"/entry"))?;
        for node in &mut self.nodes {
            let replacement=match &node.kind {
                RawKind::Arg(binding)=>{
                    let b=binding.ok_or_else(||Refusal::new(Reason::Reference,&node.pointer))?;
                    node.ty=Some(b.ty); Some(NodeKind::Arg{parameter:b.slot})
                }
                RawKind::Use(binding)=>{
                    let b=binding.ok_or_else(||Refusal::new(Reason::Reference,&node.pointer))?;
                    Some(NodeKind::Use{slot:b.slot})
                }
                RawKind::Call{name,arguments}=>{
                    let function=*names.get(name).ok_or_else(||Refusal::new(Reason::Reference,&node.pointer))?;
                    if arguments.len()!=self.functions[function].parameters.len() { return fail(Reason::Reference,&node.pointer); }
                    Some(NodeKind::Call{function,arguments:arguments.clone()})
                }
                _=>None,
            };
            if let Some(kind)=replacement { node.kind=RawKind::Ready(kind); }
        }
        Ok(entry)
    }

    fn cycles(&mut self) -> CheckResult<()> {
        // First occurrence per direct edge, then sorted callee indices/ASCII IDs.
        let mut edges=vec![BTreeMap::<usize,usize>::new();self.functions.len()];
        for (i,node) in self.nodes.iter().enumerate() {
            if let RawKind::Ready(NodeKind::Call{function,..})=&node.kind {
                edges[node.function].entry(*function).or_insert(i);
            }
        }
        fn visit(function:usize,edges:&[BTreeMap<usize,usize>],colours:&mut [u8],nodes:&[RawNode]) -> CheckResult<()> {
            colours[function]=1;
            for (&callee,&occurrence) in &edges[function] {
                if colours[callee]==1 { return fail(Reason::Cycle,&nodes[occurrence].pointer); }
                if colours[callee]==0 { visit(callee,edges,colours,nodes)?; }
            }
            colours[function]=2; Ok(())
        }
        let mut colours=vec![0;self.functions.len()];
        for i in 0..self.functions.len() { if colours[i]==0 { visit(i,&edges,&mut colours,&self.nodes)?; } }
        for (function,edge) in self.functions.iter_mut().zip(edges) { function.callees=edge.into_keys().collect(); }
        Ok(())
    }

    fn require(&mut self, id: NodeId, expected: Type) -> CheckResult<()> {
        if self.infer(id)? != expected { return fail(Reason::Type,&self.nodes[usize::from(id)-1].pointer); }
        Ok(())
    }
    fn infer(&mut self, id: NodeId) -> CheckResult<Type> {
        let n=usize::from(id)-1;
        if let Some(ty)=self.nodes[n].ty { return Ok(ty); }
        let kind=match &self.nodes[n].kind { RawKind::Ready(kind)=>kind.clone(),_=>unreachable!("references precede types") };
        let ty=match kind {
            NodeKind::OptionSome{operand}=>{if self.infer(operand)?!=Type::Int64{return fail(Reason::Type,&self.nodes[n].pointer);}Type::OptionInt64}
            NodeKind::OptionHas{operand}=>{if self.infer(operand)?!=Type::OptionInt64{return fail(Reason::Type,&self.nodes[n].pointer);}Type::Bool}
            NodeKind::OptionOr{option,fallback}=>{if self.infer(option)?!=Type::OptionInt64{return fail(Reason::Type,&self.nodes[n].pointer);}if self.infer(fallback)?!=Type::Int64{return fail(Reason::Type,&self.nodes[n].pointer);}Type::Int64}

            NodeKind::Binary{op,left,right}=>match op {
                BinaryOp::Eq=>{ let left_type=self.infer(left)?; if !matches!(left_type,Type::Int64|Type::Bool){return fail(Reason::Type,&self.nodes[usize::from(left)-1].pointer);} self.require(right,left_type)?; Type::Bool }
                BinaryOp::Add|BinaryOp::Sub|BinaryOp::Mul=>{ self.require(left,Type::Int64)?;self.require(right,Type::Int64)?;Type::Int64 }
                BinaryOp::Lt|BinaryOp::Le=>{ self.require(left,Type::Int64)?;self.require(right,Type::Int64)?;Type::Bool }
            },
            NodeKind::TextBinary{left,right,..}=>{self.require(left,Type::Text)?;self.require(right,Type::Text)?;Type::Bool}
            NodeKind::TextLength{operand,..}=>{self.require(operand,Type::Text)?;Type::Int64}
            NodeKind::Not{operand}=>{self.require(operand,Type::Bool)?;Type::Bool}
            NodeKind::Let{slot,value,body,..}=>{
                let declared=self.infer(value)?;let f=self.nodes[n].function;
                self.functions[f].locals[slot].ty=declared;
                self.nodes[n].kind=RawKind::Ready(NodeKind::Let{slot,declared,value,body});
                self.infer(body)?
            }
            NodeKind::If{condition,yes,no}=>{self.require(condition,Type::Bool)?;let yes_type=self.infer(yes)?;self.require(no,yes_type)?;yes_type}
            NodeKind::Call{function,arguments}=>{
                for (i,argument) in arguments.into_iter().enumerate() {
                    let expected=self.functions[function].parameters[i].ty;
                    self.require(argument,expected)?;
                }
                self.functions[function].result
            }
            NodeKind::Loop{count,index_slot,accumulator_slot,initial,body,..}=>{
                let declared=self.infer(initial)?;let f=self.nodes[n].function;
                self.functions[f].locals[accumulator_slot].ty=declared;
                self.nodes[n].kind=RawKind::Ready(NodeKind::Loop{count,index_slot,accumulator_slot,declared,initial,body});
                self.require(body,declared)?;declared
            }
            NodeKind::Use{slot}=>self.functions[self.nodes[n].function].locals[slot].ty,
            _=>unreachable!("leaf types set during structure/reference checking"),
        };
        self.nodes[n].ty=Some(ty); Ok(ty)
    }
    fn types(&mut self) -> CheckResult<()> {
        for i in 0..self.functions.len() {
            let body=self.functions[i].body; let result=self.functions[i].result;
            self.require(body,result)?;
        }
        Ok(())
    }
}

fn program(doc: &Document, root: ValueId) -> Result<CheckedSource,FrontendError> {
    let envelope=exact(doc,root,&["schema","entry","functions"],"")?;
    schema(doc,envelope,"bagaev-typed-option-int/1","")?;
    json_bounds(doc,root,128,8192,"")?;
    let entry_name=identifier(doc,field(envelope,"entry"),"/entry")?;
    let definitions=object(doc,field(envelope,"functions"),"/functions")?;
    if !(1..=8).contains(&definitions.len()) { return Err(Refusal::new(Reason::Bounds,"/functions").into()); }
    let mut names=Vec::new();
    for key in definitions.keys() {
        let name=key.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,"/functions"))?;
        if !valid_id(&name) { return Err(Refusal::new(Reason::Shape,"/functions").into()); }
        names.push(name);
    }
    let mut builder=Builder{functions:Vec::new(),nodes:Vec::new()};
    for (function,((_,&definition),name)) in definitions.iter().zip(names).enumerate() {
        let path=child("/functions",&name);
        let definition=exact(doc,definition,&["params","result","body"],&path)?;
        let params_path=child(&path,"params");
        let params=array(doc,field(definition,"params"),&params_path)?;
        if params.len()>8 { return Err(Refusal::new(Reason::Bounds,&params_path).into()); }
        let mut scope=Scope::new(); let mut parameters=Vec::new();
        for (i,&parameter) in params.iter().enumerate() {
            let pointer=index(&params_path,i); let pair=array(doc,parameter,&pointer)?;
            if pair.len()!=2 { return Err(Refusal::new(Reason::Shape,&pointer).into()); }
            let name=identifier(doc,pair[0],&index(&pointer,0))?;
            if scope.contains_key(&name) { return Err(Refusal::new(Reason::Shape,&index(&pointer,0)).into()); }
            let ty=ty(doc,pair[1],&index(&pointer,1))?;
            scope.insert(name.clone(),Binding{slot:i,ty,parameter:true});
            parameters.push(Parameter{name,ty});
        }
        let result=ty(doc,field(definition,"result"),&child(&path,"result"))?;
        builder.functions.push(Function{name,parameters,result,body:0,locals:Vec::new(),callees:Vec::new()});
        let body=builder.expression(doc,field(definition,"body"),child(&path,"body"),1,function,&scope)?;
        builder.functions[function].body=body;
    }
    let entry=builder.references(&entry_name)?;
    builder.cycles()?;
    builder.types()?;
    if !matches!(builder.functions[entry].result,Type::Int64|Type::Bool) {return Err(Refusal::new(Reason::Type,&format!("/functions/{}/result",builder.functions[entry].name)).into());}
    let canonical=canonical::program_bytes(doc,root).map_err(FrontendError::Environment)?;
    let identity=sha256::digest(&canonical);
    let nodes=builder.nodes.into_iter().enumerate().map(|(i,node)|{
        let kind=match node.kind {RawKind::Ready(kind)=>kind,_=>unreachable!("complete reference phase")};
        Node{id:(i+1) as NodeId,function:node.function,pointer:node.pointer,
             ty:node.ty.expect("complete type phase visits every expression"),kind}
    }).collect();
    Ok(CheckedSource{functions:builder.functions,nodes,entry,canonical,identity})
}

fn parsed(bytes: &[u8]) -> Result<Document,FrontendError> {
    transport::parse(bytes).map_err(|e|Refusal::new(match e {TransportError::Bounds=>Reason::Bounds,TransportError::Json=>Reason::Json},"").into())
}

#[derive(Clone,Copy)]
enum RuntimeValue<'a> { Int(i64), Bool(bool), Text(crate::text_value::Text<'a>), Optional(crate::option_int::OptionInt64) }
impl<'a> RuntimeValue<'a> {
    fn optional(self)->Result<crate::option_int::OptionInt64,EvalError>{match self{Self::Optional(v)=>Ok(v),_=>Err(EvalError::Environment("checked optional type"))}}
    fn int(self)->Result<i64,EvalError>{match self{Self::Int(x)=>Ok(x),_=>Err(EvalError::Environment("checked integer type"))}}
    fn boolean(self)->Result<bool,EvalError>{match self{Self::Bool(x)=>Ok(x),_=>Err(EvalError::Environment("checked boolean type"))}}
    fn text(self)->Result<crate::text_value::Text<'a>,EvalError>{match self{Self::Text(x)=>Ok(x),_=>Err(EvalError::Environment("checked text type"))}}
}
enum EvalError { Work(NodeId), Overflow(NodeId), Environment(&'static str) }
struct Runtime<'a> { program:&'a CheckedSource, work:u64 }
impl<'a> Runtime<'a> {
    fn charge(&mut self,n:u64,id:NodeId)->Result<(),EvalError>{
        if n>65536-self.work{return Err(EvalError::Work(id));}self.work+=n;Ok(())
    }
    fn function(&mut self,f:usize,args:&[RuntimeValue<'a>])->Result<RuntimeValue<'a>,EvalError>{
        let function=&self.program.functions[f];
        let mut locals=vec![None;function.locals.len()];
        self.expression(function.body,args,&mut locals)
    }
    fn expression(&mut self,id:NodeId,args:&[RuntimeValue<'a>],locals:&mut [Option<RuntimeValue<'a>>])->Result<RuntimeValue<'a>,EvalError>{
        self.charge(1,id)?;
        let program=self.program;let node=program.node(id).ok_or(EvalError::Environment("checked node"))?;
        match node.kind() {
            NodeKind::OptionNone=>Ok(RuntimeValue::Optional(crate::option_int::OptionInt64::none())),
            NodeKind::OptionSome{operand}=>Ok(RuntimeValue::Optional(crate::option_int::OptionInt64::some(self.expression(*operand,args,locals)?.int()?))),
            NodeKind::OptionHas{operand}=>Ok(RuntimeValue::Bool(self.expression(*operand,args,locals)?.optional()?.is_some())),
            NodeKind::OptionOr{option,fallback}=>{let v=self.expression(*option,args,locals)?.optional()?;match v.value(){Some(n)=>Ok(RuntimeValue::Int(n)),None=>self.expression(*fallback,args,locals)}},

            NodeKind::Int(x)=>Ok(RuntimeValue::Int(*x)),
            NodeKind::Bool(x)=>Ok(RuntimeValue::Bool(*x)),
            NodeKind::Text(x)=>{
                self.charge(x.len() as u64,id)?;
                Ok(RuntimeValue::Text(crate::text_value::Text::from_bytes(x.as_bytes()).map_err(|_|EvalError::Environment("checked text literal"))?))
            }
            NodeKind::Arg{parameter}=>args.get(*parameter).copied().ok_or(EvalError::Environment("checked argument")),
            NodeKind::Use{slot}=>locals.get(*slot).copied().flatten().ok_or(EvalError::Environment("checked local")),
            NodeKind::Not{operand}=>Ok(RuntimeValue::Bool(!self.expression(*operand,args,locals)?.boolean()?)),
            NodeKind::TextLength{scalars,operand}=>{
                let value=self.expression(*operand,args,locals)?.text()?;
                Ok(RuntimeValue::Int(if *scalars{value.scalar_len()}else{value.byte_len()} as i64))
            }
            NodeKind::TextBinary{equal,left,right}=>{
                let a=self.expression(*left,args,locals)?.text()?;
                let b=self.expression(*right,args,locals)?.text()?;
                self.charge((a.byte_len()+b.byte_len()) as u64,id)?;
                Ok(RuntimeValue::Bool(if *equal{a.equal(b)}else{a.compare(b)<0}))
            }
            NodeKind::Binary{op,left,right}=>{
                let a=self.expression(*left,args,locals)?;let b=self.expression(*right,args,locals)?;
                if *op==BinaryOp::Eq{return Ok(RuntimeValue::Bool(match (a,b){(RuntimeValue::Int(x),RuntimeValue::Int(y))=>x==y,(RuntimeValue::Bool(x),RuntimeValue::Bool(y))=>x==y,_=>return Err(EvalError::Environment("checked scalar equality"))}));}
                let a=a.int()?;let b=b.int()?;
                match op {
                    BinaryOp::Add=>a.checked_add(b).map(RuntimeValue::Int).ok_or(EvalError::Overflow(id)),
                    BinaryOp::Sub=>a.checked_sub(b).map(RuntimeValue::Int).ok_or(EvalError::Overflow(id)),
                    BinaryOp::Mul=>a.checked_mul(b).map(RuntimeValue::Int).ok_or(EvalError::Overflow(id)),
                    BinaryOp::Lt=>Ok(RuntimeValue::Bool(a<b)),BinaryOp::Le=>Ok(RuntimeValue::Bool(a<=b)),
                    BinaryOp::Eq=>unreachable!(),
                }
            }
            NodeKind::Let{slot,value,body,..}=>{
                let v=self.expression(*value,args,locals)?;locals[*slot]=Some(v);self.expression(*body,args,locals)
            }
            NodeKind::If{condition,yes,no}=>{
                let c=self.expression(*condition,args,locals)?.boolean()?;self.expression(if c{*yes}else{*no},args,locals)
            }
            NodeKind::Call{function,arguments}=>{
                let mut values=Vec::with_capacity(arguments.len());
                for child in arguments{values.push(self.expression(*child,args,locals)?);}
                self.function(*function,&values)
            }
            NodeKind::Loop{count,index_slot,accumulator_slot,initial,body,..}=>{
                let mut value=self.expression(*initial,args,locals)?;
                for i in 0..*count{locals[*index_slot]=Some(RuntimeValue::Int(i64::from(i)));locals[*accumulator_slot]=Some(value);value=self.expression(*body,args,locals)?;}
                Ok(value)
            }
        }
    }
}
fn result_wire(status:&str,reason:Option<&str>,location:Option<&str>,value:Option<RuntimeValue<'_>>,work:u64)->Result<Vec<u8>,&'static str>{
    use std::fmt::Write;
    let mut out=String::from("{\"location\":");
    match location{Some(x)=>canonical::quote(x,&mut out),None=>out.push_str("null")};out.push_str(",\"reason\":");
    match reason{Some(x)=>canonical::quote(x,&mut out),None=>out.push_str("null")};
    out.push_str(",\"schema\":\"bagaev-typed-option-int-result/1\",\"status\":");canonical::quote(status,&mut out);out.push_str(",\"value\":");
    let ty=match value{Some(RuntimeValue::Int(x))=>{write!(&mut out,"{x}").map_err(|_|"result formatting")?;Some("Int64")},Some(RuntimeValue::Bool(x))=>{out.push_str(if x{"true"}else{"false"});Some("Bool")},Some(RuntimeValue::Text(_))|Some(RuntimeValue::Optional(_))=>return Err("non-scalar entry result"),None=>{out.push_str("null");None}};
    out.push_str(",\"value_type\":");match ty{Some(x)=>canonical::quote(x,&mut out),None=>out.push_str("null")};write!(&mut out,",\"work\":{work}}}\n").map_err(|_|"result formatting")?;Ok(out.into_bytes())
}
enum OwnedArgument { Int(i64), Bool(bool), Text(String), Optional(crate::option_int::OptionInt64) }
fn checked_invocation(doc:&Document)->Result<(CheckedSource,Vec<OwnedArgument>),FrontendError>{
    let outer=exact(doc,doc.root,&["schema","program","arguments"],"")?;
    schema(doc,outer,"bagaev-typed-option-int-invocation/1","")?;
    json_bounds(doc,doc.root,132,16384,"")?;
    let checked=program(doc,field(outer,"program")).map_err(|e|match e{FrontendError::Refusal(mut r)=>{r.location=format!("/program{}",r.location);FrontendError::Refusal(r)},other=>other})?;
    let vals=match &doc.values[field(outer,"arguments")]{Value::Array(x)=>x,_=>return Err(Refusal::new(Reason::Argument,"/arguments").into())};
    let params=&checked.functions[checked.entry].parameters;
    if vals.len()!=params.len(){return Err(Refusal::new(Reason::Argument,"/arguments").into());}
    let mut args=Vec::new();
    for (i,(&v,p)) in vals.iter().zip(params).enumerate(){
        let bad=||Refusal::new(Reason::Argument,&format!("/arguments/{i}"));
        let value=match (p.ty,&doc.values[v]){
            (Type::OptionInt64,Value::Null)=>OwnedArgument::Optional(crate::option_int::OptionInt64::none()),
            (Type::OptionInt64,Value::Integer(s))=>OwnedArgument::Optional(crate::option_int::OptionInt64::some(s.parse().map_err(|_|bad())?)),

            (Type::Int64,Value::Integer(s))=>OwnedArgument::Int(s.parse().map_err(|_|bad())?),
            (Type::Bool,Value::Bool(x))=>OwnedArgument::Bool(*x),
            (Type::Text,Value::String(s))=>{let text=s.scalar_string().ok_or_else(bad)?;crate::text_value::Text::from_bytes(text.as_bytes()).map_err(|_|bad())?;OwnedArgument::Text(text)},
            _=>return Err(bad().into()),
        };args.push(value);
    }
    Ok((checked,args))
}
/// Complete bounded invocation, returning only detached scalar/error data.
/// This reference evaluator does not invoke compilers or generated native code.
pub fn process(bytes:&[u8])->Result<Vec<u8>,&'static str>{
    let checked=parsed(bytes).and_then(|doc|checked_invocation(&doc));
    let (program,owned)=match checked{Ok(x)=>x,Err(FrontendError::Environment(e))=>return Err(e),Err(FrontendError::Refusal(r))=>return result_wire("invalid-ir",Some(r.reason().name()),Some(r.location()),None,0)};
    let mut args=Vec::new();
    for a in &owned{args.push(match a{OwnedArgument::Optional(v)=>RuntimeValue::Optional(*v),OwnedArgument::Int(x)=>RuntimeValue::Int(*x),OwnedArgument::Bool(x)=>RuntimeValue::Bool(*x),OwnedArgument::Text(x)=>RuntimeValue::Text(crate::text_value::Text::from_bytes(x.as_bytes()).map_err(|_|"checked text argument")?)});}
    let mut runtime=Runtime{program:&program,work:0};
    match runtime.function(program.entry,&args){
        Ok(value)=>result_wire("success",None,None,Some(value),runtime.work),
        Err(EvalError::Environment(e))=>Err(e),
        Err(error)=>{let (id,status,reason)=match error{EvalError::Work(id)=>(id,"work-limit","OI_WORK"),EvalError::Overflow(id)=>(id,"integer-overflow","OI_OVERFLOW"),EvalError::Environment(_)=>unreachable!()};let loc=format!("/program{}",program.node(id).ok_or("runtime node")?.pointer());result_wire(status,Some(reason),Some(&loc),None,runtime.work)}
    }
}

pub fn checked_program(bytes:&[u8])->Result<CheckedSource,String>{let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;program(&doc,doc.root).map_err(|e|format!("{e:?}"))}

/// Checked source or stable source refusal data; neither variant admits execution.
pub enum SourceCheck { Checked(CheckedSource), Refused { reason: &'static str, location: String } }
pub fn check_source(bytes:&[u8])->Result<SourceCheck,&'static str>{
    match parsed(bytes).and_then(|doc|program(&doc,doc.root)) {
        Ok(p)=>Ok(SourceCheck::Checked(p)),
        Err(FrontendError::Refusal(r))=>Ok(SourceCheck::Refused{reason:r.reason().name(),location:r.location}),
        Err(FrontendError::Environment(e))=>Err(e),
    }
}
