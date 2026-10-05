//! Literal list cases frozen before implementation.
#[path="../../../examples/probes/backend/rust/text_value.rs"] pub mod text_value;
#[path="../../../examples/probes/backend/rust/text_list.rs"] pub mod text_list;
use text_value::Text;use text_list::TextList;
fn bytes(h:&str)->Vec<u8>{(0..h.len()).step_by(2).map(|i|u8::from_str_radix(&h[i..i+2],16).unwrap()).collect()}

#[test]
fn empty(){
let owned:Vec<Vec<u8>>=vec![];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),0);assert_eq!(list.is_empty(),true);assert_eq!(list.total_bytes(),0);assert_eq!(list.is_strictly_increasing(),true);assert!(list.get(usize::MAX).is_none());
let query=bytes("");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),false);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),0);assert_eq!(sorted.is_empty(),true);assert!(sorted.get(usize::MAX).is_none());
drop(list);drop(values);assert_eq!(owned,before);}

#[test]
fn empty_text(){
let owned:Vec<Vec<u8>>=vec![bytes("").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),1);assert_eq!(list.is_empty(),false);assert_eq!(list.total_bytes(),0);assert_eq!(list.is_strictly_increasing(),true);assert!(list.get(usize::MAX).is_none());
let query=bytes("");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),true);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),1);assert_eq!(sorted.is_empty(),false);assert!(sorted.get(usize::MAX).is_none());
assert_eq!(sorted.get(0).unwrap().bytes(),owned[0]);assert_eq!(sorted.get(0).unwrap().bytes().as_ptr(),owned[0].as_ptr());
drop(list);drop(values);assert_eq!(sorted.get(0).unwrap().bytes(),owned[0]);
assert_eq!(owned,before);}

#[test]
fn duplicates(){
let owned:Vec<Vec<u8>>=vec![bytes("726564").repeat(1),bytes("626c7565").repeat(1),bytes("726564").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),3);assert_eq!(list.is_empty(),false);assert_eq!(list.total_bytes(),10);assert_eq!(list.is_strictly_increasing(),false);assert!(list.get(usize::MAX).is_none());
let query=bytes("726564");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),true);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),2);assert_eq!(sorted.is_empty(),false);assert!(sorted.get(usize::MAX).is_none());
assert_eq!(sorted.get(0).unwrap().bytes(),owned[1]);assert_eq!(sorted.get(0).unwrap().bytes().as_ptr(),owned[1].as_ptr());
assert_eq!(sorted.get(1).unwrap().bytes(),owned[0]);assert_eq!(sorted.get(1).unwrap().bytes().as_ptr(),owned[0].as_ptr());
drop(list);drop(values);assert_eq!(sorted.get(0).unwrap().bytes(),owned[1]);
assert_eq!(sorted.get(1).unwrap().bytes(),owned[0]);
assert_eq!(owned,before);}

#[test]
fn ordered(){
let owned:Vec<Vec<u8>>=vec![bytes("61").repeat(1),bytes("62").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),2);assert_eq!(list.is_empty(),false);assert_eq!(list.total_bytes(),2);assert_eq!(list.is_strictly_increasing(),true);assert!(list.get(usize::MAX).is_none());
let query=bytes("7a");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),false);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),2);assert_eq!(sorted.is_empty(),false);assert!(sorted.get(usize::MAX).is_none());
assert_eq!(sorted.get(0).unwrap().bytes(),owned[0]);assert_eq!(sorted.get(0).unwrap().bytes().as_ptr(),owned[0].as_ptr());
assert_eq!(sorted.get(1).unwrap().bytes(),owned[1]);assert_eq!(sorted.get(1).unwrap().bytes().as_ptr(),owned[1].as_ptr());
drop(list);drop(values);assert_eq!(sorted.get(0).unwrap().bytes(),owned[0]);
assert_eq!(sorted.get(1).unwrap().bytes(),owned[1]);
assert_eq!(owned,before);}

