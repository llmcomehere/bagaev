//! Explicit read-only inferred-source CLI. No native execution or subprocess.
pub mod transport;
pub mod check;
pub mod ir;
pub mod canonical;
pub mod sha256;
pub mod typed_source;

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

fn run() -> Result<(), &'static str> {
    let args:Vec<_>=std::env::args_os().skip(1).collect();
    const USAGE:&str="usage: typed-source check-source --input FILE | project-node --input FILE --lowered-pin PIN --node U16";
    let projection=if args.len()==3 && args[0]=="check-source" && args[1]=="--input" && !args[2].is_empty() {
        None
    } else if args.len()==7 && args[0]=="project-node" && args[1]=="--input" && !args[2].is_empty()
        && args[3]=="--lowered-pin" && args[5]=="--node" {
        let pin=args[4].to_str().ok_or(USAGE)?;
        let text=args[6].to_str().ok_or(USAGE)?;let node=text.parse::<u16>().map_err(|_|USAGE)?;
        if node.to_string()!=text {return Err(USAGE);}
        Some((pin,node))
    } else {return Err(USAGE);};
    let bytes=frame(Path::new(&args[2])).map_err(|_|"unable to read complete input file")?;
    let output=match projection {
        None=>typed_source::process(&bytes),
        Some((pin,node))=>typed_source::project_node(&bytes,pin,node),
    }.map_err(|_|"unable to construct detached typed result")?;
    let mut stdout=io::stdout().lock();
    stdout.write_all(&output).map_err(|_|"unable to complete output")?;
    stdout.flush().map_err(|_|"unable to complete output")?;
    Ok(())
}

fn main() {
    if let Err(message)=run() {
        let _=writeln!(io::stderr().lock(),"{message}");
        std::process::exit(1);
    }
}
