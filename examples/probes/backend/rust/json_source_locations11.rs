//! Inspect checked /11 node locations only. Never evaluates, compiles or invokes a kernel.
pub mod transport;
pub mod check;
pub mod ir;
pub mod canonical;
pub mod sha256;
pub mod record_ir;
pub mod option_int;
pub mod text_value;
pub mod text_list;
pub mod typed_record;
pub mod text_inspection;
pub mod int_projection;
pub mod record_value;
pub mod type_graph;
pub mod json_view;

use std::fs::File;use std::io::{self,Read,Write};use std::path::Path;
fn frame(path: &Path) -> io::Result<Vec<u8>> {
    if !std::fs::symlink_metadata(path)?.file_type().is_file() {
        return Err(io::Error::new(io::ErrorKind::InvalidInput,"input must be regular"));
    }
    let mut input=File::open(path)?;
    let before=input.metadata()?;
    if !before.is_file() {
        return Err(io::Error::new(io::ErrorKind::InvalidInput,"input must be a regular file"));
    }
    let mut bytes=Vec::new(); let mut buffer=[0u8;8192];
    let witness_limit=transport::FRAME_LIMIT+1;
    while bytes.len()<witness_limit {
        let count=(witness_limit-bytes.len()).min(buffer.len());
        let n=match input.read(&mut buffer[..count]) {
            Err(e) if e.kind()==io::ErrorKind::Interrupted=>continue,
            other=>other?,
        };
        if n==0 { break; }
        bytes.extend_from_slice(&buffer[..n]);
    }
    if bytes.len()<=transport::FRAME_LIMIT {
        let after=input.metadata()?;
        if before.len()!=bytes.len() as u64 || before.len()!=after.len()
            || before.modified().ok()!=after.modified().ok()
        {
            return Err(io::Error::new(io::ErrorKind::InvalidData,"input changed during read"));
        }
    }
    Ok(bytes)
}


fn node_json(program: &typed_record::CheckedSource, node: &record_ir::Node, out: &mut String) -> Result<(), String> {
    use std::fmt::Write as _;
    let function = program.functions().get(node.function()).ok_or("LOCATION_FUNCTION")?;
    write!(out, "{{\"id\":{},\"function\":", node.id()).map_err(|_| "LOCATION_OUTPUT")?;
    canonical::quote(function.name(), out);
    out.push_str(",\"program_pointer\":");
    canonical::quote(&format!("/program{}", node.pointer()), out);
    out.push_str(",\"operation\":");
    canonical::quote(node.kind().name(), out);
    out.push_str(",\"type_category\":");
    canonical::quote(node.ty().name(), out);
    out.push('}');
    Ok(())
}

/// Checked data inspection only. A source digest does not authenticate native output.
pub fn report(bytes: &[u8], expected_pin: &str, selected: Option<u16>) -> Result<Vec<u8>, String> {
    use std::fmt::Write as _;
    let invocation = typed_record::checked_json_invocation_v11(bytes)?;
    let program = invocation.program();
    if program.identity() != expected_pin { return Err("LOCATION_SOURCE_PIN".to_owned()); }
    if let Some(id) = selected {
        if program.node(id).is_none() { return Err("LOCATION_NODE".to_owned()); }
    }
    let mut out = String::from("{\"schema\":\"bagaev-native-source-locations/1\",\"profile\":\"bagaev-typed-record/11\",\"source_pin\":");
    canonical::quote(program.identity(), &mut out);
    write!(out, ",\"node_count\":{},\"locations\":[", program.nodes().len()).map_err(|_| "LOCATION_OUTPUT")?;
    let mut first = true;
    for node in program.nodes() {
        if selected.is_some() && selected != Some(node.id()) { continue; }
        if !first { out.push(','); }
        first = false;
        node_json(program, node, &mut out)?;
        if out.len() > transport::FRAME_LIMIT { return Err("LOCATION_OUTPUT_BOUND".to_owned()); }
    }
    out.push_str("],\"semantic_check\":true,\"program_executed\":false,\"native_output_authenticated\":false,\"execution_admission\":false}\n");
    if out.len() > transport::FRAME_LIMIT { return Err("LOCATION_OUTPUT_BOUND".to_owned()); }
    Ok(out.into_bytes())
}

fn main() {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    let result = (|| -> Result<(), String> {
        let all = args.len() == 5 && args[0] == "locations";
        let one = args.len() == 7 && args[0] == "locate" && args[5] == "--node";
        if !(all || one) || args[1] != "--input" || args[2].is_empty() || args[3] != "--source-pin" {
            return Err("usage: json-source-locations (locations|locate) --input FILE --source-pin PIN [--node ID]".to_owned());
        }
        let pin = args[4].to_str().ok_or("LOCATION_SOURCE_PIN")?;
        let selected = if one { Some(args[6].to_str().ok_or("LOCATION_NODE")?.parse::<u16>().map_err(|_| "LOCATION_NODE")?) } else { None };
        let bytes = frame(Path::new(&args[2])).map_err(|_| "LOCATION_INPUT")?;
        let output = report(&bytes, pin, selected)?;
        let mut stdout = io::stdout().lock();
        stdout.write_all(&output).map_err(|_| "LOCATION_WRITE")?;
        stdout.flush().map_err(|_| "LOCATION_WRITE")?;
        Ok(())
    })();
    if let Err(error) = result {
        let _ = writeln!(io::stderr().lock(), "{error}");
        std::process::exit(1);
    }
}
