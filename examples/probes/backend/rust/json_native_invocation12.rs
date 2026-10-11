//! Explicit /12 immutable Boolean-preserving input bridge; not execution admission.
use crate::{typed_record::CheckedJsonInvocation,json_native_input12::{self,Owned,Error}};
pub fn prepare(invocation:&CheckedJsonInvocation)->Result<Owned,Error>{
 if invocation.program().profile()!=12{return Err(Error("JSON_PROFILE"));}
 let documents=invocation.json_arguments().iter().map(|x|x.document()).collect::<Vec<_>>();
 json_native_input12::encode_admitted(&documents)
}