#[test]
fn reversed(){
let owned:Vec<Vec<u8>>=vec![bytes("62").repeat(1),bytes("61").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),2);assert_eq!(list.is_empty(),false);assert_eq!(list.total_bytes(),2);assert_eq!(list.is_strictly_increasing(),false);assert!(list.get(usize::MAX).is_none());
let query=bytes("61");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),true);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),2);assert_eq!(sorted.is_empty(),false);assert!(sorted.get(usize::MAX).is_none());
assert_eq!(sorted.get(0).unwrap().bytes(),owned[1]);assert_eq!(sorted.get(0).unwrap().bytes().as_ptr(),owned[1].as_ptr());
assert_eq!(sorted.get(1).unwrap().bytes(),owned[0]);assert_eq!(sorted.get(1).unwrap().bytes().as_ptr(),owned[0].as_ptr());
drop(list);drop(values);assert_eq!(sorted.get(0).unwrap().bytes(),owned[1]);
assert_eq!(sorted.get(1).unwrap().bytes(),owned[0]);
assert_eq!(owned,before);}

#[test]
fn nul(){
let owned:Vec<Vec<u8>>=vec![bytes("610063").repeat(1),bytes("610062").repeat(1),bytes("610063").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),3);assert_eq!(list.is_empty(),false);assert_eq!(list.total_bytes(),9);assert_eq!(list.is_strictly_increasing(),false);assert!(list.get(usize::MAX).is_none());
let query=bytes("610062");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),true);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),2);assert_eq!(sorted.is_empty(),false);assert!(sorted.get(usize::MAX).is_none());
assert_eq!(sorted.get(0).unwrap().bytes(),owned[1]);assert_eq!(sorted.get(0).unwrap().bytes().as_ptr(),owned[1].as_ptr());
assert_eq!(sorted.get(1).unwrap().bytes(),owned[0]);assert_eq!(sorted.get(1).unwrap().bytes().as_ptr(),owned[0].as_ptr());
drop(list);drop(values);assert_eq!(sorted.get(0).unwrap().bytes(),owned[1]);
assert_eq!(sorted.get(1).unwrap().bytes(),owned[0]);
assert_eq!(owned,before);}

#[test]
fn scalar_order(){
let owned:Vec<Vec<u8>>=vec![bytes("f0908080").repeat(1),bytes("ee8080").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),2);assert_eq!(list.is_empty(),false);assert_eq!(list.total_bytes(),7);assert_eq!(list.is_strictly_increasing(),false);assert!(list.get(usize::MAX).is_none());
let query=bytes("");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),false);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),2);assert_eq!(sorted.is_empty(),false);assert!(sorted.get(usize::MAX).is_none());
assert_eq!(sorted.get(0).unwrap().bytes(),owned[1]);assert_eq!(sorted.get(0).unwrap().bytes().as_ptr(),owned[1].as_ptr());
assert_eq!(sorted.get(1).unwrap().bytes(),owned[0]);assert_eq!(sorted.get(1).unwrap().bytes().as_ptr(),owned[0].as_ptr());
drop(list);drop(values);assert_eq!(sorted.get(0).unwrap().bytes(),owned[1]);
assert_eq!(sorted.get(1).unwrap().bytes(),owned[0]);
assert_eq!(owned,before);}

#[test]
fn no_normalization(){
let owned:Vec<Vec<u8>>=vec![bytes("c3a9").repeat(1),bytes("65cc81").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),2);assert_eq!(list.is_empty(),false);assert_eq!(list.total_bytes(),5);assert_eq!(list.is_strictly_increasing(),false);assert!(list.get(usize::MAX).is_none());
let query=bytes("c3a9");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),true);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),2);assert_eq!(sorted.is_empty(),false);assert!(sorted.get(usize::MAX).is_none());
assert_eq!(sorted.get(0).unwrap().bytes(),owned[1]);assert_eq!(sorted.get(0).unwrap().bytes().as_ptr(),owned[1].as_ptr());
assert_eq!(sorted.get(1).unwrap().bytes(),owned[0]);assert_eq!(sorted.get(1).unwrap().bytes().as_ptr(),owned[0].as_ptr());
drop(list);drop(values);assert_eq!(sorted.get(0).unwrap().bytes(),owned[1]);
assert_eq!(sorted.get(1).unwrap().bytes(),owned[0]);
assert_eq!(owned,before);}

