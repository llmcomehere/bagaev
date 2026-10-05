//! Checked Text source to detached canonical LLVM data. No execution or file writes.
use crate::{canonical,text_llvm,typed_text};
pub const ENVELOPE_LIMIT: usize=64*1024*1024;
pub fn process(bytes:&[u8])->Result<Vec<u8>,&'static str>{
    let p=match typed_text::check_source(bytes)? {
        typed_text::SourceCheck::Checked(p)=>p,
        typed_text::SourceCheck::Refused{reason,location}=>{
            let mut out=String::from("{\"kind\":\"refusal\",\"location\":");
            canonical::quote(&location,&mut out);out.push_str(",\"reason\":");canonical::quote(reason,&mut out);
            out.push_str(",\"schema\":\"bagaev-typed-text-llvm/1\"}\n");return Ok(out.into_bytes());
        }
    };
    let module=text_llvm::emit_program(&p).map_err(|_|"Text LLVM emission failure")?;
    let llvm=std::str::from_utf8(module.bytes()).map_err(|_|"Text LLVM encoding")?;
    let record=std::str::from_utf8(module.binding_bytes()).map_err(|_|"Text LLVM record encoding")?;
    let record=record.strip_suffix('\n').ok_or("Text LLVM record terminator")?;
    let mut out=String::from("{\"execution_admission\":false,\"kind\":\"module\",\"llvm_ir\":");
    canonical::quote(llvm,&mut out);out.push_str(",\"module_record\":");out.push_str(record);
    out.push_str(",\"schema\":\"bagaev-typed-text-llvm/1\",\"source_pin\":");canonical::quote(p.identity(),&mut out);out.push_str("}\n");
    if out.len()>ENVELOPE_LIMIT{return Err("Text LLVM envelope bound");}Ok(out.into_bytes())
}
