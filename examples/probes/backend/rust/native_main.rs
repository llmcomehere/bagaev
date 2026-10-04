//! Explicit-file caller, statically linked to exactly one fixed kernel object.
#[cfg(not(test))] pub mod transport;
#[cfg(not(test))] pub mod check;
#[cfg(not(test))] pub mod ir;
#[cfg(not(test))] pub mod canonical;
#[cfg(not(test))] pub mod sha256;
#[cfg(not(test))] pub mod native;
#[cfg(test)] use crate::{native,transport};

use std::ffi::{OsStr,OsString};
use std::fs::{self,File,OpenOptions};
use std::io::{self,Read,Write};
use std::path::{Component,Path,PathBuf};

#[cfg(all(not(test),not(all(target_arch="x86_64",target_os="linux",target_endian="little"))))]
compile_error!("fixed probe caller requires little-endian x86_64 Linux");

const USAGE: &str = "usage: probe-native invoke --input INVOCATION_FILE --witness /out/WITNESS_FILE --prefill 00|ff";
#[derive(Debug)]
pub struct Paths { pub input:PathBuf,pub witness:PathBuf,pub prefill:native::Prefill }

pub fn parse_arguments(args: &[OsString]) -> Result<Paths,&'static str> {
    if args.len()!=7 || args[0]!="invoke" || args[1]!="--input" || args[3]!="--witness"
        || args[5]!="--prefill" || args[2].is_empty() || args[4].is_empty() { return Err(USAGE); }
    let input=PathBuf::from(&args[2]); let witness=PathBuf::from(&args[4]);
    let prefill=if args[6]=="00" { native::Prefill::Zero }
        else if args[6]=="ff" { native::Prefill::Ones } else { return Err(USAGE); };
    if input==Path::new("-") || !output_path(&witness) { return Err(USAGE); }
    Ok(Paths {input,witness,prefill})
}

pub fn output_path(path: &Path) -> bool {
    if !path.is_absolute() { return false; }
    let mut parts=path.components();
    if parts.next()!=Some(Component::RootDir) || parts.next()!=Some(Component::Normal(OsStr::new("out"))) { return false; }
    let rest:Vec<_>=parts.collect();
    !rest.is_empty() && rest.iter().all(|part|matches!(part,Component::Normal(_)))
}

/// No input write. Exactly the frame cap plus at most one overrun byte is read.
/// Path/ancestor immutability is an external prerequisite; these std operations
/// and metadata comparisons do not certify hostile-host stability or whole-file
/// before/after identity. Oversize bytes go to the frontend's IR_BOUNDS priority.
pub fn read_frame(path: &Path) -> io::Result<Vec<u8>> {
    if !fs::symlink_metadata(path)?.file_type().is_file() { return Err(io::Error::new(io::ErrorKind::InvalidInput,"input must be regular")); }
    let mut file=File::open(path)?; let before=file.metadata()?;
    if !before.is_file() { return Err(io::Error::new(io::ErrorKind::InvalidInput,"input must be regular")); }
    let mut bytes=Vec::new(); let mut buffer=[0u8;8192];
    let limit=transport::FRAME_LIMIT+1;
    while bytes.len()<limit {
        let amount=(limit-bytes.len()).min(buffer.len());
        let n=match file.read(&mut buffer[..amount]) {
            Err(error) if error.kind()==io::ErrorKind::Interrupted=>continue,
            other=>other?,
        };
        if n==0 { break; } bytes.extend_from_slice(&buffer[..n]);
    }
    if bytes.len()<=transport::FRAME_LIMIT {
        let after=file.metadata()?;
        if before.len()!=bytes.len() as u64 || before.len()!=after.len()
            || before.modified().ok()!=after.modified().ok() {
            return Err(io::Error::new(io::ErrorKind::InvalidData,"input changed during read"));
        }
    }
    Ok(bytes)
}

pub fn write_complete(writer: &mut impl Write, bytes: &[u8]) -> io::Result<()> {
    writer.write_all(bytes)?; writer.flush()
}

