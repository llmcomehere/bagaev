//! Experimental inferred-scalar source. Separate from the frozen kernel checker.
//! Reuses its transport and IR data shapes; no filesystem, execution or admission.
use std::collections::BTreeMap;
use crate::canonical;
use crate::ir::{BinaryOp, Function, Local, Node, NodeId, NodeKind, Parameter, Type};
use crate::sha256;
use crate::transport::{self, Document, JsonString, TransportError, Value, ValueId};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Reason { Json, Version, Shape, Bounds, Reference, Cycle, Type }
impl Reason {
    pub fn name(self) -> &'static str {
        match self {
            Self::Json=>"TS_JSON",Self::Version=>"TS_VERSION",Self::Shape=>"TS_SHAPE",
            Self::Bounds=>"TS_BOUNDS",Self::Reference=>"TS_REFERENCE",Self::Cycle=>"TS_CYCLE",
            Self::Type=>"TS_TYPE",
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
struct CheckedSource {
    functions: Vec<Function>, nodes: Vec<Node>, entry: usize,
    canonical: Vec<u8>, identity: String,
}
impl CheckedSource {
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
        "Int64"=>Ok(Type::Int64),"Bool"=>Ok(Type::Bool),_=>fail(Reason::Shape,path),
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
            "int"|"bool"|"arg"|"use"|"not"=>Some(2),
            "add"|"sub"|"mul"|"eq"|"lt"|"le"=>Some(3),
            "if"=>Some(4),"let"=>Some(4),"loop"=>Some(6),
            "call" if items.len()>=2=>None,
            _=>return fail(Reason::Shape,&path),
        };
        if arity.is_some_and(|n|items.len()!=n) { return fail(Reason::Shape,&path); }
        let id=(self.nodes.len()+1) as NodeId;
        self.nodes.push(RawNode {function,pointer:path.clone(),ty:None,kind:RawKind::Ready(NodeKind::Int(0))});
        let mut result_type=None;
        let kind=match op.as_str() {
            "int"=>{
                let n=integer(doc,items[1],&index(&path,1))?;
                result_type=Some(Type::Int64); RawKind::Ready(NodeKind::Int(n))
            }
            "bool"=>{
                let b=match &doc.values[items[1]] { Value::Bool(b)=>*b,_=>return fail(Reason::Shape,&index(&path,1)) };
                result_type=Some(Type::Bool); RawKind::Ready(NodeKind::Bool(b))
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
            NodeKind::Binary{op,left,right}=>match op {
                BinaryOp::Eq=>{ let left_type=self.infer(left)?; self.require(right,left_type)?; Type::Bool }
                BinaryOp::Add|BinaryOp::Sub|BinaryOp::Mul=>{ self.require(left,Type::Int64)?;self.require(right,Type::Int64)?;Type::Int64 }
                BinaryOp::Lt|BinaryOp::Le=>{ self.require(left,Type::Int64)?;self.require(right,Type::Int64)?;Type::Bool }
            },
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
    schema(doc,envelope,"bagaev-typed-scalar/1","")?;
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

fn check_source_bytes(bytes: &[u8]) -> Result<CheckedSource,FrontendError> {
    let doc=parsed(bytes)?; program(&doc,doc.root)
}


fn value_at(doc:&Document,pointer:&str)->Result<ValueId,&'static str> {
    let mut at=doc.root;
    for part in pointer.split('/').skip(1) {
        let key=part.replace("~1","/").replace("~0","~");
        at=match &doc.values[at] {
            Value::Object(map)=>*map.get(&JsonString::from_str(&key)).ok_or("origin key")?,
            Value::Array(items)=>*items.get(key.parse::<usize>().map_err(|_|"origin index")?).ok_or("origin index")?,
            _=>return Err("origin container"),
        };
    }
    Ok(at)
}
fn lowered_pointers(source:&CheckedSource)->Result<Vec<String>,&'static str> {
    let mut pointers=vec![String::new();source.nodes.len()];
    fn visit(source:&CheckedSource,id:NodeId,path:String,out:&mut [String])->Result<(),&'static str> {
        let node=source.node(id).ok_or("origin node")?;
        if !out[usize::from(id)-1].is_empty(){return Err("duplicate origin");}
        out[usize::from(id)-1]=path.clone();
        let indices:Vec<usize>=match node.kind() {
            NodeKind::Let{..}=>vec![3,4],NodeKind::Loop{..}=>vec![5,6],
            NodeKind::Call{arguments,..}=>(2..2+arguments.len()).collect(),
            NodeKind::If{..}=>vec![1,2,3],NodeKind::Binary{..}=>vec![1,2],
            NodeKind::Not{..}=>vec![1],_=>vec![],
        };
        let children=node.kind().children();if children.len()!=indices.len(){return Err("origin arity");}
        for (child,index) in children.into_iter().zip(indices){visit(source,child,format!("{path}/{index}"),out)?;}
        Ok(())
    }
    for f in &source.functions {visit(source,f.body,format!("/functions/{}/body",f.name),&mut pointers)?;}
    if pointers.iter().any(String::is_empty){return Err("missing origin");}Ok(pointers)
}
fn lower(source:&CheckedSource)->Result<(crate::check::CheckedProgram,Vec<String>),&'static str> {
    let mut doc=transport::parse(source.canonical_bytes()).map_err(|_|"canonical source transport")?;
    // Resolve every source location before inserting any metadata. Flat arena
    // value IDs stay stable even when parent-array positions shift.
    let mut insertions=Vec::new();
    for node in &source.nodes {
        let data=match node.kind() {
            NodeKind::Let{declared,..}=>Some((2,*declared)),
            NodeKind::Loop{declared,..}=>Some((4,*declared)),_=>None,
        };
        if let Some((index,ty))=data {insertions.push((value_at(&doc,node.pointer())?,index,ty));}
    }
    let schema_id=value_at(&doc,"/schema")?;
    doc.values[schema_id]=Value::String(JsonString::from_str("bagaev-probe-ir/1"));
    for (at,index,ty) in insertions {
        let id=doc.values.len();doc.values.push(Value::String(JsonString::from_str(ty.name())));
        match &mut doc.values[at] {Value::Array(items)=>items.insert(index,id),_=>return Err("binder origin")}
    }
    let bytes=canonical::program_bytes(&doc,doc.root)?;
    let checked=crate::check::check_program_bytes(&bytes).map_err(|_|"lowered kernel rejected")?;
    let pointers=lowered_pointers(source)?;
    if checked.entry()!=source.entry || checked.nodes().len()!=source.nodes.len(){return Err("lowered occurrence count");}
    for (node,pointer) in checked.nodes().iter().zip(&pointers) {
        if node.pointer()!=pointer {return Err("lowered occurrence mapping");}
        let original=&source.nodes[usize::from(node.id())-1];
        if node.ty()!=original.ty() || node.kind().name()!=original.kind().name(){return Err("lowered occurrence type");}
    }
    Ok((checked,pointers))
}
/// Complete detached canonical result plus LF. Never executes the lowered code.
/// Allocation or internal lowering failures are environment errors, not refusals.
pub fn process(bytes:&[u8])->Result<Vec<u8>,&'static str> {
    use std::fmt::Write;
    let source=match check_source_bytes(bytes) {
        Ok(source)=>source,
        Err(FrontendError::Environment(message))=>return Err(message),
        Err(FrontendError::Refusal(error))=>{
            let mut out=String::from("{\"code\":");canonical::quote(error.reason().name(),&mut out);
            out.push_str(",\"execution_admission\":false,\"kind\":\"refusal\",\"schema\":\"bagaev-typed-source-result/1\",\"source_location\":");
            canonical::quote(error.location(),&mut out);out.push_str("}\n");
            if out.len()>8*1024*1024 {return Err("typed source output bound");}
            return Ok(out.into_bytes());
        }
    };
    let (lowered,pointers)=lower(&source)?;
    let mut out=String::from("{\"execution_admission\":false,\"kind\":\"draft\",\"lowered\":");
    out.push_str(std::str::from_utf8(lowered.canonical_bytes()).map_err(|_|"lowered UTF-8")?);
    out.push_str(",\"lowered_pin\":");canonical::quote(lowered.identity(),&mut out);
    out.push_str(",\"origins\":[");
    for (i,(node,pointer)) in source.nodes.iter().zip(pointers).enumerate() {
        if i>0 {out.push(',');}write!(&mut out,"{{\"id\":{},\"lowered\":",node.id()).map_err(|_|"origin formatting")?;
        canonical::quote(&pointer,&mut out);out.push_str(",\"source\":");canonical::quote(node.pointer(),&mut out);out.push('}');
    }
    out.push_str("],\"schema\":\"bagaev-typed-source-result/1\",\"source_pin\":");
    canonical::quote(source.identity(),&mut out);out.push_str("}\n");
    if out.len()>8*1024*1024 {return Err("typed source output bound");}Ok(out.into_bytes())
}

