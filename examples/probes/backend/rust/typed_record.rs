//! Experimental typed compound-value checker and reference evaluator; separate profile.
//! Reuses its transport and IR data shapes; no filesystem, execution or admission.
use std::collections::BTreeMap;
use crate::canonical;
use crate::record_ir::{BinaryOp, MatchCase, Function, Local, Node, NodeId, NodeKind, Parameter, Type};
use crate::sha256;
use crate::transport::{self, Document, JsonString, TransportError, Value, ValueId};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Reason { Json, Version, Shape, Bounds, Reference, Cycle, Type, Argument }
impl Reason {
    pub fn name(self) -> &'static str {
        match self {
            Self::Json=>"RR_JSON",Self::Version=>"RR_VERSION",Self::Shape=>"RR_SHAPE",
            Self::Bounds=>"RR_BOUNDS",Self::Reference=>"RR_REFERENCE",Self::Cycle=>"RR_CYCLE",
            Self::Type=>"RR_TYPE",Self::Argument=>"RR_ARGUMENT",
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
#[derive(Clone,Debug)]
pub struct RecordDefinition { name:String, fields:Vec<(String,Type)>, optional:Vec<String> }
#[derive(Clone,Debug)]
pub struct ListDefinition{name:String,element:usize,capacity:usize}
impl ListDefinition {pub fn element(&self)->usize{self.element} pub fn capacity(&self)->usize{self.capacity}}
#[derive(Clone,Debug)]
pub struct VariantDefinition{name:String,alternatives:Vec<(String,Type)>}
impl VariantDefinition {pub fn alternatives(&self)->&[(String,Type)]{&self.alternatives}}
#[derive(Debug)]
pub struct CheckedSource {
    profile:u8,
    variants:Vec<VariantDefinition>,
    lists:Vec<ListDefinition>,
    records:Vec<RecordDefinition>,
    functions: Vec<Function>, nodes: Vec<Node>, entry: usize,
    canonical: Vec<u8>, identity: String,
}
impl RecordDefinition {pub fn name(&self)->&str{&self.name} pub fn fields(&self)->&[(String,Type)]{&self.fields}}
impl CheckedSource {
    pub fn profile(&self)->u8{self.profile}
    pub fn variant_definitions(&self)->&[VariantDefinition]{&self.variants}
    pub fn record_definitions(&self)->&[RecordDefinition]{&self.records}
    pub fn list_definitions(&self)->&[ListDefinition]{&self.lists}
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
fn primitive_ty(doc: &Document, id: ValueId, path: &str) -> CheckResult<Type> {
    match string(doc,id,path)?.as_str() {
        "Int64"=>Ok(Type::Int64),"Bool"=>Ok(Type::Bool),"Text"=>Ok(Type::Text),"OptionInt64"=>Ok(Type::OptionInt64),"TextList"=>Ok(Type::TextList),_=>fail(Reason::Shape,path),
    }
}
fn valid_record_name(s:&str)->bool{let b=s.as_bytes();!b.is_empty()&&b.len()<=32&&b[0].is_ascii_alphabetic()&&b[1..].iter().all(|x|x.is_ascii_alphanumeric()||*x==b'_')}
fn record_name(doc:&Document,id:ValueId,path:&str)->CheckResult<String>{let s=string(doc,id,path)?;if valid_record_name(&s){Ok(s)}else{fail(Reason::Shape,path)}}
fn declared_ty(doc:&Document,id:ValueId,path:&str,records:&[RecordDefinition],lists:&[ListDefinition],variants:&[VariantDefinition],profile:u8)->CheckResult<Type>{let s=string(doc,id,path)?;if profile>=6&&s=="Json"{return Ok(Type::Json);}if let Some(i)=records.iter().position(|r|r.name==s){Ok(Type::Record(i as u8))}else if let Some(i)=lists.iter().position(|r|r.name==s){Ok(Type::RecordList(i as u8))}else if let Some(i)=variants.iter().position(|r|r.name==s){Ok(Type::Variant(i as u8))}else{primitive_ty(doc,id,path)}}
fn records(doc:&Document,id:ValueId)->CheckResult<Vec<RecordDefinition>>{
 let map=object(doc,id,"/records")?;if map.len()>8{return fail(Reason::Bounds,"/records");}let mut out=Vec::new();
 for (name,&value) in map{let name=name.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,"/records"))?;if !valid_record_name(&name)||matches!(name.as_str(),"Int64"|"Bool"|"Text"|"OptionInt64"|"TextList"){return fail(Reason::Shape,"/records");}let path=child("/records",&name);let fields=object(doc,value,&path)?;if fields.len()>8{return fail(Reason::Bounds,&path);}let mut entries=Vec::new();for (key,&value) in fields{let key=key.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,&path))?;if !valid_record_name(&key){return fail(Reason::Shape,&path);}let kind=primitive_ty(doc,value,&child(&path,&key))?;entries.push((key,kind));}out.push(RecordDefinition{name,fields:entries,optional:Vec::new()});}Ok(out)
}
fn nested_records(doc:&Document,id:ValueId)->CheckResult<Vec<RecordDefinition>>{
 let map=object(doc,id,"/records")?;if map.len()>8{return fail(Reason::Bounds,"/records");}let mut names=Vec::new();
 for key in map.keys(){let name=key.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,"/records"))?;if !valid_record_name(&name)||matches!(name.as_str(),"Int64"|"Bool"|"Text"|"OptionInt64"|"TextList"){return fail(Reason::Shape,"/records");}names.push(name);}
 let mut out=Vec::new();for ((_,&value),name)in map.iter().zip(names.iter()){
  let path=child("/records",name);let fields=object(doc,value,&path)?;if fields.len()>8{return fail(Reason::Bounds,&path);}let mut entries=Vec::new();for(key,&v)in fields{let key=key.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,&path))?;if !valid_record_name(&key){return fail(Reason::Shape,&path);}let at=child(&path,&key);let target=string(doc,v,&at)?;let kind=if let Some(i)=names.iter().position(|n|*n==target){Type::Record(i as u8)}else{primitive_ty(doc,v,&at)?};entries.push((key,kind));}out.push(RecordDefinition{name:name.clone(),fields:entries,optional:Vec::new()});
 }
 use crate::type_graph::{Ref,Definition};use crate::record_value::Kind;
 let refs:Vec<Vec<Ref>>=out.iter().map(|d|d.fields.iter().map(|(_,t)|match t{Type::RecordList(_)|Type::Variant(_)|Type::Json=>unreachable!("record-only declaration parser"),Type::Record(n)=>Ref::Named(*n),Type::Int64=>Ref::Primitive(Kind::Int64),Type::Bool=>Ref::Primitive(Kind::Bool),Type::Text=>Ref::Primitive(Kind::Text),Type::TextList=>Ref::Primitive(Kind::TextList),Type::OptionInt64=>Ref::Primitive(Kind::OptionInt64)}).collect()).collect();
 let defs:Vec<_>=refs.iter().map(|r|Definition::Product(r)).collect();if let Err(e)=crate::type_graph::check(&defs,Ref::Primitive(Kind::Int64)){let path=out.get(e.index).map(|r|child("/records",&r.name)).unwrap_or_else(||"/records".to_owned());return fail(if e.reason=="GRAPH_CYCLE"{Reason::Cycle}else{Reason::Bounds},&path);}Ok(out)
}
fn composite_records(doc:&Document,rid:ValueId,lid:ValueId)->CheckResult<(Vec<RecordDefinition>,Vec<ListDefinition>)>{
 let rm=object(doc,rid,"/records")?;let lm=object(doc,lid,"/lists")?;if rm.len()>8{return fail(Reason::Bounds,"/records");}if rm.len()+lm.len()>8{return fail(Reason::Bounds,"/lists");}
 let names=|map:&BTreeMap<JsonString,ValueId>,path:&str|->CheckResult<Vec<String>>{let mut out=Vec::new();for key in map.keys(){let s=key.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,path))?;if !valid_record_name(&s)||matches!(s.as_str(),"Int64"|"Bool"|"Text"|"OptionInt64"|"TextList"){return fail(Reason::Shape,path);}out.push(s);}Ok(out)};
 let rn=names(rm,"/records")?;let ln=names(lm,"/lists")?;if ln.iter().any(|n|rn.contains(n)){return fail(Reason::Shape,"/lists");}
 let mut records=Vec::new();for((_,&v),name)in rm.iter().zip(&rn){let path=child("/records",name);let fields=object(doc,v,&path)?;if fields.len()>8{return fail(Reason::Bounds,&path);}let mut entries=Vec::new();for(key,&v)in fields{let key=key.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,&path))?;if !valid_record_name(&key){return fail(Reason::Shape,&path);}let at=child(&path,&key);let target=string(doc,v,&at)?;let ty=if let Some(i)=rn.iter().position(|n|*n==target){Type::Record(i as u8)}else if let Some(i)=ln.iter().position(|n|*n==target){Type::RecordList(i as u8)}else{primitive_ty(doc,v,&at)?};entries.push((key,ty));}records.push(RecordDefinition{name:name.clone(),fields:entries,optional:Vec::new()});}
 let mut lists=Vec::new();for((_,&v),name)in lm.iter().zip(&ln){let path=child("/lists",name);let obj=exact(doc,v,&["element","capacity"],&path)?;let at=child(&path,"element");let target=string(doc,field(obj,"element"),&at)?;let element=rn.iter().position(|n|*n==target).ok_or_else(||Refusal::new(Reason::Reference,&at))?;let at=child(&path,"capacity");let capacity=integer(doc,field(obj,"capacity"),&at)?;if !(0..=4).contains(&capacity){return fail(Reason::Bounds,&at);}lists.push(ListDefinition{name:name.clone(),element,capacity:capacity as usize});}
 use crate::type_graph::{Ref,Definition};use crate::record_value::Kind;
 let refs:Vec<Vec<Ref>>=records.iter().map(|d|d.fields.iter().map(|(_,t)|match t{Type::Variant(_)|Type::Json=>unreachable!("record-list-only declarations"),Type::Record(n)=>Ref::Named(*n),Type::RecordList(n)=>Ref::Named((records.len()+usize::from(*n)) as u8),Type::Int64=>Ref::Primitive(Kind::Int64),Type::Bool=>Ref::Primitive(Kind::Bool),Type::Text=>Ref::Primitive(Kind::Text),Type::TextList=>Ref::Primitive(Kind::TextList),Type::OptionInt64=>Ref::Primitive(Kind::OptionInt64)}).collect()).collect();let mut defs:Vec<_>=refs.iter().map(|v|Definition::Product(v)).collect();for l in &lists{defs.push(Definition::List{element:Ref::Named(l.element as u8),capacity:l.capacity as u8});}if let Err(e)=crate::type_graph::check(&defs,Ref::Primitive(Kind::Int64)){let path=if e.index<records.len(){child("/records",&records[e.index].name)}else{lists.get(e.index-records.len()).map(|l|child("/lists",&l.name)).unwrap_or_else(||"/lists".to_owned())};return fail(if e.reason=="GRAPH_CYCLE"{Reason::Cycle}else{Reason::Bounds},&path);}Ok((records,lists))
}
fn variant_declarations(doc:&Document,rid:ValueId,lid:ValueId,vid:ValueId,profile:u8)->CheckResult<(Vec<RecordDefinition>,Vec<ListDefinition>,Vec<VariantDefinition>)>{
 let rm=object(doc,rid,"/records")?;let lm=object(doc,lid,"/lists")?;let vm=object(doc,vid,"/variants")?;if rm.len()>8{return fail(Reason::Bounds,"/records");}if rm.len()+lm.len()>8{return fail(Reason::Bounds,"/lists");}
 if rm.len()+lm.len()+vm.len()>8{return fail(Reason::Bounds,"/variants");}
 let names=|map:&BTreeMap<JsonString,ValueId>,path:&str|->CheckResult<Vec<String>>{let mut out=Vec::new();for key in map.keys(){let s=key.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,path))?;if !valid_record_name(&s)||matches!(s.as_str(),"Int64"|"Bool"|"Text"|"OptionInt64"|"TextList"){return fail(Reason::Shape,path);}out.push(s);}Ok(out)};
 let rn=names(rm,"/records")?;let ln=names(lm,"/lists")?;let vn=names(vm,"/variants")?;if vn.iter().any(|n|rn.contains(n)||ln.contains(n)){return fail(Reason::Shape,"/variants");}if ln.iter().any(|n|rn.contains(n)){return fail(Reason::Shape,"/lists");}
 let mut records=Vec::new();for((_,&v),name)in rm.iter().zip(&rn){let path=child("/records",name);let fields=object(doc,v,&path)?;if fields.len()>8{return fail(Reason::Bounds,&path);}let mut entries=Vec::new();let mut optional=Vec::new();for(key,&v)in fields{let key=key.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,&path))?;if !valid_record_name(&key){return fail(Reason::Shape,&path);}let at=child(&path,&key);let ty=if profile>=7 && matches!(&doc.values[v],Value::Object(_)){let meta=exact(doc,v,&["type","omit_none"],&at)?;if string(doc,field(meta,"type"),&child(&at,"type"))?!="OptionInt64"{return fail(Reason::Shape,&child(&at,"type"));}if !matches!(&doc.values[field(meta,"omit_none")],Value::Bool(true)){return fail(Reason::Shape,&child(&at,"omit_none"));}optional.push(key.clone());Type::OptionInt64}else{let target=string(doc,v,&at)?;if let Some(i)=rn.iter().position(|n|*n==target){Type::Record(i as u8)}else if let Some(i)=ln.iter().position(|n|*n==target){Type::RecordList(i as u8)}else if let Some(i)=vn.iter().position(|n|*n==target){Type::Variant(i as u8)}else{primitive_ty(doc,v,&at)?}};entries.push((key,ty));}records.push(RecordDefinition{name:name.clone(),fields:entries,optional});}
 let mut lists=Vec::new();for((_,&v),name)in lm.iter().zip(&ln){let path=child("/lists",name);let obj=exact(doc,v,&["element","capacity"],&path)?;let at=child(&path,"element");let target=string(doc,field(obj,"element"),&at)?;let element=rn.iter().position(|n|*n==target).ok_or_else(||Refusal::new(Reason::Reference,&at))?;let at=child(&path,"capacity");let capacity=integer(doc,field(obj,"capacity"),&at)?;if !(0..=if profile==11{16}else{4}).contains(&capacity){return fail(Reason::Bounds,&at);}lists.push(ListDefinition{name:name.clone(),element,capacity:capacity as usize});}
 let mut variants=Vec::new();for((_,&v),name)in vm.iter().zip(&vn){let path=child("/variants",name);let alts=object(doc,v,&path)?;if alts.is_empty()||alts.len()>8{return fail(Reason::Bounds,&path);}let mut alternatives=Vec::new();for(key,&v)in alts{let key=key.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,&path))?;if !valid_record_name(&key){return fail(Reason::Shape,&path);}let at=child(&path,&key);let target=string(doc,v,&at)?;let ty=if let Some(i)=rn.iter().position(|n|*n==target){Type::Record(i as u8)}else if let Some(i)=ln.iter().position(|n|*n==target){Type::RecordList(i as u8)}else if let Some(i)=vn.iter().position(|n|*n==target){Type::Variant(i as u8)}else{primitive_ty(doc,v,&at)?};alternatives.push((key,ty));}variants.push(VariantDefinition{name:name.clone(),alternatives});}
 use crate::type_graph::{Ref,Definition};use crate::record_value::Kind;
 let as_ref=|t:Type|match t{Type::Json=>unreachable!("Json is not a field payload"),Type::Record(n)=>Ref::Named(n),Type::RecordList(n)=>Ref::Named((records.len()+usize::from(n)) as u8),Type::Variant(n)=>Ref::Named((records.len()+lists.len()+usize::from(n)) as u8),Type::Int64=>Ref::Primitive(Kind::Int64),Type::Bool=>Ref::Primitive(Kind::Bool),Type::Text=>Ref::Primitive(Kind::Text),Type::TextList=>Ref::Primitive(Kind::TextList),Type::OptionInt64=>Ref::Primitive(Kind::OptionInt64)};
 let refs:Vec<Vec<Ref>>=records.iter().map(|d|d.fields.iter().map(|(_,t)|as_ref(*t)).collect()).collect();let alternatives:Vec<Vec<Ref>>=variants.iter().map(|d|d.alternatives.iter().map(|(_,t)|as_ref(*t)).collect()).collect();let mut defs:Vec<_>=refs.iter().map(|v|Definition::Product(v)).collect();for l in &lists{defs.push(Definition::List{element:Ref::Named(l.element as u8),capacity:l.capacity as u8});}for a in &alternatives{defs.push(Definition::Sum(a));}
 if let Err(e)=if profile==11{crate::type_graph::check_wide(&defs,Ref::Primitive(Kind::Int64))}else{crate::type_graph::check(&defs,Ref::Primitive(Kind::Int64))}{let path=if e.index<records.len(){child("/records",&records[e.index].name)}else if e.index<records.len()+lists.len(){child("/lists",&lists[e.index-records.len()].name)}else{variants.get(e.index-records.len()-lists.len()).map(|v|child("/variants",&v.name)).unwrap_or_else(||"/variants".to_owned())};return fail(if e.reason=="GRAPH_CYCLE"{Reason::Cycle}else{Reason::Bounds},&path);}Ok((records,lists,variants))
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
struct Builder { variants:Vec<VariantDefinition>, profile:u8, lists:Vec<ListDefinition>, records:Vec<RecordDefinition>, functions: Vec<Function>, nodes: Vec<RawNode> }

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
        if depth>32 || self.nodes.len()==if self.profile>=8{2048}else{512} { return fail(Reason::Bounds,&path); }
        let items=array(doc,value,&path)?;
        if items.is_empty() { return fail(Reason::Shape,&path); }
        // Non-string op is an expression-shape failure. A surrogate string is
        // the offending scalar, not malformed JSON or an invented op spelling.
        let op=match &doc.values[items[0]] {
            Value::String(s)=>s.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,&index(&path,0)))?,
            _=>return fail(Reason::Shape,&path),
        };
        if self.profile<4 && matches!(op.as_str(),"records.list"|"records.len"|"records.at"){return fail(Reason::Shape,&path);}
        if self.profile<5 && matches!(op.as_str(),"variant"|"match"){return fail(Reason::Shape,&path);}
        if self.profile<6 && matches!(op.as_str(),"json.kind"|"json.len"|"json.int"|"json.is_text"|"json.field"|"json.at"|"json.text_or"){return fail(Reason::Shape,&path);}
        if self.profile<10 && op=="records.push"{return fail(Reason::Shape,&path);}
        if self.profile<9 && op=="list.push"{return fail(Reason::Shape,&path);}
        let arity=match op.as_str() {
            "list.push"|"records.push"=>Some(3),
            "json.kind"|"json.len"|"json.int"|"json.is_text"=>Some(2),"json.field"|"json.at"|"json.text_or"=>Some(3),
            "variant"=>Some(4),"match"=>Some(3),
            "records.list" if items.len()>=2=>None,"records.len"=>Some(2),"records.at"=>Some(3),
            "record" if items.len()>=2=>None,"field"=>Some(3),
            "list.text"=>{if items.len()>65{return fail(Reason::Bounds,&path);}None},"list.len"|"list.increasing"|"list.unique"=>Some(2),"list.at"|"list.contains"=>Some(3),
            "none.int"=>Some(1),"some.int"|"option.is_some"=>Some(2),"option.or"=>Some(3),
            "int"|"bool"|"arg"|"use"|"not"|"text"|"text.bytes"|"text.scalars"=>Some(2),
            "add"|"sub"|"mul"|"eq"|"lt"|"le"|"text.eq"|"text.lt"|"text.byte_at"=>Some(3),
            "if"=>Some(4),"let"=>Some(4),"loop"=>Some(6),
            "call" if items.len()>=2=>None,
            _=>return fail(Reason::Shape,&path),
        };
        if arity.is_some_and(|n|items.len()!=n) { return fail(Reason::Shape,&path); }
        let id=(self.nodes.len()+1) as NodeId;
        self.nodes.push(RawNode {function,pointer:path.clone(),ty:None,kind:RawKind::Ready(NodeKind::Int(0))});
        let mut result_type=None;
        let kind=match op.as_str() {
            "records.push"=>{let list=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;let value=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;RawKind::Ready(NodeKind::RecordsPush{list,value})},
            "list.push"=>{let list=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;let value=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;RawKind::Ready(NodeKind::ListPush{list,value})},
            "json.kind"|"json.len"|"json.int"|"json.is_text"=>{let operand=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;RawKind::Ready(match op.as_str(){"json.kind"=>NodeKind::JsonKind{operand},"json.len"=>NodeKind::JsonLen{operand},"json.int"=>NodeKind::JsonInt{operand},_=>NodeKind::JsonIsText{operand}})}
            "json.field"=>{let object=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;let key=string(doc,items[2],&index(&path,2))?;if key.len()>64{return fail(Reason::Bounds,&index(&path,2));}RawKind::Ready(NodeKind::JsonField{object,key})}
            "json.at"=>{let array=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;let at=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;RawKind::Ready(NodeKind::JsonAt{array,index:at})}
            "json.text_or"=>{let json=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;let fallback=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;RawKind::Ready(NodeKind::JsonTextOr{json,fallback})}

            "variant"=>{let name=record_name(doc,items[1],&index(&path,1))?;let definition=self.variants.iter().position(|v|v.name==name).ok_or_else(||Refusal::new(Reason::Reference,&index(&path,1)))?;let tag=record_name(doc,items[2],&index(&path,2))?;let alternative=self.variants[definition].alternatives.iter().position(|(n,_)|*n==tag).ok_or_else(||Refusal::new(Reason::Reference,&index(&path,2)))?;let value=self.expression(doc,items[3],index(&path,3),depth+1,function,scope)?;RawKind::Ready(NodeKind::Variant{definition,alternative,value})}
            "match"=>{let variant=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;let at=index(&path,2);let arms=array(doc,items[2],&at)?;if arms.len()>8{return fail(Reason::Bounds,&at);}let mut cases=Vec::new();for(i,&arm)in arms.iter().enumerate(){let cp=index(&at,i);let parts=array(doc,arm,&cp)?;if parts.len()!=3{return fail(Reason::Shape,&cp);}let name=record_name(doc,parts[0],&index(&cp,0))?;if cases.iter().any(|c:&MatchCase|c.name==name){return fail(Reason::Shape,&index(&cp,0));}let binder=Self::fresh(doc,parts[1],&index(&cp,1),scope)?;let binding=self.local(function,binder.clone(),Type::Int64);let mut inner=scope.clone();inner.insert(binder,binding);let body=self.expression(doc,parts[2],index(&cp,2),depth+1,function,&inner)?;cases.push(MatchCase{name,slot:binding.slot,body});}RawKind::Ready(NodeKind::Match{variant,cases})}

            "records.list"=>{let name=record_name(doc,items[1],&index(&path,1))?;let definition=self.lists.iter().position(|l|l.name==name).ok_or_else(||Refusal::new(Reason::Reference,&index(&path,1)))?;if items.len()>self.lists[definition].capacity+2{return fail(Reason::Bounds,&path);}let mut values=Vec::new();for(i,&v)in items.iter().enumerate().skip(2){values.push(self.expression(doc,v,index(&path,i),depth+1,function,scope)?);}RawKind::Ready(NodeKind::RecordList{definition,values})}
            "records.len"=>{let list=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;RawKind::Ready(NodeKind::RecordsLength{list})}
            "records.at"=>{let list=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;let at=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;RawKind::Ready(NodeKind::RecordsAt{list,index:at})}

            "record"=>{let name=record_name(doc,items[1],&index(&path,1))?;let definition=self.records.iter().position(|r|r.name==name).ok_or_else(||Refusal::new(Reason::Reference,&index(&path,1)))?;if items.len()!=self.records[definition].fields.len()+2{return fail(Reason::Shape,&path);}let mut values=Vec::new();for (i,&v) in items.iter().enumerate().skip(2){values.push(self.expression(doc,v,index(&path,i),depth+1,function,scope)?);}RawKind::Ready(NodeKind::Record{definition,values})}
            "field"=>{let record=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;let name=record_name(doc,items[2],&index(&path,2))?;RawKind::Ready(NodeKind::Field{record,name})}

            "list.text"=>{let mut children=Vec::new();for (i,&v) in items.iter().enumerate().skip(1){children.push(self.expression(doc,v,index(&path,i),depth+1,function,scope)?);}RawKind::Ready(NodeKind::List(children))}
            "list.len"|"list.increasing"|"list.unique"=>{let operand=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;RawKind::Ready(match op.as_str(){"list.len"=>NodeKind::ListLength{operand},"list.increasing"=>NodeKind::ListIncreasing{operand},_=>NodeKind::ListUnique{operand}})}
            "list.at"|"list.contains"=>{let list=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;let other=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;RawKind::Ready(if op=="list.at"{NodeKind::ListAt{list,index:other}}else{NodeKind::ListContains{list,value:other}})}

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
            "text.byte_at"=>{let text=self.expression(doc,items[1],index(&path,1),depth+1,function,scope)?;let at=self.expression(doc,items[2],index(&path,2),depth+1,function,scope)?;RawKind::Ready(NodeKind::TextByteAt{text,index:at})}
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
            NodeKind::JsonKind{operand}=>{self.require(operand,Type::Json)?;Type::Text}
            NodeKind::JsonLen{operand}|NodeKind::JsonInt{operand}=>{self.require(operand,Type::Json)?;Type::OptionInt64}
            NodeKind::JsonIsText{operand}=>{self.require(operand,Type::Json)?;Type::Bool}
            NodeKind::JsonField{object,..}=>{self.require(object,Type::Json)?;Type::Json}
            NodeKind::JsonAt{array,index}=>{self.require(array,Type::Json)?;self.require(index,Type::Int64)?;Type::Json}
            NodeKind::JsonTextOr{json,fallback}=>{self.require(json,Type::Json)?;self.require(fallback,Type::Text)?;Type::Text}

            NodeKind::Variant{definition,alternative,value}=>{let ty=self.variants[definition].alternatives[alternative].1;self.require(value,ty)?;Type::Variant(definition as u8)}
            NodeKind::Match{variant,cases}=>{let definition=match self.infer(variant)?{Type::Variant(v)=>usize::from(v),_=>return fail(Reason::Type,&self.nodes[usize::from(variant)-1].pointer)};let alts=self.variants[definition].alternatives.clone();let at=index(&self.nodes[n].pointer,2);if cases.len()!=alts.len(){return fail(Reason::Shape,&at);}let mut result=None;for(i,c)in cases.iter().enumerate(){let ty=alts.iter().find(|(name,_)|*name==c.name).map(|(_,t)|*t).ok_or_else(||Refusal::new(Reason::Reference,&index(&index(&at,i),0)))?;let f=self.nodes[n].function;self.functions[f].locals[c.slot].ty=ty;let ty=self.infer(c.body)?;if let Some(expected)=result{if expected!=ty{return fail(Reason::Type,&self.nodes[usize::from(c.body)-1].pointer);}}else{result=Some(ty);}}result.expect("nonempty exhaustive match")}

            NodeKind::RecordList{definition,values}=>{let element=self.lists[definition].element;for v in values{self.require(v,Type::Record(element as u8))?;}Type::RecordList(definition as u8)}
            NodeKind::RecordsPush{list,value}=>{let definition=match self.infer(list)?{Type::RecordList(n)=>usize::from(n),_=>return fail(Reason::Type,&self.nodes[usize::from(list)-1].pointer)};self.require(value,Type::Record(self.lists[definition].element as u8))?;Type::RecordList(definition as u8)}
            NodeKind::RecordsLength{list}=>{if !matches!(self.infer(list)?,Type::RecordList(_)){return fail(Reason::Type,&self.nodes[usize::from(list)-1].pointer);}Type::Int64}
            NodeKind::RecordsAt{list,index}=>{let n=match self.infer(list)?{Type::RecordList(n)=>n,_=>return fail(Reason::Type,&self.nodes[usize::from(list)-1].pointer)};self.require(index,Type::Int64)?;Type::Record(self.lists[usize::from(n)].element as u8)}

            NodeKind::Record{definition,values}=>{for (i,node) in values.into_iter().enumerate(){let expected=self.records[definition].fields[i].1;self.require(node,expected)?;}Type::Record(definition as u8)}
            NodeKind::Field{record,name}=>{let t=self.infer(record)?;let d=match t{Type::Record(d)=>usize::from(d),_=>return fail(Reason::Type,&self.nodes[usize::from(record)-1].pointer)};self.records[d].fields.iter().find(|(n,_)|*n==name).map(|(_,t)|*t).ok_or_else(||Refusal::new(Reason::Reference,&index(&self.nodes[n].pointer,2)))?}

            NodeKind::List(items)=>{for item in items{self.require(item,Type::Text)?;}Type::TextList}
            NodeKind::ListPush{list,value}=>{self.require(list,Type::TextList)?;self.require(value,Type::Text)?;Type::TextList}
            NodeKind::ListLength{operand}=>{self.require(operand,Type::TextList)?;Type::Int64}
            NodeKind::ListIncreasing{operand}=>{self.require(operand,Type::TextList)?;Type::Bool}
            NodeKind::ListUnique{operand}=>{self.require(operand,Type::TextList)?;Type::TextList}
            NodeKind::ListAt{list,index}=>{self.require(list,Type::TextList)?;self.require(index,Type::Int64)?;Type::Text}
            NodeKind::ListContains{list,value}=>{self.require(list,Type::TextList)?;self.require(value,Type::Text)?;Type::Bool}

            NodeKind::OptionSome{operand}=>{if self.infer(operand)?!=Type::Int64{return fail(Reason::Type,&self.nodes[n].pointer);}Type::OptionInt64}
            NodeKind::OptionHas{operand}=>{if self.infer(operand)?!=Type::OptionInt64{return fail(Reason::Type,&self.nodes[n].pointer);}Type::Bool}
            NodeKind::OptionOr{option,fallback}=>{if self.infer(option)?!=Type::OptionInt64{return fail(Reason::Type,&self.nodes[n].pointer);}if self.infer(fallback)?!=Type::Int64{return fail(Reason::Type,&self.nodes[n].pointer);}Type::Int64}

            NodeKind::Binary{op,left,right}=>match op {
                BinaryOp::Eq=>{ let left_type=self.infer(left)?; if !matches!(left_type,Type::Int64|Type::Bool){return fail(Reason::Type,&self.nodes[usize::from(left)-1].pointer);} self.require(right,left_type)?; Type::Bool }
                BinaryOp::Add|BinaryOp::Sub|BinaryOp::Mul=>{ self.require(left,Type::Int64)?;self.require(right,Type::Int64)?;Type::Int64 }
                BinaryOp::Lt|BinaryOp::Le=>{ self.require(left,Type::Int64)?;self.require(right,Type::Int64)?;Type::Bool }
            },
            NodeKind::TextBinary{left,right,..}=>{self.require(left,Type::Text)?;self.require(right,Type::Text)?;Type::Bool}
            NodeKind::TextByteAt{text,index}=>{self.require(text,Type::Text)?;self.require(index,Type::Int64)?;Type::OptionInt64}
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

fn program(doc: &Document, root: ValueId, profile:u8) -> Result<CheckedSource,FrontendError> {
    let envelope=exact(doc,root,if profile>=5{&["schema","records","lists","variants","entry","functions"]}else if profile==4{&["schema","records","lists","entry","functions"]}else{&["schema","records","entry","functions"]},"")?;
    schema(doc,envelope,if profile==11{"bagaev-typed-record/11"}else if profile==10{"bagaev-typed-record/10"}else if profile==9{"bagaev-typed-record/9"}else if profile==8{"bagaev-typed-record/8"}else if profile==7{"bagaev-typed-record/7"}else if profile==6{"bagaev-typed-record/6"}else if profile==5{"bagaev-typed-record/5"}else if profile==4{"bagaev-typed-record/4"}else if profile==3{"bagaev-typed-record/3"}else if profile==2{"bagaev-typed-record/2"}else{"bagaev-typed-record/1"},"")?;
    json_bounds(doc,root,128,8192,"")?;
    if profile>=6{for name in ["records","lists","variants"]{if object(doc,field(envelope,name),&format!("/{name}"))?.contains_key(&JsonString::from_str("Json")){return Err(Refusal::new(Reason::Shape,&format!("/{name}")).into());}}}
    let (records,lists,variants)=if profile>=5{variant_declarations(doc,field(envelope,"records"),field(envelope,"lists"),field(envelope,"variants"),profile)?}else{let pair=if profile==4{composite_records(doc,field(envelope,"records"),field(envelope,"lists"))?}else{(if profile==3{nested_records(doc,field(envelope,"records"))?}else{records(doc,field(envelope,"records"))?},Vec::new())}; (pair.0,pair.1,Vec::new())};
    let entry_name=identifier(doc,field(envelope,"entry"),"/entry")?;
    let definitions=object(doc,field(envelope,"functions"),"/functions")?;
    if !(1..=if profile>=8{32}else{8}).contains(&definitions.len()) { return Err(Refusal::new(Reason::Bounds,"/functions").into()); }
    let mut names=Vec::new();
    for key in definitions.keys() {
        let name=key.scalar_string().ok_or_else(||Refusal::new(Reason::Shape,"/functions"))?;
        if !valid_id(&name) { return Err(Refusal::new(Reason::Shape,"/functions").into()); }
        names.push(name);
    }
    let mut builder=Builder{profile,records,lists,variants,functions:Vec::new(),nodes:Vec::new()};
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
            let ty=declared_ty(doc,pair[1],&index(&pointer,1),&builder.records,&builder.lists,&builder.variants,profile)?;
            scope.insert(name.clone(),Binding{slot:i,ty,parameter:true});
            parameters.push(Parameter{name,ty});
        }
        let result=declared_ty(doc,field(definition,"result"),&child(&path,"result"),&builder.records,&builder.lists,&builder.variants,profile)?;
        builder.functions.push(Function{name,parameters,result,body:0,locals:Vec::new(),callees:Vec::new()});
        let body=builder.expression(doc,field(definition,"body"),child(&path,"body"),1,function,&scope)?;
        builder.functions[function].body=body;
    }
    let entry=builder.references(&entry_name)?;
    builder.cycles()?;
    builder.types()?;
    if builder.functions[entry].result==Type::Json{return Err(Refusal::new(Reason::Type,&format!("/functions/{}/result",builder.functions[entry].name)).into());}
    if profile==1 && matches!(builder.functions[entry].result,Type::Record(_)){return Err(Refusal::new(Reason::Type,&format!("/functions/{}/result",builder.functions[entry].name)).into());}
    for (i,p) in builder.functions[entry].parameters.iter().enumerate(){if profile==1 && matches!(p.ty,Type::Record(_)){return Err(Refusal::new(Reason::Type,&format!("/functions/{}/params/{i}/1",builder.functions[entry].name)).into());}}

    let canonical=canonical::program_bytes(doc,root).map_err(FrontendError::Environment)?;
    let identity=sha256::digest(&canonical);
    let nodes=builder.nodes.into_iter().enumerate().map(|(i,node)|{
        let kind=match node.kind {RawKind::Ready(kind)=>kind,_=>unreachable!("complete reference phase")};
        Node{id:(i+1) as NodeId,function:node.function,pointer:node.pointer,
             ty:node.ty.expect("complete type phase visits every expression"),kind}
    }).collect();
    Ok(CheckedSource{profile,records:builder.records,lists:builder.lists,variants:builder.variants,functions:builder.functions,nodes,entry,canonical,identity})
}