pub fn write_new(path: &Path, bytes: &[u8]) -> io::Result<()> {
    if !output_path(path) || bytes.len()>native::WITNESS_LIMIT { return Err(io::Error::new(io::ErrorKind::InvalidInput,"invalid witness destination or size")); }
    let parent=path.parent().ok_or_else(||io::Error::new(io::ErrorKind::InvalidInput,"missing witness parent"))?;
    let resolved=fs::canonicalize(parent)?;
    if resolved!=parent || !resolved.starts_with("/out") { return Err(io::Error::new(io::ErrorKind::InvalidInput,"witness parent must be direct and owned")); }
    let mut file=OpenOptions::new().write(true).create_new(true).open(path)?;
    if !file.metadata()?.is_file() { return Err(io::Error::new(io::ErrorKind::InvalidInput,"witness must be regular")); }
    // Failures retain any new partial evidence; no overwrite, delete or retry.
    write_complete(&mut file,bytes)?; file.sync_all()
}

/// A language result becomes stdout only AFTER complete witness write/flush/sync.
pub fn publish(observation: &native::Observation, path: &Path, stdout: &mut impl Write) -> io::Result<()> {
    write_new(path,observation.witness_bytes())?;
    write_complete(stdout,observation.result_bytes())
}

// No real object references or calls are compiled into the source-test harness.
// The library's bound type/decoder support synthetic bytes only in those tests.
#[cfg(not(test))]
mod fixed {
    use super::native;
    use std::ffi::c_void;
    unsafe extern "C" {
        fn bagaev_probe_entry(arguments: *const i64, output: *mut c_void);
        static bagaev_probe_binding: u8;
        static bagaev_probe_binding_length: u64;
    }

    /// SAFETY prerequisite from external artifact admission: these named data
    /// symbols are the producer's immutable globals, length is initialized u64
    /// at an aligned address, binding occupies that many readable bytes in ONE
    /// allocation, remains immutable/live for the whole process, and corresponds
    /// to the fixed entry object. Numeric checks cannot prove any of those facts.
    fn binding() -> Result<&'static [u8],native::Error> {
        // addr_of! creates no reference to an extern static. Read only after the
        // external region/alignment admission; check numeric length before slice.
        let length=unsafe { std::ptr::addr_of!(bagaev_probe_binding_length).read() };
        if length==0 || length>native::BINDING_LIMIT as u64 || length>isize::MAX as u64 { return Err(native::Error::Binding); }
        let pointer=unsafe { std::ptr::addr_of!(bagaev_probe_binding) };
        // SAFETY: externally admitted actual region/lifetime as above. u8
        // alignment is1, pointer is non-null, positive length <=isize::MAX.
        Ok(unsafe { std::slice::from_raw_parts(pointer,length as usize) })
    }

    pub fn observe(bytes: &[u8], prefill: native::Prefill) -> Result<native::Observation,native::Error> {
        let invocation=match native::check_frame(bytes,prefill)? {
            native::Checked::Refusal(observation)=>return Ok(observation),
            native::Checked::Invocation(invocation)=>invocation,
        };
        // Static/argument checking precedes even the foreign global read.
        let bound=native::bind(invocation,binding()?)?;
        let (mut arguments,mut output)=bound.regions(prefill);
        let before=*arguments.bytes();
        let input_pointer=arguments.as_mut_ptr().cast::<i64>().cast_const();
        let output_pointer=output.as_mut_ptr().cast::<c_void>();
        // SAFETY: repr(C,align(8)) separate caller-owned objects have64/32 live
        // initialized bytes, disjoint storage, typed LE slots, zero unused slots.
        // No shared region borrow survives this call. Admitted C object returns
        // without unwinding, retaining pointers, out-of-bounds writes or concurrent
        // accesses. In-bounds accidental input mutation is captured and rejected.
        // No native fault/trap can be recovered into a language observation.
        unsafe { bagaev_probe_entry(input_pointer,output_pointer); }
        let capture=native::Capture { before,after:*arguments.bytes(),output:*output.bytes() };
        native::decode(&bound,capture,prefill)
    }
}

#[cfg(not(test))]
pub fn run_with(args: &[OsString], stdout: &mut impl Write) -> Result<(),&'static str> {
    let paths=parse_arguments(args)?;
    let bytes=read_frame(&paths.input).map_err(|_|"unable to read complete regular input")?;
    let observation=fixed::observe(&bytes,paths.prefill).map_err(|_|"unable to complete bound native observation")?;
    publish(&observation,&paths.witness,stdout).map_err(|_|"unable to complete witness and result output")
}

#[cfg(not(test))]
fn main() {
    let args:Vec<_>=std::env::args_os().skip(1).collect();
    if let Err(message)=run_with(&args,&mut io::stdout().lock()) {
        let _=writeln!(io::stderr().lock(),"{message}"); std::process::exit(1);
    }
}
