//! Separate explicit-file LLVM emitter CLI. No evaluation or toolchain invocation.
#[cfg(not(test))] pub mod transport;
#[cfg(not(test))] pub mod check;
#[cfg(not(test))] pub mod ir;
#[cfg(not(test))] pub mod canonical;
#[cfg(not(test))] pub mod sha256;
#[cfg(not(test))] pub mod llvm;

#[cfg(test)] use crate::{canonical, check, llvm, transport};
use std::ffi::OsString;
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Write};
use std::path::{Component, Path, PathBuf};

const USAGE: &str = "usage: probe-llvm emit-program --input PROGRAM_FILE --output /out/MODULE_FILE";

#[derive(Debug)]
pub struct Paths { pub input: PathBuf, pub output: PathBuf }

/// Pure argument validation. No defaults, stdin, relative output or parent traversal.
pub fn parse_arguments(args: &[OsString]) -> Result<Paths, &'static str> {
    if args.len()!=5 || args[0]!="emit-program" || args[1]!="--input" || args[3]!="--output"
        || args[2].is_empty() || args[4].is_empty()
    { return Err(USAGE); }
    let input=PathBuf::from(&args[2]); let output=PathBuf::from(&args[4]);
    if input==Path::new("-") || !output_path(&output) { return Err(USAGE); }
    Ok(Paths{input,output})
}

pub fn output_path(path: &Path) -> bool {
    if !path.is_absolute() { return false; }
    let mut components=path.components();
    if components.next()!=Some(Component::RootDir)
        || components.next()!=Some(Component::Normal(std::ffi::OsStr::new("out")))
    { return false; }
    let rest:Vec<_>=components.collect();
    !rest.is_empty() && rest.iter().all(|part|matches!(part,Component::Normal(_)))
}

/// Input and ancestor directories are externally admitted immutable resources.
/// Checking both pathname and opened descriptor rejects ordinary special files;
/// std-only pathname operations do not provide a hostile-host race boundary.
pub fn read_frame(path: &Path) -> io::Result<Vec<u8>> {
    if !fs::symlink_metadata(path)?.file_type().is_file() {
        return Err(io::Error::new(io::ErrorKind::InvalidInput,"input must be a regular file"));
    }
    let mut input=File::open(path)?;
    let before=input.metadata()?;
    if !before.is_file() {
        return Err(io::Error::new(io::ErrorKind::InvalidInput,"input must be a regular file"));
    }
    let mut bytes=Vec::new(); let mut buffer=[0u8;8192];
    let limit=transport::FRAME_LIMIT+1;
    while bytes.len()<limit {
        let count=(limit-bytes.len()).min(buffer.len());
        let n=match input.read(&mut buffer[..count]) {
            Err(error) if error.kind()==io::ErrorKind::Interrupted=>continue,
            other=>other?,
        };
        if n==0 { break; }
        bytes.extend_from_slice(&buffer[..n]);
    }
    if bytes.len()<=transport::FRAME_LIMIT {
        let after=input.metadata()?;
        if before.len()!=bytes.len() as u64 || before.len()!=after.len()
            || before.modified().ok()!=after.modified().ok()
        { return Err(io::Error::new(io::ErrorKind::InvalidData,"input changed during read")); }
    }
    Ok(bytes)
}

#[derive(Debug)]
pub enum Prepared { Module(llvm::Module), Refusal(Vec<u8>) }

/// Whole-program checking completes before any output path is opened.
pub fn prepare(bytes: &[u8]) -> Result<Prepared, &'static str> {
    match check::check_program_bytes(bytes) {
        Ok(program)=>llvm::emit_program(&program).map(Prepared::Module)
            .map_err(|_|"unable to construct bounded LLVM module"),
        Err(check::FrontendError::Refusal(error))=>Ok(Prepared::Refusal(canonical::refusal_bytes(&error))),
        Err(check::FrontendError::Environment(_))=>Err("unable to check complete program"),
    }
}

pub fn write_complete(writer: &mut impl Write, bytes: &[u8]) -> io::Result<()> {
    writer.write_all(bytes)?; writer.flush()
}

pub fn write_new(path: &Path, bytes: &[u8]) -> io::Result<()> {
    if !output_path(path) {
        return Err(io::Error::new(io::ErrorKind::InvalidInput,"output must be under /out"));
    }
    let parent=path.parent().ok_or_else(||io::Error::new(io::ErrorKind::InvalidInput,"missing parent"))?;
    // No creation/discovery of ancestors; no resolving an alias to another tree.
    // Admission must keep this owned parent stable until the command terminates.
    let resolved=fs::canonicalize(parent)?;
    if resolved!=parent || !resolved.starts_with("/out") {
        return Err(io::Error::new(io::ErrorKind::InvalidInput,"output parent must be direct and owned"));
    }
    let mut file=OpenOptions::new().write(true).create_new(true).open(path)?;
    if !file.metadata()?.is_file() {
        return Err(io::Error::new(io::ErrorKind::InvalidInput,"output must be a regular file"));
    }
    // An I/O error may leave a new partial file. It is retained as unadmitted
    // evidence; this command never removes/replaces it or emits success metadata.
    write_complete(&mut file,bytes)?; file.sync_all()
}

pub fn run_with(args: &[OsString], stdout: &mut impl Write) -> Result<(), &'static str> {
    let paths=parse_arguments(args)?;
    let bytes=read_frame(&paths.input).map_err(|_|"unable to read complete regular input file")?;
    match prepare(&bytes)? {
        Prepared::Refusal(bytes)=>write_complete(stdout,&bytes).map_err(|_|"unable to complete refusal output"),
        Prepared::Module(module)=>{
            write_new(&paths.output,module.bytes()).map_err(|_|"unable to create complete new module file")?;
            write_complete(stdout,module.binding_bytes()).map_err(|_|"unable to complete binding output")
        }
    }
}

#[cfg(not(test))]
fn main() {
    let args:Vec<_>=std::env::args_os().skip(1).collect();
    if let Err(message)=run_with(&args,&mut io::stdout().lock()) {
        let _=writeln!(io::stderr().lock(),"{message}");
        std::process::exit(1);
    }
}