#[test]
fn prefix(){
let owned:Vec<Vec<u8>>=vec![bytes("6162").repeat(1),bytes("61").repeat(1),bytes("").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),3);assert_eq!(list.is_empty(),false);assert_eq!(list.total_bytes(),3);assert_eq!(list.is_strictly_increasing(),false);assert!(list.get(usize::MAX).is_none());
let query=bytes("61");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),true);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),3);assert_eq!(sorted.is_empty(),false);assert!(sorted.get(usize::MAX).is_none());
assert_eq!(sorted.get(0).unwrap().bytes(),owned[2]);assert_eq!(sorted.get(0).unwrap().bytes().as_ptr(),owned[2].as_ptr());
assert_eq!(sorted.get(1).unwrap().bytes(),owned[1]);assert_eq!(sorted.get(1).unwrap().bytes().as_ptr(),owned[1].as_ptr());
assert_eq!(sorted.get(2).unwrap().bytes(),owned[0]);assert_eq!(sorted.get(2).unwrap().bytes().as_ptr(),owned[0].as_ptr());
drop(list);drop(values);assert_eq!(sorted.get(0).unwrap().bytes(),owned[2]);
assert_eq!(sorted.get(1).unwrap().bytes(),owned[1]);
assert_eq!(sorted.get(2).unwrap().bytes(),owned[0]);
assert_eq!(owned,before);}

