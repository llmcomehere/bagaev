//! Separate typed Text-list IR data shapes; not the frozen scalar native ABI.


/// One-based complete structural occurrence number, not a machine-code offset.
pub type NodeId = u16;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Type { Int64, Bool, Text, OptionInt64, TextList }
impl Type {
    pub fn name(self) -> &'static str { match self { Self::Int64 => "Int64", Self::Bool => "Bool", Self::Text => "Text", Self::OptionInt64=>"OptionInt64",Self::TextList=>"TextList" } }
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

#[derive(Clone, Debug)]
pub enum NodeKind {
    Int(i64), Bool(bool), Text(String),
    List(Vec<NodeId>), ListLength{operand:NodeId}, ListAt{list:NodeId,index:NodeId}, ListContains{list:NodeId,value:NodeId}, ListIncreasing{operand:NodeId}, ListUnique{operand:NodeId},
    OptionNone, OptionSome { operand:NodeId }, OptionHas { operand:NodeId }, OptionOr { option:NodeId, fallback:NodeId },
    TextBinary { equal: bool, left: NodeId, right: NodeId },
    TextLength { scalars: bool, operand: NodeId },
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
            Self::List(_)=>"list.text",Self::ListLength{..}=>"list.len",Self::ListAt{..}=>"list.at",Self::ListContains{..}=>"list.contains",Self::ListIncreasing{..}=>"list.increasing",Self::ListUnique{..}=>"list.unique",
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
            Self::List(items)=>items.clone(),Self::ListLength{operand}|Self::ListIncreasing{operand}|Self::ListUnique{operand}=>vec![*operand],Self::ListAt{list,index}=>vec![*list,*index],Self::ListContains{list,value}=>vec![*list,*value],
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
