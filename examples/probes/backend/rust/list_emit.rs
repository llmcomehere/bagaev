//! Checked Text-list source to detached canonical LLVM data. No execution or file writes.
use crate::{canonical,list_llvm,typed_list};
pub const ENVELOPE_LIMIT: usize=64*1024*1024;
pub fn process(bytes:&[u8])->Result<Vec<u8>,&'static str>{
    let p=match typed_list::check_source(bytes)? {
        typed_list::SourceCheck::Checked(p)=>p,
        typed_list::SourceCheck::Refused{reason,location}=>{
            let mut out=String::from("{\"kind\":\"refusal\",\"location\":");
            canonical::quote(&location,&mut out);out.push_str(",\"reason\":");canonical::quote(reason,&mut out);
            out.push_str(",\"schema\":\"bagaev-typed-list-llvm/1\"}\n");return Ok(out.into_bytes());
        }
    };
    let module=list_llvm::emit_program(&p).map_err(|_|"List LLVM emission failure")?;
    let llvm=std::str::from_utf8(module.bytes()).map_err(|_|"List LLVM encoding")?;
    let record=std::str::from_utf8(module.binding_bytes()).map_err(|_|"List LLVM record encoding")?;
    let record=record.strip_suffix('\n').ok_or("List LLVM record terminator")?;
    let mut out=String::from("{\"execution_admission\":false,\"kind\":\"module\",\"llvm_ir\":");
    canonical::quote(llvm,&mut out);out.push_str(",\"module_record\":");out.push_str(record);
    out.push_str(",\"schema\":\"bagaev-typed-list-llvm/1\",\"source_pin\":");canonical::quote(p.identity(),&mut out);out.push_str("}\n");
    if out.len()>ENVELOPE_LIMIT{return Err("List LLVM envelope bound");}Ok(out.into_bytes())
}
