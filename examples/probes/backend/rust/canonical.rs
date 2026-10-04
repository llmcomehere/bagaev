//! Canonical scalar JSON and explicitly distinct checked-tool artifacts.
use crate::check::{CheckedInvocation, Refusal};
use crate::ir::{NodeKind, Scalar};
use crate::transport::{Document, JsonString, Value, ValueId};
use std::fmt::Write;

pub fn quote(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"'=>out.push_str("\\\""), '\\'=>out.push_str("\\\\"),
            '\u{8}'=>out.push_str("\\b"), '\u{c}'=>out.push_str("\\f"),
            '\n'=>out.push_str("\\n"), '\r'=>out.push_str("\\r"), '\t'=>out.push_str("\\t"),
            c if (c as u32) < 32 => { write!(out, "\\u{:04x}", c as u32).unwrap(); }
            _=>out.push(c),
        }
    }
    out.push('"');
}

enum Action<'a> { Value(ValueId), Key(&'a JsonString), Text(&'static str) }
pub(crate) fn program_bytes(doc: &Document, root: ValueId) -> Result<Vec<u8>, &'static str> {
    let mut stack = vec![Action::Value(root)];
    let mut out = String::new();
    while let Some(action) = stack.pop() {
        match action {
            Action::Text(text)=>out.push_str(text),
            Action::Key(key)=>quote(&key.scalar_string().ok_or("non-scalar checked key")?, &mut out),
            Action::Value(id)=>match &doc.values[id] {
                Value::Null=>out.push_str("null"),
                Value::Bool(b)=>out.push_str(if *b { "true" } else { "false" }),
                Value::Integer(n)=>write!(&mut out, "{}", n.parse::<i64>().map_err(|_| "non-Int64 checked integer")?).unwrap(),
                Value::Number(_)=>return Err("non-integer checked number"),
                Value::String(s)=>quote(&s.scalar_string().ok_or("non-scalar checked string")?, &mut out),
                Value::Array(items)=>{
                    out.push('['); stack.push(Action::Text("]"));
                    for (i,&child) in items.iter().enumerate().rev() {
                        stack.push(Action::Value(child));
                        if i > 0 { stack.push(Action::Text(",")); }
                    }
                }
                Value::Object(items)=>{
                    out.push('{'); stack.push(Action::Text("}"));
                    for (i,(key,&child)) in items.iter().enumerate().rev() {
                        stack.push(Action::Value(child)); stack.push(Action::Text(":"));
                        stack.push(Action::Key(key)); if i > 0 { stack.push(Action::Text(",")); }
                    }
                }
            },
        }
    }
    Ok(out.into_bytes())
}

pub fn refusal_bytes(error: &Refusal) -> Vec<u8> {
    let mut out = String::from("{\"location\":"); quote(error.location(), &mut out);
    out.push_str(",\"reason\":"); quote(error.reason().name(), &mut out);
    out.push_str(",\"schema\":\"bagaev-probe-result/1\",\"status\":\"invalid-ir\",\"value\":null,\"value_type\":null,\"work\":0}\n");
    out.into_bytes()
}

fn ids(values: &[u16], out: &mut String) {
    out.push('['); for (i,n) in values.iter().enumerate() { if i>0 { out.push(','); } write!(out,"{n}").unwrap(); } out.push(']');
}

/// No deserializer: this artifact cannot grant the checked Rust type or authority.
pub fn invocation_bytes(invocation: &CheckedInvocation) -> Vec<u8> {
    let program = invocation.program();
    let mut out = String::from("{\"arguments\":[");
    for (i,value) in invocation.arguments().iter().enumerate() {
        if i>0 { out.push(','); }
        match value { Scalar::Int64(n)=>write!(&mut out,"{n}").unwrap(), Scalar::Bool(b)=>out.push_str(if *b {"true"} else {"false"}) }
    }
    write!(&mut out,"],\"entry\":{},\"functions\":[",program.entry()).unwrap();
    for (i,function) in program.functions().iter().enumerate() {
        if i>0 { out.push(','); }
        write!(&mut out,"{{\"body\":{},\"callees\":[",function.body()).unwrap();
        for (j,n) in function.callees().iter().enumerate() { if j>0 { out.push(','); } write!(&mut out,"{n}").unwrap(); }
        write!(&mut out,"],\"index\":{i},\"locals\":[").unwrap();
        for (j,local) in function.locals().iter().enumerate() {
            if j>0 { out.push(','); } out.push_str("{\"name\":"); quote(local.name(),&mut out);
            write!(&mut out,",\"slot\":{j},\"type\":").unwrap(); quote(local.ty().name(),&mut out); out.push('}');
        }
        out.push_str("],\"name\":"); quote(function.name(),&mut out); out.push_str(",\"parameters\":[");
        for (j,parameter) in function.parameters().iter().enumerate() {
            if j>0 { out.push(','); } out.push_str("{\"name\":"); quote(parameter.name(),&mut out);
            write!(&mut out,",\"slot\":{j},\"type\":").unwrap(); quote(parameter.ty().name(),&mut out); out.push('}');
        }
        out.push_str("],\"result\":"); quote(function.result().name(),&mut out); out.push('}');
    }
    out.push_str("],\"nodes\":[");
    for (i,node) in program.nodes().iter().enumerate() {
        if i>0 { out.push(','); }
        out.push_str("{\"children\":"); ids(&node.kind().children(),&mut out);
        out.push_str(",\"data\":{");
        match node.kind() {
            NodeKind::Int(n)=>{ write!(&mut out,"\"value\":{n}").unwrap(); }
            NodeKind::Bool(b)=>out.push_str(if *b {"\"value\":true"} else {"\"value\":false"}),
            NodeKind::Arg{parameter}=>{ write!(&mut out,"\"parameter\":{parameter}").unwrap(); }
            NodeKind::Use{slot}=>{ write!(&mut out,"\"slot\":{slot}").unwrap(); }
            NodeKind::Call{function,..}=>{ write!(&mut out,"\"function\":{function}").unwrap(); }
            NodeKind::Let{slot,declared,..}=>{
                out.push_str("\"declared\":"); quote(declared.name(),&mut out); write!(&mut out,",\"slot\":{slot}").unwrap();
            }
            NodeKind::Loop{count,index_slot,accumulator_slot,declared,..}=>{
                write!(&mut out,"\"accumulator_slot\":{accumulator_slot},\"count\":{count},\"declared\":").unwrap();
                quote(declared.name(),&mut out); write!(&mut out,",\"index_slot\":{index_slot}").unwrap();
            }
            _=>{},
        }
        write!(&mut out,"}},\"function\":{},\"id\":{},\"op\":",node.function(),node.id()).unwrap();
        quote(node.kind().name(),&mut out); out.push_str(",\"pointer\":"); quote(node.pointer(),&mut out);
        out.push_str(",\"type\":"); quote(node.ty().name(),&mut out); out.push('}');
    }
    out.push_str("],\"program\":");
    // Constructed only after complete checking, so canonical bytes are UTF-8.
    out.push_str(std::str::from_utf8(program.canonical_bytes()).expect("checked canonical UTF-8"));
    out.push_str(",\"program_pin\":"); quote(program.identity(),&mut out);
    out.push_str(",\"schema\":\"bagaev-probe-checked-invocation/1\"}\n");
    out.into_bytes()
}
