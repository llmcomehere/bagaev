//! Source-only tests authored from the contracts, without conformance vector input.
//! Compiling/running these tests or any generated LLVM requires separate admission.
#[path = "../../../examples/probes/backend/rust/transport.rs"] pub mod transport;
#[path = "../../../examples/probes/backend/rust/check.rs"] pub mod check;
#[path = "../../../examples/probes/backend/rust/ir.rs"] pub mod ir;
#[path = "../../../examples/probes/backend/rust/canonical.rs"] pub mod canonical;
#[path = "../../../examples/probes/backend/rust/sha256.rs"] pub mod sha256;
#[path = "../../../examples/probes/backend/rust/llvm.rs"] pub mod llvm;
#[path = "../../../examples/probes/backend/rust/llvm_main.rs"] pub mod llvm_cli;

#[cfg(test)]
mod tests {
    use crate::{check, ir, llvm, llvm_cli, sha256, transport};
    use std::ffi::OsString;
    use std::io::{self, Write};
    use std::path::Path;
    use transport::{Document, JsonString, Value, ValueId};

    fn source(body: &str, ty: &str, params: &str) -> String {
        format!(r#"{{"schema":"bagaev-probe-ir/1","entry":"kernel","functions":{{"kernel":{{"params":{params},"result":"{ty}","body":{body}}}}}}}"#)
    }
    fn emit(source: &str) -> (ir::CheckedProgram, llvm::Module) {
        let checked=check::check_program_bytes(source.as_bytes()).unwrap();
        let module=llvm::emit_program(&checked).unwrap(); (checked,module)
    }
    fn field(doc: &Document, object: ValueId, key: &str) -> ValueId {
        match &doc.values[object] {
            Value::Object(map)=>map[&JsonString::from_str(key)],_=>panic!("object"),
        }
    }
    fn text(doc: &Document, id: ValueId) -> String {
        match &doc.values[id] { Value::String(s)=>s.scalar_string().unwrap(),_=>panic!("string") }
    }
    fn array(doc: &Document, id: ValueId) -> &[ValueId] {
        match &doc.values[id] { Value::Array(a)=>a,_=>panic!("array") }
    }
    fn number(doc: &Document, id: ValueId) -> usize {
        match &doc.values[id] { Value::Integer(n)=>n.parse().unwrap(),_=>panic!("integer") }
    }
    fn module_text(module: &llvm::Module) -> &str { std::str::from_utf8(module.bytes()).unwrap() }

    #[test]
    fn all_fifteen_forms_lower_without_evaluating_them() {
        let forms=[
            (r#"["int",-73]"#,"Int64","int"),
            (r#"["bool",true]"#,"Bool","bool"),
            (r#"["arg","input"]"#,"Int64","arg"),
            (r#"["add",["int",7],["int",13]]"#,"Int64","add"),
            (r#"["sub",["int",7],["int",13]]"#,"Int64","sub"),
            (r#"["mul",["int",7],["int",13]]"#,"Int64","mul"),
            (r#"["eq",["bool",true],["bool",false]]"#,"Bool","eq"),
            (r#"["lt",["int",7],["int",13]]"#,"Bool","lt"),
            (r#"["le",["int",7],["int",13]]"#,"Bool","le"),
            (r#"["not",["bool",false]]"#,"Bool","not"),
            (r#"["let","saved","Int64",["int",73],["use","saved"]]"#,"Int64","let"),
            (r#"["if",["bool",false],["int",73],["int",79]]"#,"Int64","if"),
            (r#"["loop",19,"index","sum","Int64",["int",3],["add",["use","sum"],["use","index"]]]"#,"Int64","loop"),
        ];
        let mut seen=std::collections::BTreeSet::new();
        for (body,ty,op) in forms {
            let params=if op=="arg" {r#"[["input","Int64"]]"#} else {"[]"};
            let (checked,module)=emit(&source(body,ty,params));
            for node in checked.nodes() { seen.insert(node.kind().name()); }
            assert!(module.bytes().len()<llvm::MODULE_LIMIT);
            assert!(module_text(&module).contains("define ccc void @bagaev_probe_entry"));
        }
        let dag=r#"{"schema":"bagaev-probe-ir/1","entry":"caller","functions":{"unused":{"params":[],"result":"Bool","body":["bool",false]},"callee":{"params":[["flag","Bool"]],"result":"Bool","body":["arg","flag"]},"caller":{"params":[],"result":"Bool","body":["call","callee",["bool",true]]}}}"#;
        let (checked,module)=emit(dag);
        for node in checked.nodes() { seen.insert(node.kind().name()); }
        assert_eq!(seen.len(),15);
        assert!(module_text(&module).contains("call i64 @probe_fn0(ptr %work, ptr %status, ptr %location"));
        assert!(module_text(&module).contains("define internal i64 @probe_fn2("));
    }

    #[test]
    fn identity_maps_bind_the_whole_program_and_exact_module_bytes() {
        let raw=r#"{"schema":"bagaev-probe-ir/1","entry":"alpha","functions":{"zeta":{"params":[],"result":"Int64","body":["int",85]},"alpha":{"params":[["switch","Bool"]],"result":"Int64","body":["if",["arg","switch"],["int",83],["int",89]]}}}"#;
        let (checked,module)=emit(raw); let second=llvm::emit_program(&checked).unwrap();
        assert_eq!(module.bytes(),second.bytes()); assert_eq!(module.binding_bytes(),second.binding_bytes());
        assert_eq!(module.identity(),sha256::digest(module.bytes()));
        let doc=transport::parse(module.binding_bytes()).unwrap();
        assert_eq!(text(&doc,field(&doc,doc.root,"schema")),"bagaev-probe-llvm-module/1");
        assert_eq!(text(&doc,field(&doc,doc.root,"artifact_pin")),module.identity());
        assert_eq!(number(&doc,field(&doc,doc.root,"module_bytes")),module.bytes().len());
        let binding=field(&doc,doc.root,"binding");
        assert_eq!(text(&doc,field(&doc,binding,"program_pin")),checked.identity());
        assert_eq!(number(&doc,field(&doc,binding,"entry")),checked.entry());
        let nodes=array(&doc,field(&doc,binding,"nodes")); assert_eq!(nodes.len(),checked.nodes().len());
        for (mapped,node) in nodes.iter().zip(checked.nodes()) {
            assert_eq!(number(&doc,field(&doc,*mapped,"id")),usize::from(node.id()));
            assert_eq!(number(&doc,field(&doc,*mapped,"function")),node.function());
            assert_eq!(text(&doc,field(&doc,*mapped,"pointer")),node.pointer());
            assert_eq!(text(&doc,field(&doc,*mapped,"type")),node.ty().name());
            let source_marker=format!("; node {}\n",node.id());
            assert_eq!(module_text(&module).matches(&source_marker).count(),1);
        }
        // Decode only the embedded descriptor bytes, never a serialized checked IR.
        let text_module=module_text(&module);
        let begin=text_module.find(" x i8] c\"").unwrap()+" x i8] c\"".len();
        let end=text_module[begin..].find('"').unwrap()+begin;
        let encoded=&text_module[begin..end]; assert_eq!(encoded.len()%3,0);
        let mut description=Vec::new();
        for chunk in encoded.as_bytes().chunks_exact(3) {
            assert_eq!(chunk[0],b'\\');
            description.push(u8::from_str_radix(std::str::from_utf8(&chunk[1..]).unwrap(),16).unwrap());
        }
        assert_eq!(text(&doc,field(&doc,doc.root,"binding_pin")),sha256::digest(&description));
        let embedded=transport::parse(&description).unwrap();
        assert_eq!(text(&embedded,field(&embedded,embedded.root,"program_pin")),checked.identity());
        let changed=raw.replace("85","87"); let (_,different)=emit(&changed);
        assert_ne!(module.identity(),different.identity());
    }

    #[test]
    fn overflow_and_work_failures_have_explicit_checked_paths() {
        let body=r#"["add",["sub",["int",-9223372036854775808],["int",23]],["mul",["int",9223372036854775807],["int",29]]]"#;
        let (checked,module)=emit(&source(body,"Int64","[]")); let text=module_text(&module);
        for name in ["sadd","ssub","smul"] {
            assert!(text.contains(&format!("call {{ i64, i1 }} @llvm.{name}.with.overflow.i64")));
        }
        for node in checked.nodes() {
            assert!(text.contains(&format!("store volatile i32 {}, ptr %location, align 4",node.id())));
        }
        assert_eq!(text.matches("icmp uge i64").count(),checked.nodes().len());
        assert!(text.contains("65536")); assert!(text.contains("store volatile i32 1, ptr %status"));
        assert!(text.contains("store volatile i32 2, ptr %status"));
        for forbidden in [" nsw "," nuw "," inbounds ","@llvm.trap"," poison"," undef"," sdiv "," shl "] {
            assert!(!text.contains(forbidden));
        }
    }

    #[test]
    fn lazy_paths_zero_and_max_loops_remain_control_flow() {
        for count in [0,1024] {
            let body=format!(r#"["loop",{count},"index","acc","Bool",["bool",true],["if",["use","acc"],["not",["use","acc"]],["eq",["use","index"],["int",31]]]]"#);
            let (checked,module)=emit(&source(&body,"Bool","[]")); let text=module_text(&module);
            assert!(text.contains("phi i64")); assert!(text.contains("icmp ult i64"));
            assert!(text.contains(&format!(", {count}\n")));
            assert_eq!(text.matches("icmp uge i64").count(),checked.nodes().len());
            // Locals are allocated at entry; loop backedges do not allocate.
            assert_eq!(text.matches("alloca i64, align 8").count(),3);
        }
    }

    #[test]
    fn abi_reads_eight_slots_and_writes_exact_fields_on_every_result() {
        let (_,module)=emit(&source(r#"["arg","flag"]"#,"Bool",r#"[["first","Int64"],["flag","Bool"]]"#));
        let text=module_text(&module);
        let entry=&text[text.find("define ccc void @bagaev_probe_entry").unwrap()..];
        assert_eq!(entry.matches("load volatile i64, ptr %input").count(),8);
        assert!(entry.find("%arg7 = load volatile").unwrap()<entry.find("call void @probe_write").unwrap());
        assert!(!entry.contains("%valid0")); assert!(entry.contains("icmp ule i64 %arg1, 1"));
        let mut previous=0;
        for i in 1..8 {
            let position=entry.find(&format!("%valid{i} =")).unwrap(); assert!(position>previous); previous=position;
            assert!(entry.contains(&format!("i32 {})",2147483649u32+i as u32)));
        }
        for (offset,ty,align) in [(0,"i32",4),(4,"i32",4),(8,"i64",8),(16,"i64",8),(24,"i32",4),(28,"i32",4)] {
            assert!(text.contains(&format!("getelementptr i8, ptr %out, i64 {offset}")));
            assert!(text.contains(&format!("ptr %o{offset}, align {align}")));
            assert!(text.contains(&format!("store volatile {ty}")));
        }
        assert!(text.contains("i32 0, i32 2, i64 %result"));
        assert!(text.contains("i32 %final_status, i32 0, i64 0, i64 %final_work"));
    }

    #[test]
    fn bounded_generation_never_returns_a_partial_module() {
        let checked=check::check_program_bytes(source(r#"["int",41]"#,"Int64","[]").as_bytes()).unwrap();
        for (module,binding) in [(0,llvm::BINDING_LIMIT),(llvm::MODULE_LIMIT,0),(17,17)] {
            assert!(matches!(llvm::emit_with_limits(&checked,module,binding),Err(llvm::EmitError::Bound)));
        }
    }

    #[test]
    fn all_active_slots_and_nested_disjoint_scopes_keep_their_namespaces() {
        let mut params=String::from("[");
        for i in 0..8 {
            if i>0 { params.push(','); }
            params.push_str(&format!(r#"["p{i}","Bool"]"#));
        }
        params.push(']');
        let body=r#"["if",["arg","p7"],["let","temp","Bool",["arg","p0"],["use","temp"]],["let","temp","Bool",["arg","p1"],["use","temp"]]]"#;
        let (checked,module)=emit(&source(body,"Bool",&params));
        assert_eq!(checked.functions()[0].locals().len(),2);
        let text=module_text(&module); assert!(text.contains("%local0 = alloca"));
        assert!(text.contains("%local1 = alloca"));
        for i in 0..8 { assert!(text.contains(&format!("icmp ule i64 %arg{i}, 1"))); }
        let body=r#"["loop",7,"outer","acc","Int64",["int",53],["loop",5,"inner","sum","Int64",["use","acc"],["add",["use","outer"],["use","inner"]]]]"#;
        let (checked,module)=emit(&source(body,"Int64","[]"));
        assert_eq!(checked.functions()[0].locals().len(),4);
        assert_eq!(module_text(&module).matches("icmp ult i64").count(),2);
        let int_params=params.replace("Bool","Int64");
        let (_,module)=emit(&source(r#"["arg","p6"]"#,"Int64",&int_params));
        let text=module_text(&module);
        let entry=&text[text.find("define ccc void @bagaev_probe_entry").unwrap()..];
        assert!(!entry.contains("%valid"));
        assert_eq!(entry.matches("load volatile i64, ptr %input").count(),8);
    }

    #[test]
    fn direct_calls_check_failure_before_later_caller_work() {
        let raw=r#"{"schema":"bagaev-probe-ir/1","entry":"a","functions":{"a":{"params":[],"result":"Int64","body":["add",["call","b",["int",59]],["int",61]]},"b":{"params":[["n","Int64"]],"result":"Int64","body":["arg","n"]}}}"#;
        let (checked,module)=emit(raw); let text=module_text(&module);
        let begin=text.find("define internal i64 @probe_fn0(").unwrap();
        let end=text[begin..].find("define internal i64 @probe_fn1(").unwrap()+begin;
        let caller=&text[begin..end];
        let call=caller.find("call i64 @probe_fn1(").unwrap();
        let continuation=&caller[call..];
        let failure_check=continuation.find("load volatile i32, ptr %status").unwrap();
        let right=match checked.node(1).unwrap().kind() {
            ir::NodeKind::Binary{right,..}=>*right,_=>panic!("binary root"),
        };
        assert!(failure_check<continuation.find(&format!("; node {right}\n")).unwrap());
        assert!(continuation.contains("label %failed"));
    }

    fn args(input: &str, output: &str) -> Vec<OsString> {
        ["emit-program","--input",input,"--output",output].map(OsString::from).to_vec()
    }
    #[test]
    fn explicit_cli_shape_and_output_domain_have_no_fallback() {
        assert!(llvm_cli::parse_arguments(&args("/source/program.json","/out/kernel.ll")).is_ok());
        for path in ["kernel.ll","/out","/outside/kernel.ll","/out/../kernel.ll","/out/sub/../../kernel.ll"] {
            assert!(!llvm_cli::output_path(Path::new(path)));
            assert!(llvm_cli::parse_arguments(&args("/source/program.json",path)).is_err());
        }
        assert!(llvm_cli::parse_arguments(&[]).is_err());
        assert!(llvm_cli::parse_arguments(&args("-","/out/kernel.ll")).is_err());
        let mut wrong=args("/source/program.json","/out/kernel.ll"); wrong.push(OsString::from("--force"));
        assert!(llvm_cli::parse_arguments(&wrong).is_err());
        wrong.pop(); wrong[0]=OsString::from("run-program");
        assert!(llvm_cli::parse_arguments(&wrong).is_err());
    }

    #[test]
    fn malformed_and_unused_invalid_programs_prepare_refusal_without_module() {
        let unused=r#"{"schema":"bagaev-probe-ir/1","entry":"a","functions":{"a":{"params":[],"result":"Int64","body":["int",43]},"z":{"params":[],"result":"Bool","body":["not",["int",47]]}}}"#;
        for bytes in [b"{}".as_slice(),b"{} null",unused.as_bytes()] {
            let refusal=match llvm_cli::prepare(bytes).unwrap() {
                llvm_cli::Prepared::Refusal(bytes)=>bytes,_=>panic!("no module for invalid IR"),
            };
            let doc=transport::parse(&refusal).unwrap();
            assert_eq!(text(&doc,field(&doc,doc.root,"schema")),"bagaev-probe-result/1");
            assert_eq!(text(&doc,field(&doc,doc.root,"status")),"invalid-ir");
            assert_eq!(number(&doc,field(&doc,doc.root,"work")),0);
        }
    }

    struct FailedWriter { flush_failure: bool }
    impl Write for FailedWriter {
        fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
            if self.flush_failure { Ok(bytes.len()) }
            else { Err(io::Error::new(io::ErrorKind::WriteZero,"synthetic write failure")) }
        }
        fn flush(&mut self) -> io::Result<()> { Err(io::Error::new(io::ErrorKind::Other,"synthetic flush failure")) }
    }
    #[test]
    fn incomplete_write_and_flush_are_environment_failures() {
        for flush_failure in [false,true] {
            assert!(llvm_cli::write_complete(&mut FailedWriter{flush_failure},b"bounded bytes").is_err());
        }
        // These early refusals touch no filesystem and cannot replace any file.
        assert!(llvm_cli::write_new(Path::new("/elsewhere/module.ll"),b"bytes").is_err());
        assert!(llvm_cli::run_with(&[],&mut Vec::new()).is_err());
    }
}
