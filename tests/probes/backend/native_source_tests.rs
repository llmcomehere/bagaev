//! Authored source tests only; no real linked object, expected-vector input or
//! LLVM emission. Compilation, execution and conformance require later admission.
#[path = "../../../examples/probes/backend/rust/transport.rs"] pub mod transport;
#[path = "../../../examples/probes/backend/rust/check.rs"] pub mod check;
#[path = "../../../examples/probes/backend/rust/ir.rs"] pub mod ir;
#[path = "../../../examples/probes/backend/rust/canonical.rs"] pub mod canonical;
#[path = "../../../examples/probes/backend/rust/sha256.rs"] pub mod sha256;
#[path = "../../../examples/probes/backend/rust/native.rs"] pub mod native;
#[path = "../../../examples/probes/backend/rust/native_main.rs"] pub mod native_cli;

#[cfg(test)]
mod tests {
    use crate::{check,native,native_cli,transport};
    use std::ffi::OsString;
    use std::io::{self,Write};
    use std::path::Path;
    use transport::{Document,JsonString,Value,ValueId};
    use native::{Capture,Error,Prefill};

    fn program(body: &str, result: &str, params: &str) -> String {
        format!(r#"{{"schema":"bagaev-probe-ir/1","entry":"kernel","functions":{{"kernel":{{"params":{params},"result":"{result}","body":{body}}}}}}}"#)
    }
    fn invocation(program: &str, args: &str) -> Vec<u8> {
        format!(r#"{{"schema":"bagaev-probe-invocation/1","program":{program},"arguments":{args}}}"#).into_bytes()
    }
    fn bind(program: &str, args: &str) -> native::BoundInvocation {
        let checked=check::check_invocation_bytes(&invocation(program,args)).unwrap();
        let descriptor=native::expected_binding(checked.program()).unwrap();
        native::bind(checked,&descriptor).unwrap()
    }
    fn field(doc: &Document, id: ValueId, key: &str) -> ValueId {
        match &doc.values[id] { Value::Object(map)=>map[&JsonString::from_str(key)],_=>panic!("object") }
    }
    fn text(doc: &Document, id: ValueId) -> String {
        match &doc.values[id] { Value::String(s)=>s.scalar_string().unwrap(),_=>panic!("string") }
    }
    fn integer(doc: &Document, id: ValueId) -> i64 {
        match &doc.values[id] { Value::Integer(n)=>n.parse().unwrap(),_=>panic!("integer") }
    }
    fn unhex(value: &str) -> Vec<u8> {
        assert_eq!(value.len()%2,0);
        value.as_bytes().chunks_exact(2).map(|pair| {
            u8::from_str_radix(std::str::from_utf8(pair).unwrap(),16).unwrap()
        }).collect()
    }
    fn output(status:u32,ty:u32,value:i64,work:u64,reason:u32,location:u32) -> [u8;32] {
        let mut bytes=[0u8;32];
        bytes[0..4].copy_from_slice(&status.to_le_bytes());
        bytes[4..8].copy_from_slice(&ty.to_le_bytes());
        bytes[8..16].copy_from_slice(&value.to_le_bytes());
        bytes[16..24].copy_from_slice(&work.to_le_bytes());
        bytes[24..28].copy_from_slice(&reason.to_le_bytes());
        bytes[28..32].copy_from_slice(&location.to_le_bytes()); bytes
    }
    fn capture(bound: &native::BoundInvocation, output: [u8;32], prefill: Prefill) -> Capture {
        let (args,_)=bound.regions(prefill);
        Capture { before:*args.bytes(),after:*args.bytes(),output }
    }
    fn result(observation: &native::Observation) -> Document {
        transport::parse(observation.result_bytes()).unwrap()
    }
    fn assert_witness(observation: &native::Observation, count:i64, prefill:Prefill) {
        let doc=transport::parse(observation.witness_bytes()).unwrap();
        assert_eq!(text(&doc,field(&doc,doc.root,"schema")),"bagaev-probe-native-witness/1");
        assert_eq!(integer(&doc,field(&doc,doc.root,"entry_call_count")),count);
        assert_eq!(text(&doc,field(&doc,doc.root,"prefill")),prefill.name());
        let wire=unhex(&text(&doc,field(&doc,doc.root,"result_wire_hex")));
        assert_eq!(wire,observation.result_bytes());
        assert_eq!(integer(&doc,field(&doc,doc.root,"result_wire_bytes")),wire.len() as i64);
        for name in ["input_before_hex","input_after_hex","output_hex"] {
            let value=field(&doc,doc.root,name);
            if count==0 { assert!(matches!(doc.values[value],Value::Null)); }
            else { assert_eq!(unhex(&text(&doc,value)).len(),if name=="output_hex" {32} else {64}); }
        }
        assert_eq!(observation.result_bytes().last(),Some(&b'\n'));
        assert_eq!(observation.witness_bytes().last(),Some(&b'\n'));
    }

    #[test]
    fn descriptor_is_complete_canonical_data_not_hash_only() {
        let raw=r#"{"schema":"bagaev-probe-ir/1","entry":"alpha","functions":{"zeta":{"params":[],"result":"Bool","body":["bool",false]},"alpha":{"params":[["flag","Bool"]],"result":"Int64","body":["let","saved","Int64",["int",71],["if",["arg","flag"],["use","saved"],["int",73]]]}}}"#;
        let checked=check::check_program_bytes(raw.as_bytes()).unwrap();
        let bytes=native::expected_binding(&checked).unwrap();
        let s=std::str::from_utf8(&bytes).unwrap();
        assert!(s.contains(r#""cpu":"x86-64","entry":0,"functions":[{"body":1,"callees":[],"index":0,"locals":[{"name":"saved","slot":0,"type":"Int64"}]"#));
        assert!(s.contains(r#""name":"flag","slot":0,"type":"Bool""#));
        assert!(s.contains(r#""name":"zeta","parameters":[],"result":"Bool""#));
        assert!(s.contains(r#""pointer":"/functions/zeta/body","type":"Bool""#));
        assert!(s.contains(r#""children":[2,3],"function":0,"id":1,"op":"let""#));
        assert!(s.contains(std::str::from_utf8(checked.canonical_bytes()).unwrap()));
        assert!(s.contains(checked.identity()));
        assert!(s.starts_with(r#"{"abi":{"alignment":8,"argument_bytes":64,"argument_location_base":2147483649"#));
        assert!(s.ends_with(r#""target":"x86_64-unknown-linux-gnu","work_limit":65536}"#));
        assert!(!bytes.ends_with(b"\n"));
        assert!(bytes.len()<=native::BINDING_LIMIT);
        // Alter full-map/ABI/source information while leaving the program pin
        // intact; every mismatch must fail before any bound invocation exists.
        for (old,new) in [
            ("\"alignment\":8","\"alignment\":4"),
            ("x86-64","native"),("21.1","22.1"),
            ("system-C","other-C"),("uint64","int64"),
            ("/functions/zeta/body","/functions/other/body"),
            ("\"children\":[2,3]","\"children\":[3,2]"),
            ("\"slot\":0,\"type\":\"Bool\"","\"slot\":1,\"type\":\"Bool\""),
            ("\"bool\",false","\"bool\",true"),
        ] {
            assert!(s.contains(old)); let altered=s.replacen(old,new,1);
            let checked=check::check_invocation_bytes(&invocation(raw,"[true]")).unwrap();
            assert!(matches!(native::bind(checked,altered.as_bytes()),Err(Error::Binding)));
        }
        for suffix in [b"\n".as_slice(),b"\0".as_slice(),b" ".as_slice()] {
            let mut altered=bytes.clone(); altered.extend_from_slice(suffix);
            let checked=check::check_invocation_bytes(&invocation(raw,"[true]")).unwrap();
            assert!(matches!(native::bind(checked,&altered),Err(Error::Binding)));
        }
    }

    #[test]
    fn whole512_node_map_includes_unused_functions_and_last_location() {
        fn tree(depth: usize) -> String {
            if depth==0 { r#"["int",79]"#.to_owned() }
            else { format!(r#"["add",{},{}]"#,tree(depth-1),tree(depth-1)) }
        }
        let mut functions=Vec::new();
        for i in 0..8 {
            let mut body=tree(5); //63 nodes/function; four binders add2 each.
            if i<4 { body=format!(r#"["let","saved","Int64",["int",0],{body}]"#); }
            functions.push(format!(r#""a{i}":{{"params":[],"result":"Int64","body":{body}}}"#));
        }
        let raw=format!(r#"{{"schema":"bagaev-probe-ir/1","entry":"a0","functions":{{{}}}}}"#,functions.join(","));
        let bound=bind(&raw,"[]"); assert_eq!(bound.program().nodes().len(),512);
        let expected=native::expected_binding(bound.program()).unwrap();
        let doc=transport::parse(&expected).unwrap();
        match &doc.values[field(&doc,doc.root,"nodes")] { Value::Array(a)=>assert_eq!(a.len(),512),_=>panic!("nodes") }
        let observation=native::decode(&bound,capture(&bound,output(1,0,0,65536,9,512),Prefill::Zero),Prefill::Zero).unwrap();
        let doc=result(&observation);
        assert_eq!(text(&doc,field(&doc,doc.root,"location")),format!("/program{}",bound.program().node(512).unwrap().pointer()));
    }

    #[test]
    fn wrong_valid_program_cannot_bind_and_static_priorities_need_no_entry() {
        let a=program(r#"["int",83]"#,"Int64","[]");
        let b=program(r#"["int",89]"#,"Int64","[]");
        let descriptor=native::expected_binding(&check::check_program_bytes(a.as_bytes()).unwrap()).unwrap();
        let checked=check::check_invocation_bytes(&invocation(&b,"[]")).unwrap();
        assert!(matches!(native::bind(checked,&descriptor),Err(Error::Binding)));
        for (bytes,reason,location) in [
            (vec![b' ';transport::FRAME_LIMIT+1],"IR_BOUNDS",""),
            (b"{".to_vec(),"IR_JSON",""),
            (b"{}".to_vec(),"IR_SHAPE",""),
            (br#"{"schema":"wrong","program":{},"arguments":null}"#.to_vec(),"IR_VERSION","/schema"),
            (invocation("{}","null"),"IR_SHAPE","/program"),
            (invocation(&a,"[true]"),"IR_ARGUMENT","/arguments"),
        ] {
            // This path has no foreign function/object reference at all.
            let observation=match native::check_frame(&bytes,Prefill::Ones).unwrap() {
                native::Checked::Refusal(o)=>o,_=>panic!("static refusal"),
            };
            let doc=result(&observation);
            assert_eq!(text(&doc,field(&doc,doc.root,"reason")),reason);
            assert_eq!(text(&doc,field(&doc,doc.root,"location")),location);
            assert_witness(&observation,0,Prefill::Ones);
        }
        let p=program(r#"["arg","x"]"#,"Int64",r#"[["x","Int64"]]"#);
        let observation=match native::check_frame(&invocation(&p,"[false]"),Prefill::Zero).unwrap() {
            native::Checked::Refusal(o)=>o,_=>panic!("bad argument"),
        };
        let doc=result(&observation);
        assert_eq!(text(&doc,field(&doc,doc.root,"location")),"/arguments/0");
    }

    #[test]
    fn long_pointer_refusal_preserves_every_wire_byte_within8mib() {
        let p=program(r#"["int",97]"#,"Int64","[]");
        let key="/~\\\"".repeat(6000); let mut quoted=String::new();
        crate::canonical::quote(&key,&mut quoted);
        let nested=format!("{}0{}","[".repeat(133),"]".repeat(133));
        let arguments=format!("{{{quoted}:{nested}}}");
        let bytes=invocation(&p,&arguments); assert!(bytes.len()<transport::FRAME_LIMIT);
        let observation=match native::check_frame(&bytes,Prefill::Zero).unwrap() {
            native::Checked::Refusal(o)=>o,_=>panic!("bounds"),
        };
        assert!(observation.result_bytes().len()>16384);
        assert!(observation.witness_bytes().len()<native::WITNESS_LIMIT);
        assert_witness(&observation,0,Prefill::Zero);
        let doc=result(&observation);
        assert_eq!(text(&doc,field(&doc,doc.root,"reason")),"IR_BOUNDS");
        assert!(text(&doc,field(&doc,doc.root,"location")).starts_with("/arguments/~1~0"));
    }

    #[test]
    fn aligned_regions_encode_all_slots_zero_unused_and_exact_prefill() {
        let p=program(r#"["arg","x"]"#,"Int64",r#"[["x","Int64"],["flag","Bool"]]"#);
        let bound=bind(&p,"[-9223372036854775808,true]");
        for prefill in [Prefill::Zero,Prefill::Ones] {
            let (mut arguments,mut out)=bound.regions(prefill);
            assert_eq!(std::mem::size_of::<native::Arguments>(),64);
            assert_eq!(std::mem::size_of::<native::Output>(),32);
            assert_eq!(std::mem::align_of::<native::Arguments>(),8);
            assert_eq!(std::mem::align_of::<native::Output>(),8);
            assert_eq!(&arguments.bytes()[0..8],&i64::MIN.to_le_bytes());
            assert_eq!(&arguments.bytes()[8..16],&1i64.to_le_bytes());
            assert!(arguments.bytes()[16..].iter().all(|&b|b==0));
            assert_eq!(*out.bytes(),[prefill.byte();32]);
            let a=arguments.as_mut_ptr() as usize; let b=out.as_mut_ptr() as usize;
            assert_eq!(a%8,0); assert_eq!(b%8,0);
            assert!(a+64<=b || b+32<=a);
            let observation=native::decode(&bound,capture(&bound,output(0,1,i64::MIN,0,0,0),prefill),prefill).unwrap();
            assert_witness(&observation,1,prefill);
        }
    }

    #[test]
    fn complete_abi_observations_preserve_wrong_but_well_formed_results() {
        let p=program(r#"["int",101]"#,"Int64","[]"); let bound=bind(&p,"[]");
        // Different value/work, overflow at a literal, and invalid-ir despite
        // legal inputs are well-formed observations, not evaluator predictions.
        for (bytes,status,reason,location) in [
            (output(0,1,i64::MAX,65536,0,0),"success",None,None),
            (output(1,0,0,0,9,1),"integer-overflow",Some("IR_OVERFLOW"),Some("/program/functions/kernel/body")),
            (output(2,0,0,65536,10,1),"work-limit",Some("IR_WORK"),Some("/program/functions/kernel/body")),
            (output(3,0,0,0,8,0x80000008),"invalid-ir",Some("IR_ARGUMENT"),Some("/arguments/7")),
        ] {
            let observation=native::decode(&bound,capture(&bound,bytes,Prefill::Ones),Prefill::Ones).unwrap();
            let doc=result(&observation);
            assert_eq!(text(&doc,field(&doc,doc.root,"status")),status);
            for (key,value) in [("reason",reason),("location",location)] {
                let id=field(&doc,doc.root,key);
                match value { Some(value)=>assert_eq!(text(&doc,id),value),None=>assert!(matches!(doc.values[id],Value::Null)) }
            }
            if status!="success" {
                assert!(matches!(doc.values[field(&doc,doc.root,"value")],Value::Null));
                assert!(matches!(doc.values[field(&doc,doc.root,"value_type")],Value::Null));
            }
            match &doc.values[doc.root] { Value::Object(map)=>assert_eq!(map.len(),7),_=>panic!("result") }
            assert_witness(&observation,1,Prefill::Ones);
        }
        for i in 0..8 {
            let observation=native::decode(&bound,capture(&bound,output(3,0,0,0,8,0x80000001+i),Prefill::Zero),Prefill::Zero).unwrap();
            let doc=result(&observation);
            assert_eq!(text(&doc,field(&doc,doc.root,"location")),format!("/arguments/{i}"));
            assert_witness(&observation,1,Prefill::Zero);
        }
        let p=program(r#"["bool",false]"#,"Bool","[]"); let bound=bind(&p,"[]");
        for value in [0,1] {
            let observation=native::decode(&bound,capture(&bound,output(0,2,value,1,0,0),Prefill::Zero),Prefill::Zero).unwrap();
            let doc=result(&observation);
            assert!(matches!(doc.values[field(&doc,doc.root,"value")],Value::Bool(b) if b==(value==1)));
            assert_eq!(text(&doc,field(&doc,doc.root,"value_type")),"Bool");
        }
    }

    #[test]
    fn malformed_abi_and_input_mutation_are_environment_failures() {
        let p=program(r#"["int",103]"#,"Int64","[]"); let bound=bind(&p,"[]");
        for bytes in [
            output(4,0,0,0,0,0),output(0,0,0,1,0,0),output(0,2,1,1,0,0),
            output(0,1,0,1,1,0),output(0,1,0,1,0,1),output(0,1,0,65537,0,0),
            output(1,1,0,1,9,1),output(1,0,1,1,9,1),output(1,0,0,1,10,1),
            output(1,0,0,1,9,0),output(1,0,0,1,9,2),output(1,0,0,1,9,65537),
            output(2,0,0,65535,10,1),output(2,0,0,65536,9,1),
            output(3,0,0,0,8,0x80000000),output(3,0,0,0,8,0x80000009),
            output(3,0,0,1,8,0x80000001),output(3,0,0,0,7,0x80000001),
            [255u8;32],
        ] {
            assert!(matches!(native::decode(&bound,capture(&bound,bytes,Prefill::Zero),Prefill::Zero),Err(Error::Encoding)));
        }
        let mut altered=capture(&bound,output(0,1,103,1,0,0),Prefill::Zero);
        altered.after[63]=1;
        assert!(matches!(native::decode(&bound,altered,Prefill::Zero),Err(Error::InputMutation)));
        let mut fabricated=capture(&bound,output(0,1,103,1,0,0),Prefill::Zero);
        fabricated.before[63]=1; fabricated.after[63]=1;
        assert!(matches!(native::decode(&bound,fabricated,Prefill::Zero),Err(Error::InputMutation)));
        let p=program(r#"["bool",true]"#,"Bool","[]"); let bound=bind(&p,"[]");
        assert!(matches!(native::decode(&bound,capture(&bound,output(0,2,2,1,0,0),Prefill::Zero),Prefill::Zero),Err(Error::Encoding)));
    }

    fn args(input: &str,witness: &str,prefill: &str) -> Vec<OsString> {
        ["invoke","--input",input,"--witness",witness,"--prefill",prefill].iter().map(|s|OsString::from(*s)).collect()
    }
    #[test]
    fn exact_cli_and_write_failures_have_no_language_result() {
        assert_eq!(native_cli::parse_arguments(&args("invocation.json","/out/new.json","ff")).unwrap().prefill,Prefill::Ones);
        for a in [args("-","/out/new","00"),args("","/out/new","00"),args("in","out/new","00"),
            args("in","/out","00"),args("in","/out/../new","00"),args("in","/outside/new","00"),args("in","/out/new","0")] {
            assert!(native_cli::parse_arguments(&a).is_err());
        }
        let mut a=args("in","/out/new","00"); a.push("extra".into()); assert!(native_cli::parse_arguments(&a).is_err());
        let mut a=args("in","/out/new","00"); a.swap(1,3); assert!(native_cli::parse_arguments(&a).is_err());
        struct Failure { flush:bool }
        impl Write for Failure {
            fn write(&mut self,bytes: &[u8]) -> io::Result<usize> {
                if self.flush { Ok(bytes.len()) } else { Err(io::Error::new(io::ErrorKind::BrokenPipe,"synthetic write")) }
            }
            fn flush(&mut self) -> io::Result<()> { Err(io::Error::new(io::ErrorKind::BrokenPipe,"synthetic flush")) }
        }
        assert!(native_cli::write_complete(&mut Failure{flush:false},b"wire\n").is_err());
        assert!(native_cli::write_complete(&mut Failure{flush:true},b"wire\n").is_err());
        let observation=match native::check_frame(b"{}",Prefill::Zero).unwrap() {native::Checked::Refusal(o)=>o,_=>panic!("refusal")};
        let mut stdout=Vec::new();
        assert!(native_cli::publish(&observation,Path::new("relative"),&mut stdout).is_err());
        assert!(stdout.is_empty());
    }

    #[test]
    fn explicit_frame_reader_keeps_overrun_witness_and_rejects_special_file() {
        // Future test execution owns only this create_new temporary input;
        // no /out witness, native symbol, subprocess or source execution here.
        let path=std::env::temp_dir().join(format!("probe-native-source-frame-{}",std::process::id()));
        let bytes=vec![b' ';transport::FRAME_LIMIT+23];
        let mut file=std::fs::OpenOptions::new().write(true).create_new(true).open(&path).unwrap();
        file.write_all(&bytes).unwrap(); file.sync_all().unwrap(); drop(file);
        let read=native_cli::read_frame(&path).unwrap();
        assert_eq!(read.len(),transport::FRAME_LIMIT+1);
        std::fs::remove_file(&path).unwrap();
        assert!(native_cli::read_frame(Path::new("/dev/null")).is_err());
    }
}
