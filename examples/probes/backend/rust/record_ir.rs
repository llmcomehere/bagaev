//! Separate typed inspection IR data shapes; not the frozen scalar native ABI.


/// One-based complete structural occurrence number, not a machine-code offset.
pub type NodeId = u16;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Type { Int64, Bool, Text, OptionInt64, TextList, Record(u8), RecordList(u8), Variant(u8), Json }
impl Type {
    pub fn name(self) -> &'static str { match self { Self::Int64 => "Int64", Self::Bool => "Bool", Self::Text => "Text", Self::OptionInt64=>"OptionInt64",Self::TextList=>"TextList",Self::Record(_)=>"Record",Self::RecordList(_)=>"RecordList",Self::Variant(_)=>"Variant",Self::Json=>"Json" } }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Scalar { Int64(i64), Bool(bool) }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BinaryOp { Add, Sub, Mul, Eq, Lt, Le }
impl BinaryOp {
    pub fn name(self) -> &'static str {
        match self { Self::Add=>"add",Self::Sub=>"sub",Self::Mul=>"mul",Self::Eq=>"eq",Self::Lt=>"lt",Self::Le=>"le" }
    }
}

#[derive(Clone,Debug)]
pub struct MatchCase{pub name:String,pub slot:usize,pub body:NodeId}
#[derive(Clone, Debug)]
pub enum NodeKind {
    Int(i64), Bool(bool), Text(String),
    JsonKind{operand:NodeId},JsonLen{operand:NodeId},JsonInt{operand:NodeId},JsonIsText{operand:NodeId},JsonField{object:NodeId,key:String},JsonAt{array:NodeId,index:NodeId},JsonTextOr{json:NodeId,fallback:NodeId},JsonBoolOr{json:NodeId,fallback:NodeId},
    Variant{definition:usize,alternative:usize,value:NodeId}, Match{variant:NodeId,cases:Vec<MatchCase>},
    RecordList{definition:usize,values:Vec<NodeId>}, RecordsLength{list:NodeId}, RecordsAt{list:NodeId,index:NodeId},
    Record{definition:usize,values:Vec<NodeId>}, Field{record:NodeId,name:String},
    List(Vec<NodeId>), ListLength{operand:NodeId}, ListPush { list: NodeId, value: NodeId }, RecordsPush { list: NodeId, value: NodeId }, ListAt{list:NodeId,index:NodeId}, ListContains{list:NodeId,value:NodeId}, ListIncreasing{operand:NodeId}, ListUnique{operand:NodeId},
    OptionNone, OptionSome { operand:NodeId }, OptionHas { operand:NodeId }, OptionOr { option:NodeId, fallback:NodeId },
    TextBinary { equal: bool, left: NodeId, right: NodeId },
    TextLength { scalars: bool, operand: NodeId },
    TextByteAt { text: NodeId, index: NodeId },
    Arg { parameter: usize }, Use { slot: usize },
    Binary { op: BinaryOp, left: NodeId, right: NodeId },
    Not { operand: NodeId },
    Let { slot: usize, declared: Type, value: NodeId, body: NodeId },
    If { condition: NodeId, yes: NodeId, no: NodeId },
    Call { function: usize, arguments: Vec<NodeId> },
    Loop { count: u16, index_slot: usize, accumulator_slot: usize, declared: Type,
           initial: NodeId, body: NodeId },
}
impl NodeKind {
    pub fn name(&self) -> &'static str {
        match self {
            Self::JsonKind{..}=>"json.kind",Self::JsonLen{..}=>"json.len",Self::JsonInt{..}=>"json.int",Self::JsonIsText{..}=>"json.is_text",Self::JsonField{..}=>"json.field",Self::JsonAt{..}=>"json.at",Self::JsonTextOr{..}=>"json.text_or",Self::JsonBoolOr{..}=>"json.bool_or",
            Self::Variant{..}=>"variant",Self::Match{..}=>"match",
            Self::RecordList{..}=>"records.list",Self::RecordsLength{..}=>"records.len",Self::RecordsAt{..}=>"records.at",
            Self::Record{..}=>"record",Self::Field{..}=>"field",
            Self::TextByteAt{..}=>"text.byte_at",
            Self::RecordsPush{..}=>"records.push",Self::ListPush{..}=>"list.push",Self::List(_)=>"list.text",Self::ListLength{..}=>"list.len",Self::ListAt{..}=>"list.at",Self::ListContains{..}=>"list.contains",Self::ListIncreasing{..}=>"list.increasing",Self::ListUnique{..}=>"list.unique",
            Self::OptionNone=>"none.int",Self::OptionSome{..}=>"some.int",Self::OptionHas{..}=>"option.is_some",Self::OptionOr{..}=>"option.or",
            Self::Text(_)=>"text",Self::TextBinary{equal:true,..}=>"text.eq",Self::TextBinary{equal:false,..}=>"text.lt",Self::TextLength{scalars:true,..}=>"text.scalars",Self::TextLength{scalars:false,..}=>"text.bytes",
            Self::Int(_)=>"int",Self::Bool(_)=>"bool",Self::Arg{..}=>"arg",Self::Use{..}=>"use",
            Self::Binary{op,..}=>op.name(),Self::Not{..}=>"not",Self::Let{..}=>"let",
            Self::If{..}=>"if",Self::Call{..}=>"call",Self::Loop{..}=>"loop",
        }
    }
    /// Source evaluation order; includes both lazy arms and a loop's body statically.
    pub fn children(&self) -> Vec<NodeId> {
        match self {
            Self::JsonKind{operand}|Self::JsonLen{operand}|Self::JsonInt{operand}|Self::JsonIsText{operand}=>vec![*operand],Self::JsonField{object,..}=>vec![*object],Self::JsonAt{array,index}=>vec![*array,*index],Self::JsonTextOr{json,fallback}|Self::JsonBoolOr{json,fallback}=>vec![*json,*fallback],
            Self::Variant{value,..}=>vec![*value],Self::Match{variant,cases}=>{let mut v=vec![*variant];v.extend(cases.iter().map(|c|c.body));v},
            Self::RecordList{values,..}=>values.clone(),Self::RecordsLength{list}=>vec![*list],Self::RecordsAt{list,index}=>vec![*list,*index],
            Self::Record{values,..}=>values.clone(),Self::Field{record,..}=>vec![*record],
            Self::TextByteAt{text,index}=>vec![*text,*index],
            Self::List(items)=>items.clone(),Self::ListLength{operand}|Self::ListIncreasing{operand}|Self::ListUnique{operand}=>vec![*operand],Self::ListAt{list,index}=>vec![*list,*index],Self::RecordsPush{list,value}|Self::ListContains{list,value}|Self::ListPush{list,value}=>vec![*list,*value],
            Self::OptionSome{operand}|Self::OptionHas{operand}=>vec![*operand],Self::OptionOr{option,fallback}=>vec![*option,*fallback],
            Self::TextBinary{left,right,..}|Self::Binary{left,right,..}=>vec![*left,*right], Self::TextLength{operand,..}=>vec![*operand], Self::Not{operand}=>vec![*operand],
            Self::Let{value,body,..}=>vec![*value,*body],
            Self::If{condition,yes,no}=>vec![*condition,*yes,*no],
            Self::Call{arguments,..}=>arguments.clone(),
            Self::Loop{initial,body,..}=>vec![*initial,*body], _=>Vec::new(),
        }
    }
}