fn location_refusal(code:&str)->Vec<u8> {
    format!("{{\"code\":\"{code}\",\"execution_admission\":false,\"kind\":\"refused\",\"schema\":\"bagaev-typed-source-location/1\"}}\n").into_bytes()
}

/// Detached LLVM text and its complete binding record. No compiler invocation,
/// file publication, code loading or execution authority is supplied here.
pub fn emit_llvm_source(bytes:&[u8])->Result<Vec<u8>,&'static str> {
    let source=match check_source_bytes(bytes) {
        Ok(source)=>source,
        // Preserve the existing exact source-refusal wire and its bound.
        Err(FrontendError::Refusal(_))=>return process(bytes),
        Err(FrontendError::Environment(message))=>return Err(message),
    };
    let (lowered,_)=lower(&source)?;
    let module=crate::llvm::emit_program(&lowered).map_err(|_|"LLVM emission failed")?;
    let text=std::str::from_utf8(module.bytes()).map_err(|_|"LLVM UTF-8")?;
    let record=std::str::from_utf8(module.binding_bytes()).map_err(|_|"LLVM record UTF-8")?;
    let record=record.strip_suffix('\n').ok_or("LLVM record terminator")?;
    let mut out=String::from("{\"execution_admission\":false,\"kind\":\"module\",\"llvm_ir\":");
    canonical::quote(text,&mut out);
    out.push_str(",\"lowered_pin\":");canonical::quote(lowered.identity(),&mut out);
    out.push_str(",\"module_record\":");out.push_str(record);
    out.push_str(",\"schema\":\"bagaev-typed-llvm-module/1\",\"source_pin\":");
    canonical::quote(source.identity(),&mut out);out.push_str("}\n");
    if out.len()>64*1024*1024 {return Err("typed LLVM output bound");}
    Ok(out.into_bytes())
}
/// Rechecked expression location lookup, not authentication of a native result.
/// Source, expected lowered pin, then node bounds are checked in that order.
pub fn project_node(bytes:&[u8],expected_lowered_pin:&str,node:u16)->Result<Vec<u8>,&'static str> {
    use std::fmt::Write;
    let source=match check_source_bytes(bytes) {
        Ok(source)=>source,
        Err(FrontendError::Refusal(_))=>return Ok(location_refusal("TS_LOCATION_SOURCE")),
        Err(FrontendError::Environment(message))=>return Err(message),
    };
    let (lowered,pointers)=lower(&source)?;
    if lowered.identity()!=expected_lowered_pin {return Ok(location_refusal("TS_LOCATION_PIN"));}
    let index=match node.checked_sub(1).map(usize::from) {
        Some(index) if index<source.nodes.len()=>index,
        _=>return Ok(location_refusal("TS_LOCATION_NODE")),
    };
    let mut out=String::from("{\"execution_admission\":false,\"kind\":\"mapped\",\"lowered_location\":");
    canonical::quote(&pointers[index],&mut out);out.push_str(",\"lowered_pin\":");
    canonical::quote(lowered.identity(),&mut out);write!(&mut out,",\"node\":{node},\"schema\":\"bagaev-typed-source-location/1\",\"source_location\":").map_err(|_|"location formatting")?;
    canonical::quote(source.nodes[index].pointer(),&mut out);out.push_str(",\"source_pin\":");canonical::quote(source.identity(),&mut out);out.push_str("}\n");
    if out.len()>8*1024*1024 {return Err("typed location output bound");}Ok(out.into_bytes())
}
