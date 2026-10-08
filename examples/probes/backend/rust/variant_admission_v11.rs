//! Data-only nominal product and profile11 bounded record-list admission. No raw pointers, mutation or execution.
use crate::{record_value::{Kind, Value}, type_graph::{self, Definition, Ref}};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Type { Primitive(Kind), Record(u8), RecordList(u8), Variant(u8) }
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ListDefinition { pub element: u8, pub capacity: u8 }
pub enum Node<'a, 'items, 'text> {
    Primitive(Value<'items, 'text>),
    Record { definition: u8, children: &'a [usize] },
    RecordList { definition: u8, children: &'a [usize] },
    Variant { definition: u8, alternative: u8, child: usize },
}
pub struct Argument<'a, 'items, 'text> {
    pub nodes: &'a [Node<'a, 'items, 'text>],
    pub root: usize,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Refusal { pub reason: &'static str, pub index: usize, pub node: usize }
fn bad(reason: &'static str, index: usize, node: usize) -> Refusal {
    Refusal { reason, index, node }
}
pub struct Checked<'s, 'a, 'items, 'text> {
    definitions: &'s [&'s [Type]],
    lists: &'s [ListDefinition],
    variants: &'s [&'s [Type]],
    signature: &'s [Type],
    result: Type,
    arguments: &'s [Argument<'a, 'items, 'text>],
}
impl<'s, 'a, 'items, 'text> Checked<'s, 'a, 'items, 'text> {
    pub fn definitions(&self) -> &[&[Type]] { self.definitions }
    pub fn lists(&self) -> &[ListDefinition] { self.lists }
    pub fn variants(&self) -> &[&[Type]] { self.variants }
    pub fn signature(&self) -> &[Type] { self.signature }
    pub fn result(&self) -> Type { self.result }
    pub fn arguments(&self) -> &[Argument<'a, 'items, 'text>] { self.arguments }
}
fn valid(ty: Type, count: usize, lists: usize, variants: usize) -> bool {
    match ty {
        Type::Primitive(k) => k != Kind::IntProjection,
        Type::Record(n) => usize::from(n) < count,
        Type::RecordList(n) => usize::from(n) < lists,
        Type::Variant(n) => usize::from(n) < variants,
    }
}
fn walk(defs: &[&[Type]], lists: &[ListDefinition], variants: &[&[Type]], expected: Type, arg: &Argument<'_, '_, '_>,
        index: usize, at: usize, seen: &mut [bool; 4096]) -> Result<(), Refusal> {
    let node = arg.nodes.get(at).ok_or_else(|| bad("ADMIT_REF", index, at))?;
    // A seen mark must never bypass checking this particular typed occurrence.
    seen[at] = true;
    match (expected, node) {
        (Type::Primitive(k), Node::Primitive(v)) if k == v.kind() => Ok(()),
        (Type::Record(n), Node::Record { definition, children }) if n == *definition => {
            let fields = defs[usize::from(n)];
            if fields.len() != children.len() { return Err(bad("ADMIT_FIELDS", index, at)); }
            for (&ty, &child) in fields.iter().zip(*children) {
                walk(defs, lists, variants, ty, arg, index, child, seen)?;
            }
            Ok(())
        }
        (Type::RecordList(n), Node::RecordList { definition, children }) if n == *definition => {
            let list = lists[usize::from(n)];
            if children.len() > usize::from(list.capacity) { return Err(bad("ADMIT_ITEMS", index, at)); }
            for &child in *children {
                walk(defs, lists, variants, Type::Record(list.element), arg, index, child, seen)?;
            }
            Ok(())
        }
        (Type::Variant(n), Node::Variant { definition, alternative, child }) if n == *definition => {
            let payload = variants[usize::from(n)].get(usize::from(*alternative))
                .ok_or_else(|| bad("ADMIT_TAG", index, at))?;
            walk(defs, lists, variants, *payload, arg, index, *child, seen)
        }
        _ => Err(bad("ADMIT_TYPE", index, at)),
    }
}

pub fn check<'s, 'a, 'items, 'text>(
    definitions: &'s [&'s [Type]], lists: &'s [ListDefinition], variants: &'s [&'s [Type]], signature: &'s [Type], result: Type,
    arguments: &'s [Argument<'a, 'items, 'text>],
    text_scratch: usize, cell_scratch: usize, input_cells: usize,
) -> Result<Checked<'s, 'a, 'items, 'text>, Refusal> {
    if definitions.len() > 8 || lists.len() > 8 - definitions.len() || variants.len() > 8 - definitions.len() - lists.len() { return Err(bad("ADMIT_DECLARATIONS", 8, 0)); }
    let mut fields = [[Ref::Primitive(Kind::Int64); 8]; 8];
    let mut lengths = [0usize; 8];
    for (i, row) in definitions.iter().enumerate() {
        if row.len() > 8 { return Err(bad("ADMIT_RECORD_FIELDS", i, 8)); }
        lengths[i] = row.len();
        for (j, &ty) in row.iter().enumerate() {
            if !valid(ty, definitions.len(), lists.len(), variants.len()) { return Err(bad("ADMIT_RECORD_TYPE", i, j)); }
            fields[i][j] = match ty { Type::Primitive(k) => Ref::Primitive(k), Type::Record(n) => Ref::Named(n), Type::RecordList(n) => Ref::Named((definitions.len()+usize::from(n)) as u8), Type::Variant(n) => Ref::Named((definitions.len()+lists.len()+usize::from(n)) as u8) };
        }
    }
    for (i, list) in lists.iter().enumerate() {
        if usize::from(list.element) >= definitions.len() { return Err(bad("ADMIT_LIST_ELEMENT", i, usize::from(list.element))); }
        if list.capacity > 16 { return Err(bad("ADMIT_LIST_CAPACITY", i, usize::from(list.capacity))); }
    }
    let mut variant_fields = [[Ref::Primitive(Kind::Int64); 8]; 8];
    let mut variant_lengths = [0usize; 8];
    for (i, row) in variants.iter().enumerate() {
        if row.is_empty() || row.len() > 8 { return Err(bad("ADMIT_VARIANT_ALTS", i, row.len())); }
        variant_lengths[i] = row.len();
        for (j, &ty) in row.iter().enumerate() {
            if !valid(ty, definitions.len(), lists.len(), variants.len()) { return Err(bad("ADMIT_VARIANT_TYPE", i, j)); }
            variant_fields[i][j] = match ty {
                Type::Primitive(k) => Ref::Primitive(k), Type::Record(n) => Ref::Named(n),
                Type::RecordList(n) => Ref::Named((definitions.len()+usize::from(n)) as u8),
                Type::Variant(n) => Ref::Named((definitions.len()+lists.len()+usize::from(n)) as u8),
            };
        }
    }
    let graph: [Definition<'_>; 8] = std::array::from_fn(|i| {
        if i < definitions.len() { Definition::Product(&fields[i][..lengths[i]]) }
        else if let Some(list) = lists.get(i-definitions.len()) { Definition::List { element: Ref::Named(list.element), capacity: list.capacity } }
        else { let v=i-definitions.len()-lists.len(); if v<variants.len() {Definition::Sum(&variant_fields[v][..variant_lengths[v]])} else {Definition::Product(&[])} }
    });
    type_graph::check_wide(&graph[..definitions.len()+lists.len()+variants.len()], Ref::Primitive(Kind::Int64))
        .map_err(|e| bad(e.reason, e.index, 0))?;
    if signature.len() > 8 { return Err(bad("ADMIT_PARAMS", 8, 0)); }
    for (i, &ty) in signature.iter().enumerate() {
        if !valid(ty, definitions.len(), lists.len(), variants.len()) { return Err(bad("ADMIT_SIGNATURE", i, 0)); }
    }
    if !valid(result, definitions.len(), lists.len(), variants.len()) { return Err(bad("ADMIT_RESULT", 0, 0)); }
    if signature.len() != arguments.len() {
        return Err(bad("ADMIT_COUNT", signature.len().min(arguments.len()), 0));
    }
    for (i, (&ty, arg)) in signature.iter().zip(arguments).enumerate() {
        if arg.nodes.len() > 4096 { return Err(bad("ADMIT_ARENA", i, 4096)); }
        if arg.root >= arg.nodes.len() { return Err(bad("ADMIT_ROOT", i, arg.root)); }
        let mut seen = [false; 4096];
        walk(definitions, lists, variants, ty, arg, i, arg.root, &mut seen)?;
        if let Some(at) = seen[..arg.nodes.len()].iter().position(|x| !*x) {
            return Err(bad("ADMIT_UNUSED", i, at));
        }
    }
    if text_scratch != 65536 { return Err(bad("ADMIT_TEXT_SCRATCH", text_scratch, 0)); }
    if cell_scratch != 65536 { return Err(bad("ADMIT_CELL_SCRATCH", cell_scratch, 0)); }
    if input_cells != 32768 { return Err(bad("ADMIT_INPUT_CELLS", input_cells, 0)); }
    Ok(Checked { definitions, lists, variants, signature, result, arguments })
}
