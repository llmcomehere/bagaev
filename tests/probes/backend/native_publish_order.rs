//! Prepared publish ordering; original /out execution requires separate authority.
//! Compilation and --list do not execute filesystem cases.
#[path = "../../../examples/probes/backend/rust/transport.rs"] pub mod transport;
#[path = "../../../examples/probes/backend/rust/check.rs"] pub mod check;
#[path = "../../../examples/probes/backend/rust/ir.rs"] pub mod ir;
#[path = "../../../examples/probes/backend/rust/canonical.rs"] pub mod canonical;
#[path = "../../../examples/probes/backend/rust/sha256.rs"] pub mod sha256;
#[path = "../../../examples/probes/backend/rust/native.rs"] pub mod native;
#[path = "../../../examples/probes/backend/rust/native_main.rs"] pub mod native_cli;

#[cfg(test)]
mod publish_order {
    use super::{native, native_cli};
    use std::fs::{self, OpenOptions};
    use std::io::{self, Write};
    use std::path::{Path, PathBuf};

    struct Sink {
        path: PathBuf, witness: Vec<u8>, bytes: Vec<u8>, calls: usize,
        flushes: usize, stop: Option<usize>, fail_flush: bool,
    }
    impl Write for Sink {
        fn write(&mut self, input: &[u8]) -> io::Result<usize> {
            self.calls += 1;
            assert_eq!(fs::read(&self.path).unwrap(), self.witness);
            if self.stop == Some(self.bytes.len()) {
                return Err(io::Error::new(io::ErrorKind::BrokenPipe,"scripted stdout"));
            }
            let n = input.len().min(2).min(self.stop.unwrap_or(usize::MAX)-self.bytes.len());
            self.bytes.extend_from_slice(&input[..n]); Ok(n)
        }
        fn flush(&mut self) -> io::Result<()> {
            self.flushes += 1;
            assert_eq!(fs::read(&self.path).unwrap(), self.witness);
            if self.fail_flush { Err(io::Error::new(io::ErrorKind::BrokenPipe,"scripted flush")) }
            else { Ok(()) }
        }
    }

    #[test]
    fn original_publish_order() {
        let out = Path::new("/out");
        assert!(fs::symlink_metadata(out).unwrap().file_type().is_dir());
        assert_eq!(fs::canonicalize(out).unwrap(), out);
        let root = out.join("bagaev-publish-order-r1");
        fs::create_dir(&root).unwrap(); // exclusive; retain all partial artifacts
        assert_eq!(fs::canonicalize(&root).unwrap(), root);
        let observation = match native::check_frame(b"{}",native::Prefill::Zero).unwrap() {
            native::Checked::Refusal(o) => o, _ => panic!("static refusal required")
        };
        let result = observation.result_bytes();
        assert!(result.len() > 2);
        let witness = observation.witness_bytes();
        for (id, stop, fail_flush, existing) in [
            ("ORDER-01",None,false,false),
            ("ORDER-02",Some(2),false,false),
            ("ORDER-03",None,true,false),
            ("ORDER-04",None,false,true),
        ] {
            let path = root.join(format!("{id}.witness"));
            if existing {
                let mut file = OpenOptions::new().write(true).create_new(true).open(&path).unwrap();
                file.write_all(b"keep").unwrap(); file.flush().unwrap();
            }
            let mut sink = Sink {path:path.clone(),witness:witness.to_vec(),bytes:Vec::new(),calls:0,flushes:0,stop,fail_flush};
            let outcome = native_cli::publish(&observation,&path,&mut sink);
            assert_eq!(outcome.is_ok(),id=="ORDER-01");
            if existing {
                assert_eq!(fs::read(&path).unwrap(),b"keep");
                assert_eq!((sink.calls,sink.flushes),(0,0));
                assert!(sink.bytes.is_empty());
            } else {
                assert_eq!(fs::read(&path).unwrap(),witness);
                assert_eq!(sink.bytes,if stop.is_some(){result[..2].to_vec()}else{result.to_vec()});
                assert_eq!(sink.flushes,if stop.is_some(){0}else{1});
                if id!="ORDER-01" {assert_eq!(outcome.unwrap_err().kind(),io::ErrorKind::BrokenPipe);}
            }
            println!("{id}: exact witness/stdout observation matched");
        }
        assert_eq!(fs::read_dir(&root).unwrap().count(),4);
    }
}
