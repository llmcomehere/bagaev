//! Data-only component-outcome-source CLI; no evaluation or execution admission.
pub mod transport;pub mod check;pub mod ir;pub mod canonical;pub mod sha256;
pub mod record_ir;pub mod record_value;pub mod int_projection;pub mod type_graph;
pub mod json_view;pub mod option_int;pub mod text_value;pub mod text_inspection;
pub mod text_list;pub mod typed_record;pub mod component_outcome_source;
use std::io::{Read,Write};
fn read(path:&std::ffi::OsStr)->Result<Vec<u8>,&'static str>{let file=std::fs::File::open(path).map_err(|_|"input open")?;if !file.metadata().map_err(|_|"input metadata")?.is_file(){return Err("input must be regular");}let mut bytes=Vec::new();file.take((transport::FRAME_LIMIT+1)as u64).read_to_end(&mut bytes).map_err(|_|"input read")?;Ok(bytes)}
fn main(){let a:Vec<_>=std::env::args_os().skip(1).collect();let r=(||->Result<(),&'static str>{if !(a.len()==2&&a[0]=="check"||a.len()==3&&a[0]=="policy"){return Err("usage: component-outcome-source check SOURCE | policy SOURCE POLICY");}let source=read(&a[1])?;let policy=if a.len()==3{Some(read(&a[2])?)}else{None};let out=component_outcome_source::process(&source,policy.as_deref())?;let mut stdout=std::io::stdout().lock();stdout.write_all(&out).map_err(|_|"output write")?;stdout.flush().map_err(|_|"output flush")?;Ok(())})();if let Err(e)=r{let _=writeln!(std::io::stderr(),"{e}");std::process::exit(1);}}
