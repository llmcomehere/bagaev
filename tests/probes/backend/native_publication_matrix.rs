//! Prepared original-path matrix. Running this test needs separate /out authority.
//! Compilation and --list do not execute original_out_matrix.
#[path = "../../../examples/probes/backend/rust/transport.rs"] pub mod transport;
#[path = "../../../examples/probes/backend/rust/check.rs"] pub mod check;
#[path = "../../../examples/probes/backend/rust/ir.rs"] pub mod ir;
#[path = "../../../examples/probes/backend/rust/canonical.rs"] pub mod canonical;
#[path = "../../../examples/probes/backend/rust/sha256.rs"] pub mod sha256;
#[path = "../../../examples/probes/backend/rust/native.rs"] pub mod native;
#[path = "../../../examples/probes/backend/rust/native_main.rs"] pub mod native_cli;

#[cfg(test)]
mod publication_matrix {
    use super::native_cli;
    use std::collections::BTreeMap;
    use std::fs::{self, OpenOptions};
    use std::io::{self, Write};
    use std::os::unix::fs::symlink;
    use std::path::{Path, PathBuf};

    // The operator must authorize this exact root before running the test.
    const ROOT: &str = "/out/bagaev-publication-matrix-r1";
    #[derive(Clone, Debug, PartialEq, Eq)]
    enum Entry { File(Vec<u8>), Directory, Symlink(PathBuf) }

    fn snapshot(root: &Path) -> BTreeMap<PathBuf, Entry> {
        fn collect(root: &Path, dir: &Path, rows: &mut BTreeMap<PathBuf, Entry>) {
            for item in fs::read_dir(dir).unwrap() {
                let path = item.unwrap().path();
                let kind = fs::symlink_metadata(&path).unwrap().file_type();
                let key = path.strip_prefix(root).unwrap().to_path_buf();
                if kind.is_symlink() { rows.insert(key, Entry::Symlink(fs::read_link(&path).unwrap())); }
                else if kind.is_dir() { rows.insert(key, Entry::Directory); collect(root, &path, rows); }
                else { assert!(kind.is_file()); rows.insert(key, Entry::File(fs::read(&path).unwrap())); }
            }
        }
        let mut rows = BTreeMap::new(); collect(root, root, &mut rows); rows
    }

    fn create(path: &Path, bytes: &[u8]) {
        let mut f = OpenOptions::new().write(true).create_new(true).open(path).unwrap();
        f.write_all(bytes).unwrap(); f.flush().unwrap();
    }

    fn observe(root: &Path, id: &str, target: &str, bytes: &[u8],
               success: bool, error_kind: Option<io::ErrorKind>) {
        let before = snapshot(root);
        let result = native_cli::write_new(&root.join(target), bytes);
        assert_eq!(result.is_ok(), success, "{id}: API result");
        if let Some(kind) = error_kind { assert_eq!(result.as_ref().unwrap_err().kind(), kind, "{id}"); }
        let after = snapshot(root);
        let mut expected = before;
        if success { assert!(expected.insert(PathBuf::from(target), Entry::File(bytes.to_vec())).is_none()); }
        assert_eq!(after, expected, "{id}: exact complete tree observation");
        // This denotes only the API return; no power-loss durability assertion.
        println!("{{\"case_id\":\"{id}\",\"api_success\":{success},\"complete_tree_matched\":true}}");
    }

    #[test]
    fn original_out_matrix() {
        let out = Path::new("/out");
        assert!(fs::symlink_metadata(out).unwrap().file_type().is_dir());
        assert_eq!(fs::canonicalize(out).unwrap(), out);
        let root = Path::new(ROOT);
        // Exclusive one-shot setup. Never overwrite, remove or reuse an old run.
        fs::create_dir(root).unwrap();
        assert_eq!(fs::canonicalize(root).unwrap(), root);
        create(&root.join("existing.witness"), b"keep");
        fs::create_dir(root.join("directory.witness")).unwrap();
        create(&root.join("directory.witness/child"), b"keep");
        create(&root.join("owned-sentinel"), b"keep");
        symlink("owned-sentinel", root.join("link.witness")).unwrap();
        fs::create_dir(root.join("real-owned-directory")).unwrap();
        symlink("real-owned-directory", root.join("alias")).unwrap();
        observe(root,"PUB-01-NEW","new.witness",b"abc\0\n\xff",true,None);
        observe(root,"PUB-02-EXISTING","existing.witness",b"replace",false,None);
        observe(root,"PUB-03-DIRECTORY","directory.witness",b"abc",false,None);
        observe(root,"PUB-04-SYMLINK","link.witness",b"abc",false,None);
        let oversized = vec![b'a'; super::native::WITNESS_LIMIT + 1];
        observe(root,"PUB-05-OVERSIZE","oversize.witness",&oversized,false,Some(io::ErrorKind::InvalidInput));
        observe(root,"PUB-06-EMPTY","empty.witness",b"",true,None);
        observe(root,"PUB-07-MISSING-PARENT","absent-parent/new.witness",b"abc",false,None);
        observe(root,"PUB-08-SYMLINK-PARENT","alias/new.witness",b"abc",false,Some(io::ErrorKind::InvalidInput));
        // No cleanup: preserve complete and partial artifacts for inspection.
    }
}
