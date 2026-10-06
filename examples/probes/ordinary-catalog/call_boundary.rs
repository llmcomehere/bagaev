//! One raw-request -> owned application-JSON boundary. Qualification only, no timers.
use crate::{catalog,transport,typed_record,prepared_json_native_v10 as native,native_projection,reference_projection,sha256};
use native::{NativeValue,NativeText,KernelOutput,Cells,Arena};
extern "C"{fn bagaev_json_view10_kernel(v:*const NativeValue,a:*mut Arena,c:*mut Cells,o:*mut KernelOutput);}
const PIN:&str="sha256:c4b7cb8b277e7d5c2e987a18cdb3bbb3ba5b422d9fbee4b98baebb847e5af80c";
const BINDING:[u8;32]=[196,183,203,139,39,126,125,92,46,152,122,24,205,179,187,179,186,91,66,45,159,190,228,185,139,174,187,132,126,90,248,12];
enum Inner{Ordinary,Reference(typed_record::PreparedJsonProgramV10),Native{program:native::Prepared,text:Vec<NativeText>,cells:Vec<NativeValue>}}
pub struct Session{inner:Inner}
impl Session{
 /// Source admission and native workspace allocation happen before calls.
 /// Preparation is data handling; it does not admit the externally linked kernel.
 pub fn new(mode:&str,source:&[u8])->Result<Self,String>{
  let inner=match mode{
   "ordinary"=>Inner::Ordinary,
   "reference"=>{let p=typed_record::prepare_json_program_v10(source)?;if sha256::digest(p.source().canonical_bytes())!=PIN{return Err("source identity".into())};Inner::Reference(p)},
   "native"=>{let p=native::prepare(source).map_err(|e|format!("{e:?}"))?;if sha256::digest(p.source().source().canonical_bytes())!=PIN{return Err("source identity".into())};Inner::Native{program:p,text:vec![NativeText::zero();65536],cells:vec![NativeValue{scalar:0,bytes:std::ptr::null(),len:0,scalars:0};65536]}},
   _=>return Err("mode".into()),
  };Ok(Self{inner})
 }
 /// # Safety
 /// In native mode the linked symbol must be the separately admitted exact own
 /// /10 catalogue kernel, preserve immutable input/scratch bounds, retain no
 /// pointers and never unwind. A source hash alone does not establish this.
 pub unsafe fn call(&mut self,raw_request:&[u8])->Result<Vec<u8>,String>{
  if raw_request.len()>1048576{return Err("raw request bound".into())}
  let response=match &mut self.inner{
   Inner::Ordinary=>{let d=transport::parse(raw_request).map_err(|e|format!("transport:{e:?}"))?;catalog::evaluate(&d)},
   Inner::Reference(program)=>{
    let mut args=Vec::with_capacity(raw_request.len()+2);args.push(b'[');args.extend_from_slice(raw_request);args.push(b']');
    let invocation=typed_record::prepare_json_arguments_v10(program,&args)?;let out=typed_record::evaluate_prepared_json_v10(&invocation).map_err(str::to_owned)?;
    reference_projection::project(&out).map_err(|e|format!("projection:{e:?}"))?
   },
   Inner::Native{program,text,cells}=>{
    let mut args=Vec::with_capacity(raw_request.len()+2);args.push(b'[');args.extend_from_slice(raw_request);args.push(b']');
    let out=unsafe{native::evaluate(program,&args,text,cells,&BINDING,bagaev_json_view10_kernel)}.map_err(|e|format!("native:{e:?}"))?;
    native_projection::project(&out.bytes,&BINDING).map_err(|e|format!("projection:{e:?}"))?
   },
  };
  Ok(catalog::encode(&response))
 }
}
