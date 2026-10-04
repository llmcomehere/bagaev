//! Explicit read-only file CLI. No evaluation, lowering, compiler or subprocess.
pub mod transport;
pub mod check;
pub mod ir;
pub mod canonical;
pub mod sha256;

use std::fs::File;
use std::io::{self, Read, Write};
use std::path::Path;
use check::FrontendError;

fn frame(path: &Path) -> io::Result<Vec<u8>> {
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
    if args.len()!=3 || args[0]!="check-invocation" || args[1]!="--input" || args[2].is_empty() {
        return Err("usage: probe-front check-invocation --input FILE");
    }
    let bytes=frame(Path::new(&args[2])).map_err(|_|"unable to read complete input file")?;
    let output=match check::check_invocation_bytes(&bytes) {
        Ok(invocation)=>canonical::invocation_bytes(&invocation),
        Err(FrontendError::Refusal(error))=>canonical::refusal_bytes(&error),
        Err(FrontendError::Environment(_))=>return Err("unable to construct checked artifact"),
    };
    // An intermediate artifact has its own output cap, never an IR refusal.
    if output.len()>4*1024*1024 { return Err("checked artifact output bound exceeded"); }
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