#[derive(Debug)]
pub struct Node {
    pub(crate) id: NodeId,
    pub(crate) function: usize,
    pub(crate) pointer: String,
    pub(crate) ty: Type,
    pub(crate) kind: NodeKind,
}
impl Node {
    pub fn id(&self) -> NodeId { self.id }
    pub fn function(&self) -> usize { self.function }
    /// Relative to the complete program, without an invocation /program prefix.
    pub fn pointer(&self) -> &str { &self.pointer }
    pub fn ty(&self) -> Type { self.ty }
    pub fn kind(&self) -> &NodeKind { &self.kind }
}

#[derive(Clone, Debug)]
pub struct Parameter { pub(crate) name: String, pub(crate) ty: Type }
impl Parameter {
    pub fn name(&self) -> &str { &self.name }
    pub fn ty(&self) -> Type { self.ty }
}

#[derive(Clone, Debug)]
pub struct Local { pub(crate) name: String, pub(crate) ty: Type }
impl Local {
    pub fn name(&self) -> &str { &self.name }
    pub fn ty(&self) -> Type { self.ty }
}

#[derive(Debug)]
pub struct Function {
    pub(crate) name: String,
    pub(crate) parameters: Vec<Parameter>,
    pub(crate) result: Type,
    pub(crate) body: NodeId,
    pub(crate) locals: Vec<Local>,
    pub(crate) callees: Vec<usize>,
}
impl Function {
    pub fn name(&self) -> &str { &self.name }
    pub fn parameters(&self) -> &[Parameter] { &self.parameters }
    pub fn result(&self) -> Type { self.result }
    pub fn body(&self) -> NodeId { self.body }
    /// Slots are function-local, allocated in structural binder order, never reused.
    pub fn locals(&self) -> &[Local] { &self.locals }
    pub fn callees(&self) -> &[usize] { &self.callees }
}