fn parsed(bytes: &[u8]) -> Result<Document,FrontendError> {
    transport::parse(bytes).map_err(|e|Refusal::new(match e {TransportError::Bounds=>Reason::Bounds,TransportError::Json=>Reason::Json},"").into())
}

#[derive(Clone)]
struct RuntimeList<'a>{values:std::rc::Rc<Vec<crate::text_value::Text<'a>>>,bytes:usize}
impl<'a> RuntimeList<'a>{
 fn new(values:Vec<crate::text_value::Text<'a>>)->Result<Self,()>{let bytes=crate::text_list::TextList::new(&values).map_err(|_|())?.total_bytes();Ok(Self{values:std::rc::Rc::new(values),bytes})}
}
#[derive(Clone)]
struct RuntimeRecord<'a>{definition:usize,values:std::rc::Rc<Vec<RuntimeValue<'a>>>}
#[derive(Clone)]
struct RuntimeVariant<'a>{definition:usize,alternative:usize,value:std::rc::Rc<RuntimeValue<'a>>}
#[derive(Clone)]
enum RuntimeValue<'a> { Json(crate::json_view::View<'a>), Variant(RuntimeVariant<'a>), RecordList(RuntimeRecord<'a>), Record(RuntimeRecord<'a>), Int(i64), Bool(bool), Text(crate::text_value::Text<'a>), Optional(crate::option_int::OptionInt64), List(RuntimeList<'a>) }
impl<'a> RuntimeValue<'a> {
 fn json(self)->Result<crate::json_view::View<'a>,EvalError>{match self{Self::Json(v)=>Ok(v),_=>Err(EvalError::Environment("checked Json type"))}}
 fn variant(self)->Result<RuntimeVariant<'a>,EvalError>{match self{Self::Variant(v)=>Ok(v),_=>Err(EvalError::Environment("checked variant"))}}
 fn record_list(self)->Result<RuntimeRecord<'a>,EvalError>{match self{Self::RecordList(v)=>Ok(v),_=>Err(EvalError::Environment("checked record-list type"))}}
    fn record(self)->Result<RuntimeRecord<'a>,EvalError>{match self{Self::Record(r)=>Ok(r),_=>Err(EvalError::Environment("checked record type"))}}
    fn list(self)->Result<RuntimeList<'a>,EvalError>{match self{Self::List(v)=>Ok(v),_=>Err(EvalError::Environment("checked list type"))}}
    fn optional(self)->Result<crate::option_int::OptionInt64,EvalError>{match self{Self::Optional(v)=>Ok(v),_=>Err(EvalError::Environment("checked optional type"))}}
    fn int(self)->Result<i64,EvalError>{match self{Self::Int(x)=>Ok(x),_=>Err(EvalError::Environment("checked integer type"))}}
    fn boolean(self)->Result<bool,EvalError>{match self{Self::Bool(x)=>Ok(x),_=>Err(EvalError::Environment("checked boolean type"))}}
    fn text(self)->Result<crate::text_value::Text<'a>,EvalError>{match self{Self::Text(x)=>Ok(x),_=>Err(EvalError::Environment("checked text type"))}}
}
enum EvalError { RecordListItems(NodeId), ListItems(NodeId), ListBytes(NodeId), Index(NodeId), Work(NodeId), Overflow(NodeId), Environment(&'static str) }
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
            NodeKind::JsonKind{operand}=>{let value=self.expression(*operand,args,locals)?.json()?;Ok(RuntimeValue::Text(crate::text_value::Text::from_bytes(value.kind().as_bytes()).map_err(|_|EvalError::Environment("fixed kind text"))?))}
            NodeKind::JsonLen{operand}=>Ok(RuntimeValue::Optional(self.expression(*operand,args,locals)?.json()?.len())),
            NodeKind::JsonInt{operand}=>{let value=self.expression(*operand,args,locals)?.json()?;self.charge(value.int_charge(),id)?;Ok(RuntimeValue::Optional(value.integer()))}
            NodeKind::JsonIsText{operand}=>Ok(RuntimeValue::Bool(self.expression(*operand,args,locals)?.json()?.text_len().is_some())),
            NodeKind::JsonField{object,key}=>{let value=self.expression(*object,args,locals)?.json()?;self.charge(value.field_charge(key),id)?;Ok(RuntimeValue::Json(value.field(key)))}
            NodeKind::JsonAt{array,index}=>{let value=self.expression(*array,args,locals)?.json()?;let at=self.expression(*index,args,locals)?.int()?;Ok(RuntimeValue::Json(value.at(at)))}
            NodeKind::JsonTextOr{json,fallback}=>{let value=self.expression(*json,args,locals)?.json()?;if let Some(bytes)=value.text_len(){self.charge(bytes as u64,id)?;Ok(RuntimeValue::Text(value.text().ok_or(EvalError::Environment("checked cached text"))?))}else{self.expression(*fallback,args,locals)}}

            NodeKind::Variant{definition,alternative,value}=>{let value=self.expression(*value,args,locals)?;Ok(RuntimeValue::Variant(RuntimeVariant{definition:*definition,alternative:*alternative,value:std::rc::Rc::new(value)}))}
            NodeKind::Match{variant,cases}=>{let value=self.expression(*variant,args,locals)?.variant()?;let name=&self.program.variants[value.definition].alternatives[value.alternative].0;let arm=cases.iter().find(|c|c.name==*name).ok_or(EvalError::Environment("exhaustive match"))?;locals[arm.slot]=Some((*value.value).clone());self.expression(arm.body,args,locals)}

            NodeKind::RecordList{definition,values}=>{let mut fields=Vec::new();for v in values{fields.push(self.expression(*v,args,locals)?);}Ok(RuntimeValue::RecordList(RuntimeRecord{definition:*definition,values:std::rc::Rc::new(fields)}))}
            NodeKind::RecordsPush{list,value}=>{
                let list=self.expression(*list,args,locals)?.record_list()?;
                let record=self.expression(*value,args,locals)?.record()?;
                let count=list.values.len()+1;self.charge(count as u64,id)?;
                if count>program.lists[list.definition].capacity{return Err(EvalError::RecordListItems(id));}
                let mut values=list.values.as_ref().clone();values.push(RuntimeValue::Record(record));
                Ok(RuntimeValue::RecordList(RuntimeRecord{definition:list.definition,values:std::rc::Rc::new(values)}))
            }
            NodeKind::RecordsLength{list}=>Ok(RuntimeValue::Int(self.expression(*list,args,locals)?.record_list()?.values.len() as i64)),
            NodeKind::RecordsAt{list,index}=>{let list=self.expression(*list,args,locals)?.record_list()?;let at=self.expression(*index,args,locals)?.int()?;if at<0||at as u64>=list.values.len() as u64{return Err(EvalError::Index(id));}Ok(list.values[at as usize].clone())}

            NodeKind::Record{definition,values}=>{let mut fields=Vec::new();for value in values{fields.push(self.expression(*value,args,locals)?);}Ok(RuntimeValue::Record(RuntimeRecord{definition:*definition,values:std::rc::Rc::new(fields)}))}
            NodeKind::Field{record,name}=>{let value=self.expression(*record,args,locals)?.record()?;let at=self.program.records[value.definition].fields.iter().position(|(n,_)|n==name).ok_or(EvalError::Environment("checked field name"))?;Ok(value.values[at].clone())}

            NodeKind::List(items)=>{let mut values=Vec::with_capacity(items.len());for item in items{values.push(self.expression(*item,args,locals)?.text()?);}Ok(RuntimeValue::List(RuntimeList::new(values).map_err(|_|EvalError::ListBytes(id))?))}
            NodeKind::ListPush{list,value}=>{
                let list=self.expression(*list,args,locals)?.list()?;
                let value=self.expression(*value,args,locals)?.text()?;
                let count=list.values.len()+1;
                self.charge(count as u64,id)?;
                if count>crate::text_list::ITEM_LIMIT{return Err(EvalError::ListItems(id));}
                if list.bytes+value.byte_len()>crate::text_list::BYTE_LIMIT{return Err(EvalError::ListBytes(id));}
                let mut values=list.values.as_ref().clone();values.push(value);
                Ok(RuntimeValue::List(RuntimeList::new(values).map_err(|_|EvalError::Environment("checked append bounds"))?))
            }
            NodeKind::ListLength{operand}=>Ok(RuntimeValue::Int(self.expression(*operand,args,locals)?.list()?.values.len() as i64)),
            NodeKind::ListAt{list,index}=>{let list=self.expression(*list,args,locals)?.list()?;let index=self.expression(*index,args,locals)?.int()?;if index<0 || index as u64>=list.values.len() as u64{return Err(EvalError::Index(id));}Ok(RuntimeValue::Text(list.values[index as usize]))}
            NodeKind::ListContains{list,value}=>{let list=self.expression(*list,args,locals)?.list()?;let value=self.expression(*value,args,locals)?.text()?;let n=list.values.len() as u64;self.charge(n+list.bytes as u64+n*value.byte_len() as u64,id)?;let view=crate::text_list::TextList::new(&list.values).map_err(|_|EvalError::Environment("checked list bounds"))?;Ok(RuntimeValue::Bool(view.contains(value)))}
            NodeKind::ListIncreasing{operand}=>{let list=self.expression(*operand,args,locals)?.list()?;self.charge(list.values.len() as u64+2*list.bytes as u64,id)?;let view=crate::text_list::TextList::new(&list.values).map_err(|_|EvalError::Environment("checked list bounds"))?;Ok(RuntimeValue::Bool(view.is_strictly_increasing()))}
            NodeKind::ListUnique{operand}=>{let list=self.expression(*operand,args,locals)?.list()?;let n=list.values.len() as u64;self.charge(n*n+2*n*list.bytes as u64,id)?;let sorted=crate::text_list::TextList::new(&list.values).map_err(|_|EvalError::Environment("checked list bounds"))?.unique_sorted();let values=(0..sorted.len()).map(|i|sorted.get(i).expect("complete sorted prefix")).collect();Ok(RuntimeValue::List(RuntimeList::new(values).map_err(|_|EvalError::Environment("normalized list bounds"))?))}

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
            NodeKind::Arg{parameter}=>args.get(*parameter).cloned().ok_or(EvalError::Environment("checked argument")),
            NodeKind::Use{slot}=>locals.get(*slot).cloned().flatten().ok_or(EvalError::Environment("checked local")),
            NodeKind::Not{operand}=>Ok(RuntimeValue::Bool(!self.expression(*operand,args,locals)?.boolean()?)),
            NodeKind::TextByteAt{text,index}=>{let t=self.expression(*text,args,locals)?.text()?;let i=self.expression(*index,args,locals)?.int()?;Ok(RuntimeValue::Optional(crate::text_inspection::byte_at(t,i)))}
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
                for i in 0..*count{locals[*index_slot]=Some(RuntimeValue::Int(i64::from(i)));locals[*accumulator_slot]=Some(value.clone());value=self.expression(*body,args,locals)?;}
                Ok(value)
            }
        }
    }
}
fn render_value(value:&RuntimeValue<'_>,records:&[RecordDefinition],lists:&[ListDefinition],variants:&[VariantDefinition],out:&mut String)->Result<String,&'static str>{
 use std::fmt::Write;
 let label=match value{
  RuntimeValue::Json(_)=>return Err("raw Json entry excluded"),
  RuntimeValue::Int(v)=>{write!(out,"{v}").map_err(|_|"format")?;"Int64"},
  RuntimeValue::Bool(v)=>{out.push_str(if *v{"true"}else{"false"});"Bool"},
  RuntimeValue::Text(v)=>{canonical::quote(std::str::from_utf8(v.bytes()).map_err(|_|"checked UTF8")?,out);"Text"},
  RuntimeValue::Optional(v)=>{match v.value(){Some(n)=>write!(out,"{n}").map_err(|_|"format")?,None=>out.push_str("null")};"OptionInt64"},
  RuntimeValue::List(v)=>{out.push('[');for(i,t)in v.values.iter().enumerate(){if i>0{out.push(',');}canonical::quote(std::str::from_utf8(t.bytes()).map_err(|_|"checked UTF8")?,out);}out.push(']');"TextList"},
  RuntimeValue::Variant(v)=>{let d=variants.get(v.definition).ok_or("checked variant identity")?;let name=&d.alternatives.get(v.alternative).ok_or("checked alternative")?.0;out.push_str("{\"case\":");canonical::quote(name,out);out.push_str(",\"value\":");render_value(&v.value,records,lists,variants,out)?;out.push('}');return Ok(format!("Variant:{}",d.name));},
  RuntimeValue::RecordList(v)=>{let d=lists.get(v.definition).ok_or("checked list identity")?;out.push('[');for(i,x)in v.values.iter().enumerate(){if i>0{out.push(',');}render_value(x,records,lists,variants,out)?;}out.push(']');return Ok(format!("RecordList:{}",d.name));},
  RuntimeValue::Record(v)=>{let d=records.get(v.definition).ok_or("checked record identity")?;if d.fields.len()!=v.values.len(){return Err("checked record arity");}out.push('{');let mut written=0;for((name,_),value)in d.fields.iter().zip(v.values.iter()){if d.optional.contains(name)&&matches!(value,RuntimeValue::Optional(v) if !v.is_some()){continue;}if written>0{out.push(',');}written+=1;canonical::quote(name,out);out.push(':');render_value(value,records,lists,variants,out)?;}out.push('}');return Ok(format!("Record:{}",d.name));},
 };Ok(label.to_owned())
}
fn result_wire(status:&str,reason:Option<&str>,location:Option<&str>,value:Option<RuntimeValue<'_>>,work:u64,records:&[RecordDefinition],lists:&[ListDefinition],variants:&[VariantDefinition],profile:u8)->Result<Vec<u8>,&'static str>{
 use std::fmt::Write;
 let mut out=String::from("{\"location\":");match location{Some(x)=>canonical::quote(x,&mut out),None=>out.push_str("null")};out.push_str(",\"reason\":");match reason{Some(x)=>canonical::quote(x,&mut out),None=>out.push_str("null")};
 write!(&mut out,",\"schema\":\"bagaev-typed-record-result/{profile}\",\"status\":").map_err(|_|"format")?;canonical::quote(status,&mut out);out.push_str(",\"value\":");let ty=match value{Some(v)=>Some(render_value(&v,records,lists,variants,&mut out)?),None=>{out.push_str("null");None}};out.push_str(",\"value_type\":");match ty{Some(x)=>canonical::quote(&x,&mut out),None=>out.push_str("null")};write!(&mut out,",\"work\":{work}}}\n").map_err(|_|"format")?;Ok(out.into_bytes())
}
enum OwnedArgument { Json(Box<crate::json_view::Owned>), Variant(usize,usize,Box<OwnedArgument>), RecordList(usize,Vec<OwnedArgument>), Record(usize,Vec<OwnedArgument>), List(Vec<String>), Int(i64), Bool(bool), Text(String), Optional(crate::option_int::OptionInt64) }
fn decode_argument(doc:&Document,id:ValueId,ty:Type,path:&str,records:&[RecordDefinition],lists:&[ListDefinition],variants:&[VariantDefinition])->Result<OwnedArgument,FrontendError>{
 let bad=||Refusal::new(Reason::Argument,path);
 Ok(match (ty,&doc.values[id]){
  (Type::Json,_)=>OwnedArgument::Json(Box::new(crate::json_view::Owned::copy(doc,id).map_err(FrontendError::Environment)?)),
  (Type::Variant(n),Value::Object(map))=>{if map.len()!=2||!map.contains_key(&JsonString::from_str("case"))||!map.contains_key(&JsonString::from_str("value")){return Err(bad().into());}let d=&variants[usize::from(n)];let tag=match &doc.values[map[&JsonString::from_str("case")]]{Value::String(s)=>s.scalar_string(),_=>None};let alternative=tag.and_then(|s|d.alternatives.iter().position(|(n,_)|*n==s)).ok_or_else(||Refusal::new(Reason::Argument,&child(path,"case")))?;let value=decode_argument(doc,map[&JsonString::from_str("value")],d.alternatives[alternative].1,&child(path,"value"),records,lists,variants)?;OwnedArgument::Variant(usize::from(n),alternative,Box::new(value))},

  (Type::RecordList(n),Value::Array(items))=>{let d=&lists[usize::from(n)];if items.len()>d.capacity{return Err(bad().into());}let mut values=Vec::new();for(i,&v)in items.iter().enumerate(){values.push(decode_argument(doc,v,Type::Record(d.element as u8),&index(path,i),records,lists,variants)?);}OwnedArgument::RecordList(usize::from(n),values)},

  (Type::Record(n),Value::Object(map))=>{let d=&records[usize::from(n)];if map.len()>d.fields.len()||d.fields.iter().any(|(name,_)|!d.optional.contains(name)&&!map.contains_key(&JsonString::from_str(name)))||map.keys().any(|key|!d.fields.iter().any(|(name,_)|JsonString::from_str(name)==*key)){return Err(bad().into());}let mut values=Vec::new();for(name,kind)in &d.fields{let at=child(path,name);if let Some(&v)=map.get(&JsonString::from_str(name)){if d.optional.contains(name)&&matches!(&doc.values[v],Value::Null){return Err(Refusal::new(Reason::Argument,&at).into());}values.push(decode_argument(doc,v,*kind,&at,records,lists,variants)?);}else{values.push(OwnedArgument::Optional(crate::option_int::OptionInt64::none()));}}OwnedArgument::Record(usize::from(n),values)},
  (Type::TextList,Value::Array(items))=>{if items.len()>64{return Err(bad().into());}let mut strings=Vec::new();for(j,&item)in items.iter().enumerate(){let at=index(path,j);let bad_item=||Refusal::new(Reason::Argument,&at);let text=match &doc.values[item]{Value::String(s)=>s.scalar_string().ok_or_else(bad_item)?,_=>return Err(bad_item().into())};crate::text_value::Text::from_bytes(text.as_bytes()).map_err(|_|bad_item())?;strings.push(text);}if strings.iter().map(String::len).sum::<usize>()>4096{return Err(bad().into());}OwnedArgument::List(strings)},
  (Type::OptionInt64,Value::Null)=>OwnedArgument::Optional(crate::option_int::OptionInt64::none()),
  (Type::OptionInt64,Value::Integer(s))=>OwnedArgument::Optional(crate::option_int::OptionInt64::some(s.parse().map_err(|_|bad())?)),
  (Type::Int64,Value::Integer(s))=>OwnedArgument::Int(s.parse().map_err(|_|bad())?),
  (Type::Bool,Value::Bool(v))=>OwnedArgument::Bool(*v),
  (Type::Text,Value::String(s))=>{let text=s.scalar_string().ok_or_else(bad)?;crate::text_value::Text::from_bytes(text.as_bytes()).map_err(|_|bad())?;OwnedArgument::Text(text)},
  _=>return Err(bad().into()),
 })
}
fn checked_invocation(doc:&Document,profile:u8)->Result<(CheckedSource,Vec<OwnedArgument>),FrontendError>{
 let outer=exact(doc,doc.root,&["schema","program","arguments"],"")?;schema(doc,outer,if profile==11{"bagaev-typed-record-invocation/11"}else if profile==10{"bagaev-typed-record-invocation/10"}else if profile==9{"bagaev-typed-record-invocation/9"}else if profile==8{"bagaev-typed-record-invocation/8"}else if profile==7{"bagaev-typed-record-invocation/7"}else if profile==6{"bagaev-typed-record-invocation/6"}else if profile==5{"bagaev-typed-record-invocation/5"}else if profile==4{"bagaev-typed-record-invocation/4"}else if profile==3{"bagaev-typed-record-invocation/3"}else if profile==2{"bagaev-typed-record-invocation/2"}else{"bagaev-typed-record-invocation/1"},"")?;json_bounds(doc,doc.root,132,16384,"")?;
 let checked=program(doc,field(outer,"program"),profile).map_err(|e|match e{FrontendError::Refusal(mut r)=>{r.location=format!("/program{}",r.location);FrontendError::Refusal(r)},other=>other})?;
 let vals=match &doc.values[field(outer,"arguments")]{Value::Array(v)=>v,_=>return Err(Refusal::new(Reason::Argument,"/arguments").into())};let params=&checked.functions[checked.entry].parameters;if vals.len()!=params.len(){return Err(Refusal::new(Reason::Argument,"/arguments").into());}let mut args=Vec::new();for(i,(&v,p))in vals.iter().zip(params).enumerate(){args.push(decode_argument(doc,v,p.ty,&format!("/arguments/{i}"),&checked.records,&checked.lists,&checked.variants)?);}Ok((checked,args))
}
fn runtime_argument(a:&OwnedArgument)->Result<RuntimeValue<'_>,&'static str>{Ok(match a{
 OwnedArgument::Json(v)=>RuntimeValue::Json(v.root()),
 OwnedArgument::Variant(n,a,value)=>RuntimeValue::Variant(RuntimeVariant{definition:*n,alternative:*a,value:std::rc::Rc::new(runtime_argument(value)?)}),
 OwnedArgument::RecordList(n,values)=>RuntimeValue::RecordList(RuntimeRecord{definition:*n,values:std::rc::Rc::new(values.iter().map(runtime_argument).collect::<Result<Vec<_>,_>>()?)}),
 OwnedArgument::Record(n,values)=>RuntimeValue::Record(RuntimeRecord{definition:*n,values:std::rc::Rc::new(values.iter().map(runtime_argument).collect::<Result<Vec<_>,_>>()?)}),
 OwnedArgument::List(strings)=>{let values=strings.iter().map(|s|crate::text_value::Text::from_bytes(s.as_bytes())).collect::<Result<Vec<_>,_>>().map_err(|_|"checked list argument")?;RuntimeValue::List(RuntimeList::new(values).map_err(|_|"checked list argument bounds")?)},
 OwnedArgument::Optional(v)=>RuntimeValue::Optional(*v),OwnedArgument::Int(x)=>RuntimeValue::Int(*x),OwnedArgument::Bool(x)=>RuntimeValue::Bool(*x),OwnedArgument::Text(x)=>RuntimeValue::Text(crate::text_value::Text::from_bytes(x.as_bytes()).map_err(|_|"checked text argument")?)})}
/// Complete bounded invocation, returning only detached scalar/error data.
/// This reference evaluator does not invoke compilers or generated native code.
pub fn process(bytes:&[u8])->Result<Vec<u8>,&'static str>{process_profile(bytes,1)}
pub fn process_v2(bytes:&[u8])->Result<Vec<u8>,&'static str>{process_profile(bytes,2)}
pub fn process_v3(bytes:&[u8])->Result<Vec<u8>,&'static str>{process_profile(bytes,3)}
pub fn process_v4(bytes:&[u8])->Result<Vec<u8>,&'static str>{process_profile(bytes,4)}
pub fn process_v5(bytes:&[u8])->Result<Vec<u8>,&'static str>{process_profile(bytes,5)}
pub fn process_v6(bytes:&[u8])->Result<Vec<u8>,&'static str>{process_profile(bytes,6)}
pub fn process_v7(bytes:&[u8])->Result<Vec<u8>,&'static str>{process_profile(bytes,7)}
pub fn process_v8(bytes:&[u8])->Result<Vec<u8>,&'static str>{process_profile(bytes,8)}
pub fn process_v9(bytes:&[u8])->Result<Vec<u8>,&'static str>{process_profile(bytes,9)}
fn process_profile(bytes:&[u8],profile:u8)->Result<Vec<u8>,&'static str>{
    let checked=parsed(bytes).and_then(|doc|checked_invocation(&doc,profile));
    let (program,owned)=match checked{Ok(x)=>x,Err(FrontendError::Environment(e))=>return Err(e),Err(FrontendError::Refusal(r))=>return result_wire("invalid-ir",Some(r.reason().name()),Some(r.location()),None,0,&[],&[],&[],profile)};
    let args=owned.iter().map(runtime_argument).collect::<Result<Vec<_>,_>>()?;
    let mut runtime=Runtime{program:&program,work:0};
    match runtime.function(program.entry,&args){
        Ok(value)=>result_wire("success",None,None,Some(value),runtime.work,&program.records,&program.lists,&program.variants,profile),
        Err(EvalError::Environment(e))=>Err(e),
        Err(error)=>{let (id,status,reason)=match error{EvalError::RecordListItems(id)=>(id,"record-list-bound","RR_RECORD_LIST_ITEMS"),EvalError::ListItems(id)=>(id,"list-bound","RR_LIST_ITEMS"),EvalError::ListBytes(id)=>(id,"list-bound","RR_LIST_BYTES"),EvalError::Index(id)=>(id,"list-index","RR_INDEX"),EvalError::Work(id)=>(id,"work-limit","RR_WORK"),EvalError::Overflow(id)=>(id,"integer-overflow","RR_OVERFLOW"),EvalError::Environment(_)=>unreachable!()};let loc=format!("/program{}",program.node(id).ok_or("runtime node")?.pointer());result_wire(status,Some(reason),Some(&loc),None,runtime.work,&program.records,&program.lists,&program.variants,profile)}
    }
}

pub fn checked_program(bytes:&[u8])->Result<CheckedSource,String>{let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;program(&doc,doc.root,1).map_err(|e|format!("{e:?}"))}

/// Checked source or stable source refusal data; neither variant admits execution.
pub enum SourceCheck { Checked(CheckedSource), Refused { reason: &'static str, location: String } }
pub fn check_source(bytes:&[u8])->Result<SourceCheck,&'static str>{
    match parsed(bytes).and_then(|doc|program(&doc,doc.root,1)) {
        Ok(p)=>Ok(SourceCheck::Checked(p)),
        Err(FrontendError::Refusal(r))=>Ok(SourceCheck::Refused{reason:r.reason().name(),location:r.location}),
        Err(FrontendError::Environment(e))=>Err(e),
    }
}

pub fn checked_program_v2(bytes:&[u8])->Result<CheckedSource,String>{let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;program(&doc,doc.root,2).map_err(|e|format!("{e:?}"))}

pub fn checked_program_v3(bytes:&[u8])->Result<CheckedSource,String>{let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;program(&doc,doc.root,3).map_err(|e|format!("{e:?}"))}

pub fn checked_program_v4(bytes:&[u8])->Result<CheckedSource,String>{let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;program(&doc,doc.root,4).map_err(|e|format!("{e:?}"))}

pub fn checked_program_v5(bytes:&[u8])->Result<CheckedSource,String>{let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;program(&doc,doc.root,5).map_err(|e|format!("{e:?}"))}

/// Full /6 envelope data admission; not an execution capability.
/// The first native Json slice accepts Json-only entry arguments.
pub struct CheckedJsonInvocation { program:CheckedSource, arguments:Vec<Box<crate::json_view::Owned>> }
impl CheckedJsonInvocation {
 pub fn program(&self)->&CheckedSource{&self.program}
 pub fn json_arguments(&self)->&[Box<crate::json_view::Owned>]{&self.arguments}
}
pub fn checked_json_invocation(bytes:&[u8])->Result<CheckedJsonInvocation,String>{
 let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;
 let (program,args)=checked_invocation(&doc,6).map_err(|e|format!("{e:?}"))?;
 if program.functions[program.entry].parameters.iter().any(|p|p.ty!=Type::Json){return Err("NATIVE_JSON_SIGNATURE".to_owned());}
 let mut arguments=Vec::new();
 for arg in args{match arg{OwnedArgument::Json(v)=>arguments.push(v),_=>return Err("NATIVE_JSON_SIGNATURE".to_owned())}}
 Ok(CheckedJsonInvocation{program,arguments})
}
pub fn checked_program_v6(bytes:&[u8])->Result<CheckedSource,String>{let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;program(&doc,doc.root,6).map_err(|e|format!("{e:?}"))}

pub fn checked_json_invocation_v8(bytes:&[u8])->Result<CheckedJsonInvocation,String>{
 let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;
 let (program,args)=checked_invocation(&doc,8).map_err(|e|format!("{e:?}"))?;
 if program.functions[program.entry].parameters.iter().any(|p|p.ty!=Type::Json){return Err("NATIVE_JSON_SIGNATURE".to_owned());}
 let mut arguments=Vec::new();
 for arg in args{match arg{OwnedArgument::Json(v)=>arguments.push(v),_=>return Err("NATIVE_JSON_SIGNATURE".to_owned())}}
 Ok(CheckedJsonInvocation{program,arguments})
}

/// Experimental source-once /8 Json data handle. This is not native execution authority.
/// Its calling convention has a canonical conceptual-envelope budget; old APIs are unchanged.
pub struct PreparedJsonProgram { source:CheckedSource, source_values:usize }
impl PreparedJsonProgram {
 pub fn source(&self)->&CheckedSource { &self.source }
 pub fn source_values(&self)->usize { self.source_values }
}
pub struct PreparedJsonInvocation<'p> {
 program:&'p PreparedJsonProgram,
 arguments:Vec<Box<crate::json_view::Owned>>,
}
impl<'p> PreparedJsonInvocation<'p> {
 pub fn program(&self)->&PreparedJsonProgram { self.program }
 pub fn json_arguments(&self)->&[Box<crate::json_view::Owned>] { &self.arguments }
}
pub fn prepare_json_program_v8(bytes:&[u8])->Result<PreparedJsonProgram,String> {
 let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;
 let source=program(&doc,doc.root,8).map_err(|e|format!("{e:?}"))?;
 if source.functions[source.entry].parameters.iter().any(|p|p.ty!=Type::Json) {
  return Err("NATIVE_JSON_SIGNATURE".to_owned());
 }
 // Reparse only at preparation to count the canonical source's actual JSON values.
 let canonical=parsed(source.canonical_bytes()).map_err(|e|format!("{e:?}"))?;
 Ok(PreparedJsonProgram{source,source_values:canonical.values.len()})
}
pub fn prepare_json_arguments_v8<'p>(program:&'p PreparedJsonProgram,raw:&[u8])->Result<PreparedJsonInvocation<'p>,String> {
 let bytes=69usize.checked_add(program.source.canonical_bytes().len()).and_then(|n|n.checked_add(raw.len()));
 if bytes.map_or(true,|n|n>transport::FRAME_LIMIT) { return Err("PREPARED_FRAME_BOUNDS".to_owned()); }
 let doc=parsed(raw).map_err(|e|format!("{e:?}"))?;
 let total=program.source_values.checked_add(doc.values.len()).and_then(|n|n.checked_add(2));
 if total.map_or(true,|n|n>16384) { return Err("PREPARED_VALUE_BOUNDS".to_owned()); }
 json_bounds(&doc,doc.root,131,16384,"/arguments").map_err(|e|format!("{e:?}"))?;
 let items=match &doc.values[doc.root] { Value::Array(v)=>v,_=>return Err("PREPARED_ARGUMENT_ARRAY".to_owned()) };
 if items.len()!=program.source.functions[program.source.entry].parameters.len() { return Err("PREPARED_ARGUMENT_ARITY".to_owned()); }
 let mut arguments=Vec::with_capacity(items.len());
 for &id in items { arguments.push(Box::new(crate::json_view::Owned::copy(&doc,id).map_err(str::to_owned)?)); }
 Ok(PreparedJsonInvocation{program,arguments})
}
/// Evaluate already admitted source and per-call Json owners. Work starts at zero each time.
pub fn evaluate_prepared_json_v8(invocation:&PreparedJsonInvocation<'_>)->Result<Vec<u8>,&'static str> {
 let program=&invocation.program.source;
 let args=invocation.arguments.iter().map(|v|RuntimeValue::Json(v.root())).collect::<Vec<_>>();
 let mut runtime=Runtime{program,work:0};
 match runtime.function(program.entry,&args) {
  Ok(value)=>result_wire("success",None,None,Some(value),runtime.work,&program.records,&program.lists,&program.variants,8),
  Err(EvalError::Environment(e))=>Err(e),
  Err(error)=>{
   let(id,status,reason)=match error {
    EvalError::RecordListItems(id)=>(id,"record-list-bound","RR_RECORD_LIST_ITEMS"),EvalError::ListItems(id)=>(id,"list-bound","RR_LIST_ITEMS"),EvalError::ListBytes(id)=>(id,"list-bound","RR_LIST_BYTES"),EvalError::Index(id)=>(id,"list-index","RR_INDEX"),
    EvalError::Work(id)=>(id,"work-limit","RR_WORK"),EvalError::Overflow(id)=>(id,"integer-overflow","RR_OVERFLOW"),
    EvalError::Environment(_)=>unreachable!(),
   };
   let loc=format!("/program{}",program.node(id).ok_or("runtime node")?.pointer());
   result_wire(status,Some(reason),Some(&loc),None,runtime.work,&program.records,&program.lists,&program.variants,8)
  }
 }
}

pub fn checked_program_v9(bytes:&[u8])->Result<CheckedSource,String>{let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;program(&doc,doc.root,9).map_err(|e|format!("{e:?}"))}

pub fn checked_json_invocation_v9(bytes:&[u8])->Result<CheckedJsonInvocation,String>{
 let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;
 let (program,args)=checked_invocation(&doc,9).map_err(|e|format!("{e:?}"))?;
 if program.functions[program.entry].parameters.iter().any(|p|p.ty!=Type::Json){return Err("NATIVE_JSON_SIGNATURE".to_owned());}
 let mut arguments=Vec::new();
 for arg in args{match arg{OwnedArgument::Json(v)=>arguments.push(v),_=>return Err("NATIVE_JSON_SIGNATURE".to_owned())}}
 Ok(CheckedJsonInvocation{program,arguments})
}

pub fn process_v10(bytes:&[u8])->Result<Vec<u8>,&'static str>{process_profile(bytes,10)}
pub fn checked_program_v10(bytes:&[u8])->Result<CheckedSource,String>{let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;program(&doc,doc.root,10).map_err(|e|format!("{e:?}"))}

pub fn checked_json_invocation_v10(bytes:&[u8])->Result<CheckedJsonInvocation,String>{
 let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;
 let (program,args)=checked_invocation(&doc,10).map_err(|e|format!("{e:?}"))?;
 if program.functions[program.entry].parameters.iter().any(|p|p.ty!=Type::Json){return Err("NATIVE_JSON_SIGNATURE".to_owned());}
 let mut arguments=Vec::new();
 for arg in args{match arg{OwnedArgument::Json(v)=>arguments.push(v),_=>return Err("NATIVE_JSON_SIGNATURE".to_owned())}}
 Ok(CheckedJsonInvocation{program,arguments})
}

/// Experimental source-once /10 Json data handle. This is not native execution authority.
/// Its calling convention has a canonical conceptual-envelope budget; old APIs are unchanged.
pub struct PreparedJsonProgramV10 { source:CheckedSource, source_values:usize }
impl PreparedJsonProgramV10 {
 pub fn source(&self)->&CheckedSource { &self.source }
 pub fn source_values(&self)->usize { self.source_values }
}
pub struct PreparedJsonInvocationV10<'p> {
 program:&'p PreparedJsonProgramV10,
 arguments:Vec<Box<crate::json_view::Owned>>,
}
impl<'p> PreparedJsonInvocationV10<'p> {
 pub fn program(&self)->&PreparedJsonProgramV10 { self.program }
 pub fn json_arguments(&self)->&[Box<crate::json_view::Owned>] { &self.arguments }
}
pub fn prepare_json_program_v10(bytes:&[u8])->Result<PreparedJsonProgramV10,String> {
 let doc=parsed(bytes).map_err(|e|format!("{e:?}"))?;
 let source=program(&doc,doc.root,10).map_err(|e|format!("{e:?}"))?;
 if source.functions[source.entry].parameters.iter().any(|p|p.ty!=Type::Json) {
  return Err("NATIVE_JSON_SIGNATURE".to_owned());
 }
 // Reparse only at preparation to count the canonical source's actual JSON values.
 let canonical=parsed(source.canonical_bytes()).map_err(|e|format!("{e:?}"))?;
 Ok(PreparedJsonProgramV10{source,source_values:canonical.values.len()})
}
pub fn prepare_json_arguments_v10<'p>(program:&'p PreparedJsonProgramV10,raw:&[u8])->Result<PreparedJsonInvocationV10<'p>,String> {
 let bytes=70usize.checked_add(program.source.canonical_bytes().len()).and_then(|n|n.checked_add(raw.len()));
 if bytes.map_or(true,|n|n>transport::FRAME_LIMIT) { return Err("PREPARED_FRAME_BOUNDS".to_owned()); }
 let doc=parsed(raw).map_err(|e|format!("{e:?}"))?;
 let total=program.source_values.checked_add(doc.values.len()).and_then(|n|n.checked_add(2));
 if total.map_or(true,|n|n>16384) { return Err("PREPARED_VALUE_BOUNDS".to_owned()); }
 json_bounds(&doc,doc.root,131,16384,"/arguments").map_err(|e|format!("{e:?}"))?;
 let items=match &doc.values[doc.root] { Value::Array(v)=>v,_=>return Err("PREPARED_ARGUMENT_ARRAY".to_owned()) };
 if items.len()!=program.source.functions[program.source.entry].parameters.len() { return Err("PREPARED_ARGUMENT_ARITY".to_owned()); }
 let mut arguments=Vec::with_capacity(items.len());
 for &id in items { arguments.push(Box::new(crate::json_view::Owned::copy(&doc,id).map_err(str::to_owned)?)); }
 Ok(PreparedJsonInvocationV10{program,arguments})
}
/// Evaluate already admitted source and per-call Json owners. Work starts at zero each time.
pub fn evaluate_prepared_json_v10(invocation:&PreparedJsonInvocationV10<'_>)->Result<Vec<u8>,&'static str> {
 let program=&invocation.program.source;
 let args=invocation.arguments.iter().map(|v|RuntimeValue::Json(v.root())).collect::<Vec<_>>();
 let mut runtime=Runtime{program,work:0};
 match runtime.function(program.entry,&args) {
  Ok(value)=>result_wire("success",None,None,Some(value),runtime.work,&program.records,&program.lists,&program.variants,10),
  Err(EvalError::Environment(e))=>Err(e),
  Err(error)=>{
   let(id,status,reason)=match error {
    EvalError::RecordListItems(id)=>(id,"record-list-bound","RR_RECORD_LIST_ITEMS"),EvalError::ListItems(id)=>(id,"list-bound","RR_LIST_ITEMS"),EvalError::ListBytes(id)=>(id,"list-bound","RR_LIST_BYTES"),EvalError::Index(id)=>(id,"list-index","RR_INDEX"),
    EvalError::Work(id)=>(id,"work-limit","RR_WORK"),EvalError::Overflow(id)=>(id,"integer-overflow","RR_OVERFLOW"),
    EvalError::Environment(_)=>unreachable!(),
   };
   let loc=format!("/program{}",program.node(id).ok_or("runtime node")?.pointer());
   result_wire(status,Some(reason),Some(&loc),None,runtime.work,&program.records,&program.lists,&program.variants,10)
  }
 }
}


/// Structured, data-only /10 source checking for composition readers.
/// Preserves refusal versus environment failure; does not evaluate or admit code.
pub fn check_source_v10(bytes:&[u8])->Result<SourceCheck,&'static str>{
 match parsed(bytes).and_then(|doc|program(&doc,doc.root,10)) {
  Ok(source)=>Ok(SourceCheck::Checked(source)),
  Err(FrontendError::Refusal(r))=>Ok(SourceCheck::Refused{reason:r.reason().name(),location:r.location().to_owned()}),
  Err(FrontendError::Environment(e))=>Err(e),
 }
}

pub fn process_v11(bytes:&[u8])->Result<Vec<u8>,&'static str>{process_profile(bytes,11)}
