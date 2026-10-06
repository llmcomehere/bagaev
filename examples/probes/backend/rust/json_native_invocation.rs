//! Full-envelope immutable Json input bridge, not execution admission.
use crate::{typed_record::CheckedJsonInvocation,json_native_input::{self,Owned,Error}};
pub fn prepare(invocation:&CheckedJsonInvocation)->Result<Owned,Error>{
 let documents=invocation.json_arguments().iter().map(|x|x.document()).collect::<Vec<_>>();
 json_native_input::encode_admitted(&documents)
}
