//! Data-only /12 input preparation checks. No generated native code is called.
pub mod transport;
pub mod text_value;
pub mod int_projection;
pub mod json_native_input;
pub mod json_native_input12;

#[test]
fn boolean_payload_and_old_boundary() {
    for (raw,expected) in [(b"true".as_slice(),1),(b"false".as_slice(),0)] {
        let new=json_native_input12::prepare(&[raw]).unwrap();
        let old=json_native_input::prepare(&[raw]).unwrap();
        // Pointers originate from these still-live immutable owners.
        unsafe {
            let n=&*new.root(0).unwrap(); let o=&*old.root(0).unwrap();
            assert_eq!((n.kind,n.bool_payload),(2,expected));
            assert_eq!((o.kind,o.reserved),(2,0));
            assert_eq!(n.int_valid,0);
        }
    }
}

#[test]
fn all_other_kinds_have_zero_boolean_payload() {
    for (raw,kind) in [("null",1),("0",3),("-0",3),("1.5",4),("1e0",4),("\"true\"",5),("[]",6),("{}",7)] {
        let owner=json_native_input12::prepare(&[raw.as_bytes()]).unwrap();
        unsafe { let n=&*owner.root(0).unwrap();assert_eq!((n.kind,n.bool_payload),(kind,0)); }
    }
}

#[test]
fn nested_values_and_layout_are_preserved() {
    assert_eq!(std::mem::size_of::<json_native_input12::Node>(),80);
    assert_eq!(std::mem::offset_of!(json_native_input12::Node,bool_payload),72);
    let owner=json_native_input12::prepare(&[b"[true,false,{\"active\":true}]"]).unwrap();
    unsafe {
        let root=&*owner.root(0).unwrap();assert_eq!((root.kind,root.count),(6,3));
        assert_eq!((*(*root.entries).child).bool_payload,1);
        assert_eq!((*(*root.entries.add(1)).child).bool_payload,0);
        let object=&*(*root.entries.add(2)).child;assert_eq!((object.kind,object.count),(7,1));
        assert_eq!((*(*object.entries).child).bool_payload,1);
    }
}

#[test]
fn malformed_and_excess_arguments_refuse() {
    assert!(json_native_input12::prepare(&[b"tru"]).is_err());
    assert!(json_native_input12::prepare(&[b"true".as_slice();9]).is_err());
    let owner=json_native_input12::prepare(&[]).unwrap();assert!(owner.root(0).is_none());
}