#[test]
fn count_max(){
let owned:Vec<Vec<u8>>=vec![bytes("3633").repeat(1),bytes("3632").repeat(1),bytes("3631").repeat(1),bytes("3630").repeat(1),bytes("3539").repeat(1),bytes("3538").repeat(1),bytes("3537").repeat(1),bytes("3536").repeat(1),bytes("3535").repeat(1),bytes("3534").repeat(1),bytes("3533").repeat(1),bytes("3532").repeat(1),bytes("3531").repeat(1),bytes("3530").repeat(1),bytes("3439").repeat(1),bytes("3438").repeat(1),bytes("3437").repeat(1),bytes("3436").repeat(1),bytes("3435").repeat(1),bytes("3434").repeat(1),bytes("3433").repeat(1),bytes("3432").repeat(1),bytes("3431").repeat(1),bytes("3430").repeat(1),bytes("3339").repeat(1),bytes("3338").repeat(1),bytes("3337").repeat(1),bytes("3336").repeat(1),bytes("3335").repeat(1),bytes("3334").repeat(1),bytes("3333").repeat(1),bytes("3332").repeat(1),bytes("3331").repeat(1),bytes("3330").repeat(1),bytes("3239").repeat(1),bytes("3238").repeat(1),bytes("3237").repeat(1),bytes("3236").repeat(1),bytes("3235").repeat(1),bytes("3234").repeat(1),bytes("3233").repeat(1),bytes("3232").repeat(1),bytes("3231").repeat(1),bytes("3230").repeat(1),bytes("3139").repeat(1),bytes("3138").repeat(1),bytes("3137").repeat(1),bytes("3136").repeat(1),bytes("3135").repeat(1),bytes("3134").repeat(1),bytes("3133").repeat(1),bytes("3132").repeat(1),bytes("3131").repeat(1),bytes("3130").repeat(1),bytes("3039").repeat(1),bytes("3038").repeat(1),bytes("3037").repeat(1),bytes("3036").repeat(1),bytes("3035").repeat(1),bytes("3034").repeat(1),bytes("3033").repeat(1),bytes("3032").repeat(1),bytes("3031").repeat(1),bytes("3030").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),64);assert_eq!(list.is_empty(),false);assert_eq!(list.total_bytes(),128);assert_eq!(list.is_strictly_increasing(),false);assert!(list.get(usize::MAX).is_none());
let query=bytes("3030");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),true);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),64);assert_eq!(sorted.is_empty(),false);assert!(sorted.get(usize::MAX).is_none());
assert_eq!(sorted.get(0).unwrap().bytes(),owned[63]);assert_eq!(sorted.get(0).unwrap().bytes().as_ptr(),owned[63].as_ptr());
assert_eq!(sorted.get(1).unwrap().bytes(),owned[62]);assert_eq!(sorted.get(1).unwrap().bytes().as_ptr(),owned[62].as_ptr());
assert_eq!(sorted.get(2).unwrap().bytes(),owned[61]);assert_eq!(sorted.get(2).unwrap().bytes().as_ptr(),owned[61].as_ptr());
assert_eq!(sorted.get(3).unwrap().bytes(),owned[60]);assert_eq!(sorted.get(3).unwrap().bytes().as_ptr(),owned[60].as_ptr());
assert_eq!(sorted.get(4).unwrap().bytes(),owned[59]);assert_eq!(sorted.get(4).unwrap().bytes().as_ptr(),owned[59].as_ptr());
assert_eq!(sorted.get(5).unwrap().bytes(),owned[58]);assert_eq!(sorted.get(5).unwrap().bytes().as_ptr(),owned[58].as_ptr());
assert_eq!(sorted.get(6).unwrap().bytes(),owned[57]);assert_eq!(sorted.get(6).unwrap().bytes().as_ptr(),owned[57].as_ptr());
assert_eq!(sorted.get(7).unwrap().bytes(),owned[56]);assert_eq!(sorted.get(7).unwrap().bytes().as_ptr(),owned[56].as_ptr());
assert_eq!(sorted.get(8).unwrap().bytes(),owned[55]);assert_eq!(sorted.get(8).unwrap().bytes().as_ptr(),owned[55].as_ptr());
assert_eq!(sorted.get(9).unwrap().bytes(),owned[54]);assert_eq!(sorted.get(9).unwrap().bytes().as_ptr(),owned[54].as_ptr());
assert_eq!(sorted.get(10).unwrap().bytes(),owned[53]);assert_eq!(sorted.get(10).unwrap().bytes().as_ptr(),owned[53].as_ptr());
assert_eq!(sorted.get(11).unwrap().bytes(),owned[52]);assert_eq!(sorted.get(11).unwrap().bytes().as_ptr(),owned[52].as_ptr());
assert_eq!(sorted.get(12).unwrap().bytes(),owned[51]);assert_eq!(sorted.get(12).unwrap().bytes().as_ptr(),owned[51].as_ptr());
assert_eq!(sorted.get(13).unwrap().bytes(),owned[50]);assert_eq!(sorted.get(13).unwrap().bytes().as_ptr(),owned[50].as_ptr());
assert_eq!(sorted.get(14).unwrap().bytes(),owned[49]);assert_eq!(sorted.get(14).unwrap().bytes().as_ptr(),owned[49].as_ptr());
assert_eq!(sorted.get(15).unwrap().bytes(),owned[48]);assert_eq!(sorted.get(15).unwrap().bytes().as_ptr(),owned[48].as_ptr());
assert_eq!(sorted.get(16).unwrap().bytes(),owned[47]);assert_eq!(sorted.get(16).unwrap().bytes().as_ptr(),owned[47].as_ptr());
assert_eq!(sorted.get(17).unwrap().bytes(),owned[46]);assert_eq!(sorted.get(17).unwrap().bytes().as_ptr(),owned[46].as_ptr());
assert_eq!(sorted.get(18).unwrap().bytes(),owned[45]);assert_eq!(sorted.get(18).unwrap().bytes().as_ptr(),owned[45].as_ptr());
assert_eq!(sorted.get(19).unwrap().bytes(),owned[44]);assert_eq!(sorted.get(19).unwrap().bytes().as_ptr(),owned[44].as_ptr());
assert_eq!(sorted.get(20).unwrap().bytes(),owned[43]);assert_eq!(sorted.get(20).unwrap().bytes().as_ptr(),owned[43].as_ptr());
assert_eq!(sorted.get(21).unwrap().bytes(),owned[42]);assert_eq!(sorted.get(21).unwrap().bytes().as_ptr(),owned[42].as_ptr());
assert_eq!(sorted.get(22).unwrap().bytes(),owned[41]);assert_eq!(sorted.get(22).unwrap().bytes().as_ptr(),owned[41].as_ptr());
assert_eq!(sorted.get(23).unwrap().bytes(),owned[40]);assert_eq!(sorted.get(23).unwrap().bytes().as_ptr(),owned[40].as_ptr());
assert_eq!(sorted.get(24).unwrap().bytes(),owned[39]);assert_eq!(sorted.get(24).unwrap().bytes().as_ptr(),owned[39].as_ptr());
assert_eq!(sorted.get(25).unwrap().bytes(),owned[38]);assert_eq!(sorted.get(25).unwrap().bytes().as_ptr(),owned[38].as_ptr());
assert_eq!(sorted.get(26).unwrap().bytes(),owned[37]);assert_eq!(sorted.get(26).unwrap().bytes().as_ptr(),owned[37].as_ptr());
assert_eq!(sorted.get(27).unwrap().bytes(),owned[36]);assert_eq!(sorted.get(27).unwrap().bytes().as_ptr(),owned[36].as_ptr());
assert_eq!(sorted.get(28).unwrap().bytes(),owned[35]);assert_eq!(sorted.get(28).unwrap().bytes().as_ptr(),owned[35].as_ptr());
assert_eq!(sorted.get(29).unwrap().bytes(),owned[34]);assert_eq!(sorted.get(29).unwrap().bytes().as_ptr(),owned[34].as_ptr());
assert_eq!(sorted.get(30).unwrap().bytes(),owned[33]);assert_eq!(sorted.get(30).unwrap().bytes().as_ptr(),owned[33].as_ptr());
assert_eq!(sorted.get(31).unwrap().bytes(),owned[32]);assert_eq!(sorted.get(31).unwrap().bytes().as_ptr(),owned[32].as_ptr());
assert_eq!(sorted.get(32).unwrap().bytes(),owned[31]);assert_eq!(sorted.get(32).unwrap().bytes().as_ptr(),owned[31].as_ptr());
assert_eq!(sorted.get(33).unwrap().bytes(),owned[30]);assert_eq!(sorted.get(33).unwrap().bytes().as_ptr(),owned[30].as_ptr());
assert_eq!(sorted.get(34).unwrap().bytes(),owned[29]);assert_eq!(sorted.get(34).unwrap().bytes().as_ptr(),owned[29].as_ptr());
assert_eq!(sorted.get(35).unwrap().bytes(),owned[28]);assert_eq!(sorted.get(35).unwrap().bytes().as_ptr(),owned[28].as_ptr());
assert_eq!(sorted.get(36).unwrap().bytes(),owned[27]);assert_eq!(sorted.get(36).unwrap().bytes().as_ptr(),owned[27].as_ptr());
assert_eq!(sorted.get(37).unwrap().bytes(),owned[26]);assert_eq!(sorted.get(37).unwrap().bytes().as_ptr(),owned[26].as_ptr());
assert_eq!(sorted.get(38).unwrap().bytes(),owned[25]);assert_eq!(sorted.get(38).unwrap().bytes().as_ptr(),owned[25].as_ptr());
assert_eq!(sorted.get(39).unwrap().bytes(),owned[24]);assert_eq!(sorted.get(39).unwrap().bytes().as_ptr(),owned[24].as_ptr());
assert_eq!(sorted.get(40).unwrap().bytes(),owned[23]);assert_eq!(sorted.get(40).unwrap().bytes().as_ptr(),owned[23].as_ptr());
assert_eq!(sorted.get(41).unwrap().bytes(),owned[22]);assert_eq!(sorted.get(41).unwrap().bytes().as_ptr(),owned[22].as_ptr());
assert_eq!(sorted.get(42).unwrap().bytes(),owned[21]);assert_eq!(sorted.get(42).unwrap().bytes().as_ptr(),owned[21].as_ptr());
assert_eq!(sorted.get(43).unwrap().bytes(),owned[20]);assert_eq!(sorted.get(43).unwrap().bytes().as_ptr(),owned[20].as_ptr());
assert_eq!(sorted.get(44).unwrap().bytes(),owned[19]);assert_eq!(sorted.get(44).unwrap().bytes().as_ptr(),owned[19].as_ptr());
assert_eq!(sorted.get(45).unwrap().bytes(),owned[18]);assert_eq!(sorted.get(45).unwrap().bytes().as_ptr(),owned[18].as_ptr());
assert_eq!(sorted.get(46).unwrap().bytes(),owned[17]);assert_eq!(sorted.get(46).unwrap().bytes().as_ptr(),owned[17].as_ptr());
assert_eq!(sorted.get(47).unwrap().bytes(),owned[16]);assert_eq!(sorted.get(47).unwrap().bytes().as_ptr(),owned[16].as_ptr());
assert_eq!(sorted.get(48).unwrap().bytes(),owned[15]);assert_eq!(sorted.get(48).unwrap().bytes().as_ptr(),owned[15].as_ptr());
assert_eq!(sorted.get(49).unwrap().bytes(),owned[14]);assert_eq!(sorted.get(49).unwrap().bytes().as_ptr(),owned[14].as_ptr());
assert_eq!(sorted.get(50).unwrap().bytes(),owned[13]);assert_eq!(sorted.get(50).unwrap().bytes().as_ptr(),owned[13].as_ptr());
assert_eq!(sorted.get(51).unwrap().bytes(),owned[12]);assert_eq!(sorted.get(51).unwrap().bytes().as_ptr(),owned[12].as_ptr());
assert_eq!(sorted.get(52).unwrap().bytes(),owned[11]);assert_eq!(sorted.get(52).unwrap().bytes().as_ptr(),owned[11].as_ptr());
assert_eq!(sorted.get(53).unwrap().bytes(),owned[10]);assert_eq!(sorted.get(53).unwrap().bytes().as_ptr(),owned[10].as_ptr());
assert_eq!(sorted.get(54).unwrap().bytes(),owned[9]);assert_eq!(sorted.get(54).unwrap().bytes().as_ptr(),owned[9].as_ptr());
assert_eq!(sorted.get(55).unwrap().bytes(),owned[8]);assert_eq!(sorted.get(55).unwrap().bytes().as_ptr(),owned[8].as_ptr());
assert_eq!(sorted.get(56).unwrap().bytes(),owned[7]);assert_eq!(sorted.get(56).unwrap().bytes().as_ptr(),owned[7].as_ptr());
assert_eq!(sorted.get(57).unwrap().bytes(),owned[6]);assert_eq!(sorted.get(57).unwrap().bytes().as_ptr(),owned[6].as_ptr());
assert_eq!(sorted.get(58).unwrap().bytes(),owned[5]);assert_eq!(sorted.get(58).unwrap().bytes().as_ptr(),owned[5].as_ptr());
assert_eq!(sorted.get(59).unwrap().bytes(),owned[4]);assert_eq!(sorted.get(59).unwrap().bytes().as_ptr(),owned[4].as_ptr());
assert_eq!(sorted.get(60).unwrap().bytes(),owned[3]);assert_eq!(sorted.get(60).unwrap().bytes().as_ptr(),owned[3].as_ptr());
assert_eq!(sorted.get(61).unwrap().bytes(),owned[2]);assert_eq!(sorted.get(61).unwrap().bytes().as_ptr(),owned[2].as_ptr());
assert_eq!(sorted.get(62).unwrap().bytes(),owned[1]);assert_eq!(sorted.get(62).unwrap().bytes().as_ptr(),owned[1].as_ptr());
assert_eq!(sorted.get(63).unwrap().bytes(),owned[0]);assert_eq!(sorted.get(63).unwrap().bytes().as_ptr(),owned[0].as_ptr());
drop(list);drop(values);assert_eq!(sorted.get(0).unwrap().bytes(),owned[63]);
assert_eq!(sorted.get(1).unwrap().bytes(),owned[62]);
assert_eq!(sorted.get(2).unwrap().bytes(),owned[61]);
assert_eq!(sorted.get(3).unwrap().bytes(),owned[60]);
assert_eq!(sorted.get(4).unwrap().bytes(),owned[59]);
assert_eq!(sorted.get(5).unwrap().bytes(),owned[58]);
assert_eq!(sorted.get(6).unwrap().bytes(),owned[57]);
assert_eq!(sorted.get(7).unwrap().bytes(),owned[56]);
assert_eq!(sorted.get(8).unwrap().bytes(),owned[55]);
assert_eq!(sorted.get(9).unwrap().bytes(),owned[54]);
assert_eq!(sorted.get(10).unwrap().bytes(),owned[53]);
assert_eq!(sorted.get(11).unwrap().bytes(),owned[52]);
assert_eq!(sorted.get(12).unwrap().bytes(),owned[51]);
assert_eq!(sorted.get(13).unwrap().bytes(),owned[50]);
assert_eq!(sorted.get(14).unwrap().bytes(),owned[49]);
assert_eq!(sorted.get(15).unwrap().bytes(),owned[48]);
assert_eq!(sorted.get(16).unwrap().bytes(),owned[47]);
assert_eq!(sorted.get(17).unwrap().bytes(),owned[46]);
assert_eq!(sorted.get(18).unwrap().bytes(),owned[45]);
assert_eq!(sorted.get(19).unwrap().bytes(),owned[44]);
assert_eq!(sorted.get(20).unwrap().bytes(),owned[43]);
assert_eq!(sorted.get(21).unwrap().bytes(),owned[42]);
assert_eq!(sorted.get(22).unwrap().bytes(),owned[41]);
assert_eq!(sorted.get(23).unwrap().bytes(),owned[40]);
assert_eq!(sorted.get(24).unwrap().bytes(),owned[39]);
assert_eq!(sorted.get(25).unwrap().bytes(),owned[38]);
assert_eq!(sorted.get(26).unwrap().bytes(),owned[37]);
assert_eq!(sorted.get(27).unwrap().bytes(),owned[36]);
assert_eq!(sorted.get(28).unwrap().bytes(),owned[35]);
assert_eq!(sorted.get(29).unwrap().bytes(),owned[34]);
assert_eq!(sorted.get(30).unwrap().bytes(),owned[33]);
assert_eq!(sorted.get(31).unwrap().bytes(),owned[32]);
assert_eq!(sorted.get(32).unwrap().bytes(),owned[31]);
assert_eq!(sorted.get(33).unwrap().bytes(),owned[30]);
assert_eq!(sorted.get(34).unwrap().bytes(),owned[29]);
assert_eq!(sorted.get(35).unwrap().bytes(),owned[28]);
assert_eq!(sorted.get(36).unwrap().bytes(),owned[27]);
assert_eq!(sorted.get(37).unwrap().bytes(),owned[26]);
assert_eq!(sorted.get(38).unwrap().bytes(),owned[25]);
assert_eq!(sorted.get(39).unwrap().bytes(),owned[24]);
assert_eq!(sorted.get(40).unwrap().bytes(),owned[23]);
assert_eq!(sorted.get(41).unwrap().bytes(),owned[22]);
assert_eq!(sorted.get(42).unwrap().bytes(),owned[21]);
assert_eq!(sorted.get(43).unwrap().bytes(),owned[20]);
assert_eq!(sorted.get(44).unwrap().bytes(),owned[19]);
assert_eq!(sorted.get(45).unwrap().bytes(),owned[18]);
assert_eq!(sorted.get(46).unwrap().bytes(),owned[17]);
assert_eq!(sorted.get(47).unwrap().bytes(),owned[16]);
assert_eq!(sorted.get(48).unwrap().bytes(),owned[15]);
assert_eq!(sorted.get(49).unwrap().bytes(),owned[14]);
assert_eq!(sorted.get(50).unwrap().bytes(),owned[13]);
assert_eq!(sorted.get(51).unwrap().bytes(),owned[12]);
assert_eq!(sorted.get(52).unwrap().bytes(),owned[11]);
assert_eq!(sorted.get(53).unwrap().bytes(),owned[10]);
assert_eq!(sorted.get(54).unwrap().bytes(),owned[9]);
assert_eq!(sorted.get(55).unwrap().bytes(),owned[8]);
assert_eq!(sorted.get(56).unwrap().bytes(),owned[7]);
assert_eq!(sorted.get(57).unwrap().bytes(),owned[6]);
assert_eq!(sorted.get(58).unwrap().bytes(),owned[5]);
assert_eq!(sorted.get(59).unwrap().bytes(),owned[4]);
assert_eq!(sorted.get(60).unwrap().bytes(),owned[3]);
assert_eq!(sorted.get(61).unwrap().bytes(),owned[2]);
assert_eq!(sorted.get(62).unwrap().bytes(),owned[1]);
assert_eq!(sorted.get(63).unwrap().bytes(),owned[0]);
assert_eq!(owned,before);}

