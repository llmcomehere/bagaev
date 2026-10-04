//! Source preparation for the bounded Cranelift object probe.
//! No lowering or conformance claim until the adapter has been checked.
#[path = "../../rust/transport.rs"] pub mod transport;
#[path = "../../rust/check.rs"] pub mod check;
#[path = "../../rust/ir.rs"] pub mod ir;
#[path = "../../rust/canonical.rs"] pub mod canonical;
#[path = "../../rust/sha256.rs"] pub mod sha256;
pub mod lower;

#[cfg(test)]
mod tests {
    use super::{check,lower};
    const SOURCE:&[u8]=br#"{"schema":"bagaev-probe-ir/1","entry":"main","functions":{"main":{"params":[],"result":"Int64","body":["int",0]}}}"#;
    #[test]
    fn deterministic_elf_for_each_declared_mode(){
        let p=check::check_program_bytes(SOURCE).unwrap();
        for mode in [lower::Mode::None,lower::Mode::Speed,lower::Mode::Size]{
            let a=lower::object(&p,mode).unwrap();let b=lower::object(&p,mode).unwrap();
            assert_eq!(a,b);assert!(a.starts_with(b"\x7fELF"));
            assert!(a.windows(p.canonical_bytes().len()).any(|w|w==p.canonical_bytes()));
            assert!(a.windows(b"bagaev_probe_entry".len()).any(|w|w==b"bagaev_probe_entry"));
        }
    }
    #[test]
    fn checked_program_remains_unchanged(){
        let p=check::check_program_bytes(SOURCE).unwrap();let before=p.canonical_bytes().to_vec();let pin=p.identity().to_owned();
        let _=lower::object(&p,lower::Mode::None).unwrap();assert_eq!(p.canonical_bytes(),before);assert_eq!(p.identity(),pin);
    }
}
