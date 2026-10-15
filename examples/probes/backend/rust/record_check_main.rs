//! Explicit source-only typed-record/11 semantic checking CLI. Never evaluates.
pub mod transport;
pub mod check;
pub mod ir;
pub mod canonical;
pub mod sha256;
pub mod record_ir;
pub mod record_value;
pub mod int_projection;
pub mod type_graph;
pub mod json_view;
pub mod option_int;
pub mod text_value;
pub mod text_inspection;
pub mod text_list;
pub mod typed_record;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::Path;

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

fn main(){
    let args:Vec<_>=std::env::args_os().skip(1).collect();
    let result=(||->Result<(),&'static str>{
        let (profile,path)=if args.len()==3 && args[0]=="check" && args[1]=="--input" && !args[2].is_empty(){
            (11,&args[2])
        }else if args.len()==5 && args[0]=="check" && args[1]=="--profile" && args[2]=="12" && args[3]=="--input" && !args[4].is_empty(){
            (12,&args[4])
        }else{return Err("usage: record-check check --input FILE");};
        let bytes=frame(Path::new(path)).map_err(|_|"unable to read complete input")?;
        let checked=if profile==12{typed_record::check_source_v12(&bytes)?}else{typed_record::check_source_v11(&bytes)?};
        let schema=if profile==12{"bagaev-record-source-check/12"}else{"bagaev-record-source-check/11"};
        let mut out=String::from("{\"execution_admission\":false,\"input_sha256\":");
        if bytes.len()<=transport::FRAME_LIMIT {
            let input_identity=sha256::digest(&bytes);
            canonical::quote(input_identity.strip_prefix("sha256:").ok_or("input identity format")?,&mut out);
        } else { out.push_str("null"); }
        out.push_str(",\"location\":");
        match checked {
            typed_record::SourceCheck::Checked(source)=>{
                out.push_str("null,\"program_sha256\":");
                let identity=source.identity().strip_prefix("sha256:").ok_or("source identity format")?;
                canonical::quote(identity,&mut out);
                out.push_str(",\"reason\":null,\"schema\":");
                canonical::quote(schema,&mut out);
                out.push_str(",\"status\":\"checked\"}\n");
            },
            typed_record::SourceCheck::Refused{reason,location}=>{
                canonical::quote(&location,&mut out);
                out.push_str(",\"program_sha256\":null,\"reason\":");
                canonical::quote(reason,&mut out);
                out.push_str(",\"schema\":");
                canonical::quote(schema,&mut out);
                out.push_str(",\"status\":\"refused\"}\n");
            },
        }
        let mut stdout=io::stdout().lock();stdout.write_all(out.as_bytes()).map_err(|_|"output write")?;stdout.flush().map_err(|_|"output flush")?;Ok(())
    })();
    if let Err(e)=result{let _=writeln!(io::stderr().lock(),"{e}");std::process::exit(1);}
}