#[test]
fn byte_max(){
let owned:Vec<Vec<u8>>=vec![bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),4);assert_eq!(list.is_empty(),false);assert_eq!(list.total_bytes(),4096);assert_eq!(list.is_strictly_increasing(),false);assert!(list.get(usize::MAX).is_none());
let query=bytes("f09f9880");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),false);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),1);assert_eq!(sorted.is_empty(),false);assert!(sorted.get(usize::MAX).is_none());
assert_eq!(sorted.get(0).unwrap().bytes(),owned[0]);assert_eq!(sorted.get(0).unwrap().bytes().as_ptr(),owned[0].as_ptr());
drop(list);drop(values);assert_eq!(sorted.get(0).unwrap().bytes(),owned[0]);
assert_eq!(owned,before);}

#[test]
fn zero_bytes_max(){
let owned:Vec<Vec<u8>>=vec![bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
let list=result.unwrap();assert_eq!(list.len(),64);assert_eq!(list.is_empty(),false);assert_eq!(list.total_bytes(),0);assert_eq!(list.is_strictly_increasing(),false);assert!(list.get(usize::MAX).is_none());
let query=bytes("");assert_eq!(list.contains(Text::from_bytes(&query).unwrap()),true);
let sorted=list.unique_sorted();assert_eq!(sorted.len(),1);assert_eq!(sorted.is_empty(),false);assert!(sorted.get(usize::MAX).is_none());
assert_eq!(sorted.get(0).unwrap().bytes(),owned[0]);assert_eq!(sorted.get(0).unwrap().bytes().as_ptr(),owned[0].as_ptr());
drop(list);drop(values);assert_eq!(sorted.get(0).unwrap().bytes(),owned[0]);
assert_eq!(owned,before);}

#[test]
fn count_over(){
let owned:Vec<Vec<u8>>=vec![bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1),bytes("").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
match result{Err(e)=>{assert_eq!(e.reason,"LIST_ITEMS");assert_eq!(e.index,64);},Ok(_)=>panic!("expected refusal")}
assert_eq!(owned,before);}

#[test]
fn bytes_over(){
let owned:Vec<Vec<u8>>=vec![bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("61").repeat(1)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
match result{Err(e)=>{assert_eq!(e.reason,"LIST_BYTES");assert_eq!(e.index,4);},Ok(_)=>panic!("expected refusal")}
assert_eq!(owned,before);}

#[test]
fn count_before_bytes(){
let owned:Vec<Vec<u8>>=vec![bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256),bytes("f09f9880").repeat(256)];
let before=owned.clone();let values:Vec<_>=owned.iter().map(|b|Text::from_bytes(b).unwrap()).collect();let result=TextList::new(&values);
match result{Err(e)=>{assert_eq!(e.reason,"LIST_ITEMS");assert_eq!(e.index,64);},Ok(_)=>panic!("expected refusal")}
assert_eq!(owned,before);}
