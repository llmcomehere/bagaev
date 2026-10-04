//! Bounded stdin-to-stdout object driver. No linking or artifact execution.
use std::io::{self,Read,Write};
use bagaev_cranelift_probe::{check,canonical,lower,transport};
fn run()->Result<(),String>{
    let args:Vec<_>=std::env::args().skip(1).collect();
    if args.len()!=2 || args[0]!="emit-object" {return Err("usage: bagaev-cranelift-probe emit-object none|speed|speed_and_size".into());}
    let mode=match args[1].as_str(){"none"=>lower::Mode::None,"speed"=>lower::Mode::Speed,"speed_and_size"=>lower::Mode::Size,_=>return Err("unsupported optimization mode".into())};
    let mut input=Vec::new();io::stdin().lock().take((transport::FRAME_LIMIT+1) as u64).read_to_end(&mut input).map_err(|e|e.to_string())?;
    let program=match check::check_program_bytes(&input){
        Ok(p)=>p,
        Err(check::FrontendError::Refusal(e))=>return Err(String::from_utf8(canonical::refusal_bytes(&e)).map_err(|e|e.to_string())?),
        Err(check::FrontendError::Environment(_))=>return Err("checking environment unavailable".into()),
    };
    let object=lower::object(&program,mode)?;
    io::stdout().lock().write_all(&object).map_err(|e|e.to_string())?;Ok(())
}
fn main(){if let Err(e)=run(){eprintln!("{e}");std::process::exit(1)}}
