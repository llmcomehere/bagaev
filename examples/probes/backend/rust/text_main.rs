//! Explicit bounded typed-Text reference CLI.
pub mod transport;
pub mod check;
pub mod ir;
pub mod canonical;
pub mod sha256;
pub mod text_ir;
pub mod text_value;
pub mod typed_text;
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
        if args.len()!=3 || args[0]!="run" || args[1]!="--input" || args[2].is_empty(){return Err("usage: typed-text run --input FILE");}
        let bytes=frame(Path::new(&args[2])).map_err(|_|"unable to read complete input")?;
        let out=typed_text::process(&bytes)?;let mut stdout=io::stdout().lock();stdout.write_all(&out).map_err(|_|"output write")?;stdout.flush().map_err(|_|"output flush")?;Ok(())
    })();
    if let Err(e)=result{let _=writeln!(io::stderr().lock(),"{e}");std::process::exit(1);}
}
