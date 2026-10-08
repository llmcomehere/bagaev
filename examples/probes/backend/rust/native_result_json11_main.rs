//! Data-only source-pinned native success wire to JSON CLI. No code dispatch.
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


pub mod composite_result_decode_v11;
pub mod native_result_json_v11;
use std::{collections::BTreeMap,io::{Read,Write},path::Path};
const USAGE:&str="native_result_json11 --source FILE --source-pin sha256:HEX --wire FILE\nData-only success projection. Does not execute source or native code.\n";
fn read_file(path:&str,limit:usize,reason:&'static str)->Result<Vec<u8>,&'static str>{
 let path=Path::new(path);let meta=std::fs::symlink_metadata(path).map_err(|_|reason)?;
 if !meta.file_type().is_file()||meta.len()>limit as u64{return Err(reason);}
 let file=std::fs::File::open(path).map_err(|_|reason)?;if !file.metadata().map_err(|_|reason)?.is_file(){return Err(reason);}
 let mut bytes=Vec::new();file.take(limit as u64+1).read_to_end(&mut bytes).map_err(|_|reason)?;
 if bytes.len()>limit{return Err(reason);}Ok(bytes)
}
fn run(args:&[String])->Result<Vec<u8>,&'static str>{
 if args==["--help"]{return Ok(USAGE.as_bytes().to_vec());}
 if args.len()!=6{return Err("ARGUMENTS");}
 let mut flags=BTreeMap::new();for pair in args.chunks_exact(2){
  if !matches!(pair[0].as_str(),"--source"|"--source-pin"|"--wire")||flags.insert(pair[0].as_str(),pair[1].as_str()).is_some(){return Err("ARGUMENTS");}
 }
 if flags.len()!=3{return Err("ARGUMENTS");}let pin=flags["--source-pin"];
 let hex=pin.strip_prefix("sha256:").ok_or("SOURCE_PIN_FORMAT")?;
 if hex.len()!=64||!hex.bytes().all(|x|x.is_ascii_digit()||(b'a'..=b'f').contains(&x)){return Err("SOURCE_PIN_FORMAT");}
 let source=read_file(flags["--source"],1048576,"SOURCE_FILE")?;
 let prepared=typed_record::prepare_json_program_v11(&source).map_err(|_|"SOURCE_ADMISSION")?;
 if prepared.source().identity()!=pin{return Err("SOURCE_PIN_MISMATCH");}drop(prepared);
 let wire=read_file(flags["--wire"],4325440,"WIRE_FILE")?;
 let mut output=native_result_json_v11::decode_success(&source,&wire).map_err(|_|"RESULT_REFUSED")?;output.push(b'\n');Ok(output)
}
fn main(){
 let args:Vec<_>=std::env::args().skip(1).collect();match run(&args){
  Ok(output)=>if std::io::stdout().write_all(&output).is_err(){std::process::exit(2);},
  Err(reason)=>{eprintln!("{{\"status\":\"refused\",\"reason\":\"{}\"}}",reason);std::process::exit(2);}
 }
}
