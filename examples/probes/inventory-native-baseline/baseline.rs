//! Ordinary imperative batch logic. Shared transport only, no bagaev evaluator.
#[path = "../backend/rust/transport.rs"]
pub mod transport;
use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::io::{Read, Write};
use transport::{Document, JsonString, Value, ValueId};

#[derive(Clone)]
struct Item { sku: String, available: i64 }
#[derive(Clone)]
struct Receipt { stock: Vec<Item>, sku: String, amount: i64 }
enum Outcome {
    Committed { stock: Vec<Item>, receipts: Vec<Receipt> },
    Rejected { stock: Vec<Item>, step: i64, reason: &'static str },
}
fn object(d: &Document, id: ValueId) -> Option<&BTreeMap<JsonString, ValueId>> {
    if let Value::Object(value) = &d.values[id] { Some(value) } else { None }
}
fn keys(value: &BTreeMap<JsonString, ValueId>, names: &[&str]) -> bool {
    value.len() == names.len() && names.iter().all(|name| value.contains_key(&JsonString::from_str(name)))
}
fn field(value: &BTreeMap<JsonString, ValueId>, name: &str) -> Option<ValueId> {
    value.get(&JsonString::from_str(name)).copied()
}
fn text(d: &Document, id: ValueId) -> Option<String> {
    if let Value::String(value) = &d.values[id] { value.scalar_string() } else { None }
}
fn integer(d: &Document, id: ValueId) -> Option<i64> {
    if let Value::Integer(value) = &d.values[id] { value.parse().ok() } else { None }
}
fn array(d: &Document, id: ValueId) -> Option<&[ValueId]> {
    if let Value::Array(value) = &d.values[id] { Some(value) } else { None }
}
fn shape(d: &Document) -> Option<(Vec<Item>, Vec<(String, i64)>)> {
    let root = object(d, d.root)?;
    if !keys(root, &["interface", "stock", "requests"])
        || text(d, field(root, "interface")?)? != "inventory-batch/1" { return None; }
    let raw_stock = array(d, field(root, "stock")?)?;
    let raw_orders = array(d, field(root, "requests")?)?;
    if raw_stock.len() > 16 || raw_orders.len() > 4 { return None; }
    let mut stock = Vec::new();
    for &id in raw_stock {
        let value = object(d, id)?;
        if !keys(value, &["sku", "available"]) { return None; }
        stock.push(Item { sku: text(d, field(value, "sku")?)?, available: integer(d, field(value, "available")?)? });
    }
    let mut orders = Vec::new();
    for &id in raw_orders {
        let value = object(d, id)?;
        if !keys(value, &["sku", "amount"]) { return None; }
        orders.push((text(d, field(value, "sku")?)?, integer(d, field(value, "amount")?)?));
    }
    Some((stock, orders))
}
fn valid_sku(value: &str) -> bool { !value.is_empty() && value.len() <= 32 }
fn valid_stock(stock: &[Item]) -> bool {
    stock.iter().enumerate().all(|(i, item)| item.available >= 0 && valid_sku(&item.sku)
        && stock[..i].iter().all(|other| other.sku != item.sku))
}
fn rejected(stock: &[Item], step: i64, reason: &'static str) -> Outcome {
    Outcome::Rejected { stock: stock.to_vec(), step, reason }
}
fn batch(d: &Document, total10: bool) -> Outcome {
    let Some((original, orders)) = shape(d) else { return rejected(&[], -1, "request-shape"); };
    if orders.is_empty() && !valid_stock(&original) { return rejected(&original, -1, "invalid-stock"); }
    let mut stock = original.clone();
    let mut receipts = Vec::new();
    let mut total = 0_i64;
    let mut stock_validated = false;
    for (step, (sku, amount)) in orders.into_iter().enumerate() {
        let step = step as i64;
        if amount < 1 || !valid_sku(&sku) { return rejected(&original, step, "invalid-request"); }
        if amount > 5 { return rejected(&original, step, "order-limit"); }
        if !stock_validated {
            if !valid_stock(&stock) { return rejected(&original, step, "invalid-stock"); }
            stock_validated = true;
        }
        let Some(index) = stock.iter().position(|item| item.sku == sku) else { return rejected(&original, step, "not-found"); };
        if stock[index].available < amount { return rejected(&original, step, "insufficient-stock"); }
        // At most four positive amounts <=5, so this checked sum cannot exceed20.
        let Some(next_total) = total.checked_add(amount) else { return rejected(&original, step, "batch-limit"); };
        if total10 && next_total > 10 { return rejected(&original, step, "batch-limit"); }
        total = next_total;
        // Positive amount <= nonnegative available, already checked above.
        stock[index].available = stock[index].available.checked_sub(amount).expect("validated subtraction");
        receipts.push(Receipt { stock: stock.clone(), sku, amount });
    }
    Outcome::Committed { stock, receipts }
}
fn quote(value: &str, out: &mut String) {
    out.push('"');
    for c in value.chars() {
        match c {
            '"' => out.push_str("\\\""), '\\' => out.push_str("\\\\"),
            c if c < ' ' => { write!(out, "\\u{:04x}", c as u32).unwrap(); },
            c => out.push(c),
        }
    }
    out.push('"');
}
fn stock_json(stock: &[Item], out: &mut String) {
    out.push('[');
    for (i, item) in stock.iter().enumerate() {
        if i != 0 { out.push(','); }
        write!(out, "{{\"available\":{},\"sku\":", item.available).unwrap();
        quote(&item.sku, out); out.push('}');
    }
    out.push(']');
}
fn render(value: Outcome) -> String {
    let mut out = String::new();
    match value {
        Outcome::Rejected { stock, step, reason } => {
            out.push_str("{\"case\":\"BatchRejected\",\"value\":{\"reason\":"); quote(reason, &mut out);
            write!(out, ",\"step\":{},\"stock\":", step).unwrap(); stock_json(&stock, &mut out); out.push_str("}}");
        },
        Outcome::Committed { stock, receipts } => {
            out.push_str("{\"case\":\"BatchCommitted\",\"value\":{\"receipts\":[");
            for (i, receipt) in receipts.iter().enumerate() {
                if i != 0 { out.push(','); }
                write!(out, "{{\"amount\":{},\"sku\":", receipt.amount).unwrap(); quote(&receipt.sku, &mut out);
                out.push_str(",\"stock\":"); stock_json(&receipt.stock, &mut out); out.push('}');
            }
            out.push_str("],\"stock\":"); stock_json(&stock, &mut out); out.push_str("}}");
        },
    }
    out
}
fn text_profile(value: &JsonString) -> bool { value.scalar_string().is_some_and(|text| text.len() <= 256) }
fn run() -> Result<String, &'static str> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 || !matches!(args[2].as_str(), "original" | "total10") { return Err("BASELINE_USAGE"); }
    let path = std::path::Path::new(&args[1]);
    if !std::fs::symlink_metadata(path).map_err(|_| "BASELINE_IO")?.file_type().is_file() { return Err("BASELINE_INPUT"); }
    let mut raw = Vec::new();
    std::fs::File::open(path).map_err(|_| "BASELINE_IO")?.take((transport::FRAME_LIMIT + 1) as u64).read_to_end(&mut raw).map_err(|_| "BASELINE_IO")?;
    let document = transport::parse(&raw).map_err(|_| "BASELINE_TRANSPORT")?;
    if document.values.iter().any(|value| match value {
        Value::String(text) => !text_profile(text),
        Value::Object(fields) => fields.keys().any(|key| !text_profile(key)),
        _ => false,
    }) { return Err("BASELINE_TEXT_PROFILE"); }
    Ok(render(batch(&document, args[2] == "total10")))
}
fn main() {
    match run() {
        Ok(value) => { if writeln!(std::io::stdout(), "{}", value).is_err() { std::process::exit(2); } },
        Err(error) => { eprintln!("{}", error); std::process::exit(2); },
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn quoting() {
        let mut out = String::new(); quote("\"\\\0é", &mut out);
        assert_eq!(out, "\"\\\"\\\\\\u0000é\"");
    }
    #[test]
    fn lexical_integer_only() {
        for (raw, expected) in [("-0", Some(0)), ("1.0", None), ("1e0", None), ("9223372036854775808", None)] {
            let d = transport::parse(raw.as_bytes()).unwrap(); assert_eq!(integer(&d, d.root), expected);
        }
    }
}
