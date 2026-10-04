//! Standalone source-only unit harness. Admission is required before compilation/run.
//! These cases are authored from the contract, not copied from a conformance oracle.
#[path = "../../../examples/probes/backend/rust/transport.rs"] pub mod transport;
#[path = "../../../examples/probes/backend/rust/check.rs"] pub mod check;
#[path = "../../../examples/probes/backend/rust/ir.rs"] pub mod ir;
#[path = "../../../examples/probes/backend/rust/canonical.rs"] pub mod canonical;
#[path = "../../../examples/probes/backend/rust/sha256.rs"] pub mod sha256;

#[cfg(test)]
mod tests {
    use crate::canonical;
    use crate::check::{self, FrontendError, Reason};
    use crate::ir::{NodeKind, Scalar, Type};
    use crate::transport::{self, JsonString, TransportError, Value};

    fn program(body: &str, result: &str) -> String {
        format!(r#"{{"schema":"bagaev-probe-ir/1","entry":"main","functions":{{"main":{{"params":[],"result":"{result}","body":{body}}}}}}}"#)
    }
    fn invocation(program: &str, args: &str) -> String {
        format!(r#"{{"schema":"bagaev-probe-invocation/1","program":{program},"arguments":{args}}}"#)
    }
    fn refusal(bytes: &[u8], reason: Reason, location: &str) {
        match check::check_invocation_bytes(bytes) {
            Err(FrontendError::Refusal(e))=>{assert_eq!(e.reason(),reason);assert_eq!(e.location(),location);}
            other=>panic!("expected refusal, got {other:?}"),
        }
    }

    #[test]
    fn byte_overrun_precedes_utf8_and_json() {
        let bytes=vec![0xff;transport::FRAME_LIMIT+1];
        refusal(&bytes,Reason::Bounds,"");
    }
    #[test]
    fn whole_document_grammar_precedes_outer_shape() {
        refusal(br#"{"extra":1,"extra":2}"#,Reason::Json,"");
        refusal(br#"{"extra":1} null"#,Reason::Json,"");
        refusal(br#"{"x":0,"\u0078":1}"#,Reason::Json,"");
        refusal(b"\xef\xbb\xbf{}",Reason::Json,"");
        refusal(b"{}\xff",Reason::Json,"");
        refusal(br#"{"extra":1}"#,Reason::Shape,"");
    }
    #[test]
    fn parser_depth_does_not_replace_envelope_shape() {
        let mut frame=String::from(r#"{"schema":"bagaev-probe-invocation/1","arguments":[],"extra":null,"program":"#);
        frame.push_str(&"[".repeat(10_000));frame.push('0');frame.push_str(&"]".repeat(10_000));frame.push('}');
        refusal(frame.as_bytes(),Reason::Shape,"");
        frame.pop();
        refusal(frame.as_bytes(),Reason::Json,"");
    }
    #[test]
    fn outer_bounds_precede_program_version() {
        let args=format!("{}0{}","[".repeat(133),"]".repeat(133));
        let p=r#"{"schema":"wrong","entry":"main","functions":{}}"#;
        match check::check_invocation_bytes(invocation(p,&args).as_bytes()) {
            Err(FrontendError::Refusal(e))=>{assert_eq!(e.reason(),Reason::Bounds);assert!(e.location().starts_with("/arguments/0"));}
            other=>panic!("expected outer bound, got {other:?}"),
        }
    }
    #[test]
    fn number_tags_and_huge_lexemes_survive_transport() {
        let huge="9".repeat(4096);
        refusal(invocation(&program(&format!("[\"int\",{huge}]"),"Int64"),"[]").as_bytes(),
                Reason::Bounds,"/program/functions/main/body/1");
        for literal in ["true","1.0","1e0"] {
            refusal(invocation(&program(&format!("[\"int\",{literal}]"),"Int64"),"[]").as_bytes(),
                    Reason::Shape,"/program/functions/main/body/1");
        }
        let checked=check::check_program_bytes(program("[\"int\",-0]","Int64").as_bytes()).unwrap();
        assert!(std::str::from_utf8(checked.canonical_bytes()).unwrap().contains("[\"int\",0]"));
    }
    #[test]
    fn escaped_surrogates_are_shape_not_json() {
        let p=r#"{"schema":"bagaev-probe-ir/1","entry":"main","functions":{"main":{"params":[["\ud800","Int64"]],"result":"Int64","body":["int",0]}}}"#;
        refusal(invocation(p,"[]").as_bytes(),Reason::Shape,"/program/functions/main/params/0/0");
        let p=r#"{"schema":"bagaev-probe-ir/1","entry":"main","functions":{"\ud800":{"params":[],"result":"Int64","body":["int",0]}}}"#;
        refusal(invocation(p,"[]").as_bytes(),Reason::Shape,"/program/functions");
        let doc=transport::parse(br#"["\ud83d\ude00","\ud800"]"#).unwrap();
        let items=match &doc.values[doc.root]{Value::Array(items)=>items,_=>panic!("array")};
        assert!(matches!(&doc.values[items[0]],Value::String(s) if s==&JsonString(vec![0x1f600])));
        assert!(matches!(&doc.values[items[1]],Value::String(s) if s==&JsonString(vec![0xd800])));
    }
    #[test]
    fn structural_phase_finishes_before_reference_or_type() {
        let p=r#"{"schema":"bagaev-probe-ir/1","entry":"missing","functions":{"a":{"params":[],"result":"Int64","body":["arg","missing"]},"z":{"params":[],"result":"Int64","body":["unknown"]}}}"#;
        refusal(invocation(p,"[]").as_bytes(),Reason::Shape,"/program/functions/z/body");
        let p=program("[\"add\",[\"bool\",true],[\"arg\",\"missing\"]]","Int64");
        refusal(invocation(&p,"[]").as_bytes(),Reason::Reference,"/program/functions/main/body/2");
    }
    #[test]
    fn immediate_child_type_check_precedes_later_child_inference() {
        let p=program("[\"add\",[\"bool\",true],[\"not\",[\"int\",0]]]","Int64");
        refusal(invocation(&p,"[]").as_bytes(),Reason::Type,"/program/functions/main/body/1");
    }
    #[test]
    fn complete_numbering_includes_unused_function_and_arm() {
        let p=r#"{"functions":{"z":{"body":["int",9],"result":"Int64","params":[]},"a":{"body":["if",["bool",true],["int",1],["int",2]],"result":"Int64","params":[]}},"entry":"a","schema":"bagaev-probe-ir/1"}"#;
        let checked=check::check_program_bytes(p.as_bytes()).unwrap();
        assert_eq!(checked.nodes().len(),5); assert_eq!(checked.functions()[0].name(),"a");
        assert_eq!(checked.node(4).unwrap().pointer(),"/functions/a/body/3");
        assert_eq!(checked.node(5).unwrap().pointer(),"/functions/z/body");
        assert_eq!(checked.node(5).unwrap().ty(),Type::Int64);
    }
    #[test]
    fn binders_see_correct_initial_and_body_scopes() {
        let p=program("[\"loop\",0,\"i\",\"acc\",\"Int64\",[\"use\",\"acc\"],[\"use\",\"acc\"]]","Int64");
        refusal(invocation(&p,"[]").as_bytes(),Reason::Reference,"/program/functions/main/body/5");
        let p=program("[\"let\",\"x\",\"Int64\",[\"int\",0],[\"let\",\"x\",\"Int64\",[\"int\",1],[\"use\",\"x\"]]]","Int64");
        refusal(invocation(&p,"[]").as_bytes(),Reason::Shape,"/program/functions/main/body/4/1");
        let checked=check::check_program_bytes(program("[\"let\",\"x\",\"Int64\",[\"int\",0],[\"use\",\"x\"]]","Int64").as_bytes()).unwrap();
        assert!(matches!(checked.node(3).unwrap().kind(),NodeKind::Use{slot:0}));
    }
    #[test]
    fn sorted_cycle_edge_uses_first_occurrence() {
        let p=r#"{"schema":"bagaev-probe-ir/1","entry":"a","functions":{"a":{"params":[],"result":"Int64","body":["add",["call","b"],["call","b"]]},"b":{"params":[],"result":"Int64","body":["call","a"]}}}"#;
        refusal(invocation(p,"[]").as_bytes(),Reason::Cycle,"/program/functions/b/body");
    }
    #[test]
    fn json_arguments_are_checked_after_entire_program() {
        let p=r#"{"schema":"bagaev-probe-ir/1","entry":"main","functions":{"main":{"params":[["x","Bool"],["y","Int64"]],"result":"Bool","body":["arg","x"]}}}"#;
        refusal(invocation(p,"[1,0]").as_bytes(),Reason::Argument,"/arguments/0");
        refusal(invocation(p,"[true,true]").as_bytes(),Reason::Argument,"/arguments/1");
        let checked=check::check_invocation_bytes(invocation(p,"[true,-9223372036854775808]").as_bytes()).unwrap();
        assert_eq!(checked.arguments(),&[Scalar::Bool(true),Scalar::Int64(i64::MIN)]);
        let output=canonical::invocation_bytes(&checked);
        assert!(output.ends_with(b"\n"));
        let doc=transport::parse(&output).unwrap();
        let map=match &doc.values[doc.root]{Value::Object(map)=>map,_=>panic!("artifact object")};
        let schema=map[&JsonString::from_str("schema")];
        assert!(matches!(&doc.values[schema],Value::String(s) if s==&JsonString::from_str("bagaev-probe-checked-invocation/1")));
    }
    #[test]
    fn malformed_number_and_trailing_comma_are_transport_errors() {
        for bytes in [b"01".as_slice(),b"1e+",b"[1,]",b"{\"x\":0,}"] {
            assert!(matches!(transport::parse(bytes),Err(TransportError::Json)));
        }
    }
    #[test]
    fn every_manifest_form_has_a_checked_representation() {
        let cases=[
            ("[\"int\",0]","Int64","int"),("[\"bool\",false]","Bool","bool"),
            ("[\"add\",[\"int\",0],[\"int\",1]]","Int64","add"),
            ("[\"sub\",[\"int\",0],[\"int\",1]]","Int64","sub"),
            ("[\"mul\",[\"int\",0],[\"int\",1]]","Int64","mul"),
            ("[\"eq\",[\"bool\",false],[\"bool\",true]]","Bool","eq"),
            ("[\"lt\",[\"int\",0],[\"int\",1]]","Bool","lt"),
            ("[\"le\",[\"int\",0],[\"int\",1]]","Bool","le"),
            ("[\"not\",[\"bool\",true]]","Bool","not"),
            ("[\"if\",[\"bool\",true],[\"int\",0],[\"int\",1]]","Int64","if"),
            ("[\"let\",\"x\",\"Int64\",[\"int\",0],[\"use\",\"x\"]]","Int64","let"),
            ("[\"loop\",1024,\"i\",\"acc\",\"Int64\",[\"int\",0],[\"use\",\"acc\"]]","Int64","loop"),
        ];
        for (body,result,op) in cases {
            let checked=check::check_program_bytes(program(body,result).as_bytes()).unwrap();
            assert_eq!(checked.node(1).unwrap().kind().name(),op);
        }
        // arg/use/call have additional scope and DAG requirements.
        let p=r#"{"schema":"bagaev-probe-ir/1","entry":"a","functions":{"a":{"params":[["x","Int64"]],"result":"Int64","body":["call","b",["arg","x"]]},"b":{"params":[["y","Int64"]],"result":"Int64","body":["let","z","Int64",["arg","y"],["use","z"]]}}}"#;
        let checked=check::check_program_bytes(p.as_bytes()).unwrap();
        assert!(matches!(checked.node(1).unwrap().kind(),NodeKind::Call{function:1,..}));
        assert_eq!(checked.functions()[0].callees(),&[1]);
    }
    #[test]
    fn expression_bounds_precede_later_semantics() {
        let mut body=String::from("[\"int\",0]");
        for _ in 0..8 { body=format!("[\"add\",{body},{body}]"); }
        let p=format!(r#"{{"schema":"bagaev-probe-ir/1","entry":"missing","functions":{{"a":{{"params":[],"result":"Int64","body":{body}}},"z":{{"params":[],"result":"Int64","body":["add",["int",0],["int",0]]}}}}}}"#);
        refusal(invocation(&p,"[]").as_bytes(),Reason::Bounds,"/program/functions/z/body/1");
        let mut body=String::from("[\"bool\",false]");
        for _ in 0..32 { body=format!("[\"not\",{body}]"); }
        let path=format!("/program/functions/main/body{}","/1".repeat(32));
        refusal(invocation(&program(&body,"Bool"),"[]").as_bytes(),Reason::Bounds,&path);
    }
    #[test]
    fn call_arity_precedes_reference_errors_in_arguments() {
        let p=r#"{"schema":"bagaev-probe-ir/1","entry":"a","functions":{"a":{"params":[],"result":"Int64","body":["call","b",["arg","missing"]]},"b":{"params":[],"result":"Int64","body":["int",0]}}}"#;
        refusal(invocation(p,"[]").as_bytes(),Reason::Reference,"/program/functions/a/body");
    }
    #[test]
    fn canonical_refusal_wire_is_complete_and_distinct() {
        let error=match check::check_invocation_bytes(b"{}") {
            Err(FrontendError::Refusal(error))=>error,other=>panic!("refusal: {other:?}"),
        };
        assert_eq!(canonical::refusal_bytes(&error),
            b"{\"location\":\"\",\"reason\":\"IR_SHAPE\",\"schema\":\"bagaev-probe-result/1\",\"status\":\"invalid-ir\",\"value\":null,\"value_type\":null,\"work\":0}\n");
    }
}
