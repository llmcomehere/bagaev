//! Experimental data-only component source reader. No evaluation, effect or admission.
use std::collections::{BTreeMap,BTreeSet};
use crate::{canonical,sha256,transport,typed_record};
use crate::transport::{Document,Value,ValueId,JsonString,TransportError};
use crate::record_ir::Type;
#[derive(Debug)]
enum Failure{Refused(&'static str),Environment(&'static str)}
type R<T>=Result<T,Failure>;
fn no(c:&'static str)->Failure{Failure::Refused(c)}
fn need(b:bool,c:&'static str)->R<()>{if b{Ok(())}else{Err(no(c))}}
fn parse(bytes:&[u8])->R<Document>{
 let d=transport::parse(bytes).map_err(|e|no(match e{TransportError::Bounds=>"CS_BOUNDS",TransportError::Json=>"CS_FORMAT"}))?;
 need(d.values.len()<=10000,"CS_BOUNDS")?;let mut pending=vec![(d.root,1usize)];
 while let Some((id,depth))=pending.pop(){need(depth<=128,"CS_BOUNDS")?;match &d.values[id]{Value::Array(a)=>pending.extend(a.iter().map(|v|(*v,depth+1))),Value::Object(o)=>pending.extend(o.values().map(|v|(*v,depth+1))),_=>{}}}
 Ok(d)
}
fn object(d:&Document,id:ValueId)->R<&BTreeMap<JsonString,ValueId>>{match &d.values[id]{Value::Object(o)=>Ok(o),_=>Err(no("CS_FORMAT"))}}
fn exact<'a>(d:&'a Document,id:ValueId,keys:&[&str])->R<&'a BTreeMap<JsonString,ValueId>>{let o=object(d,id)?;need(o.len()==keys.len()&&keys.iter().all(|k|o.contains_key(&JsonString::from_str(k))),"CS_FORMAT")?;Ok(o)}
fn field(o:&BTreeMap<JsonString,ValueId>,name:&str)->R<ValueId>{o.get(&JsonString::from_str(name)).copied().ok_or(no("CS_FORMAT"))}
fn text(d:&Document,id:ValueId)->R<String>{match &d.values[id]{Value::String(s)=>s.scalar_string().ok_or(no("CS_FORMAT")),_=>Err(no("CS_FORMAT"))}}
fn ident(d:&Document,id:ValueId)->R<String>{let s=text(d,id)?;let b=s.as_bytes();need((1..=64).contains(&b.len())&&b[0].is_ascii_alphabetic()&&b[1..].iter().all(|c|c.is_ascii_alphanumeric()||matches!(*c,b'.'|b'_'|b'-')),"CS_FORMAT")?;Ok(s)}
fn meta_text(d:&Document,o:&BTreeMap<JsonString,ValueId>,name:&str)->R<String>{ident(d,field(o,name)?)}
fn strings(d:&Document,id:ValueId)->R<Vec<String>>{let a=match &d.values[id]{Value::Array(v)=>v,_=>return Err(no("CS_FORMAT"))};a.iter().map(|id|ident(d,*id)).collect::<R<Vec<_>>>()}
#[derive(Clone)]
struct Meta{name:String,operation:String,state:String,request:String,revision:String,entry:String,state_id:String,request_id:String,revision_field:String,replace:Vec<String>}
fn meta(d:&Document,o:&BTreeMap<JsonString,ValueId>,policy:bool)->R<Meta>{
 let ids=exact(d,field(o,"identity_binding")?,&["state","request"])?;
 Ok(Meta{name:meta_text(d,o,if policy{"component"}else{"name"})?,operation:meta_text(d,o,"operation")?,state:meta_text(d,o,"state_type")?,request:meta_text(d,o,"request_type")?,revision:meta_text(d,o,"revision_type")?,entry:if policy{String::new()}else{meta_text(d,o,"entry")?},state_id:meta_text(d,ids,"state")?,request_id:meta_text(d,ids,"request")?,revision_field:meta_text(d,o,"revision_binding")?,replace:strings(d,field(o,"replace_fields")?)?})
}
fn core(bytes:&[u8])->R<typed_record::CheckedSource>{match typed_record::check_source_v10(bytes).map_err(Failure::Environment)?{typed_record::SourceCheck::Checked(s)=>Ok(s),typed_record::SourceCheck::Refused{..}=>Err(no("CS_CORE"))}}
fn record(s:&typed_record::CheckedSource,name:&str)->R<usize>{s.record_definitions().iter().position(|r|r.name()==name).ok_or(no("CS_REFERENCE"))}
fn member(s:&typed_record::CheckedSource,index:usize,name:&str,reason:&'static str)->R<Type>{s.record_definitions()[index].fields().iter().find(|(n,_)|n==name).map(|(_,t)|*t).ok_or(no(reason))}
type Closure=BTreeMap<String,BTreeMap<String,String>>;
fn owned(s:&typed_record::CheckedSource,d:&Document,records:ValueId,roots:&[usize])->R<Closure>{
 let raw=object(d,records)?;let mut pending=roots.to_vec();let mut visited=BTreeSet::new();let mut out=BTreeMap::new();
 while let Some(i)=pending.pop(){if !visited.insert(i){continue;}let r=&s.record_definitions()[i];let descriptor=object(d,*raw.get(&JsonString::from_str(r.name())).ok_or(no("CS_OWNED"))?)?;let mut fields=BTreeMap::new();
  for (name,t) in r.fields(){let value=*descriptor.get(&JsonString::from_str(name)).ok_or(no("CS_OWNED"))?;need(matches!(&d.values[value],Value::String(_)),"CS_OWNED")?;
   let ty=match *t{Type::Int64=>"Int64".to_owned(),Type::Bool=>"Bool".to_owned(),Type::Text=>"Text".to_owned(),Type::OptionInt64=>"OptionInt64".to_owned(),Type::TextList=>"TextList".to_owned(),Type::Record(n)=>{pending.push(n as usize);s.record_definitions()[n as usize].name().to_owned()},_=>return Err(no("CS_OWNED"))};fields.insert(name.clone(),ty);
  }out.insert(r.name().to_owned(),fields);
 }Ok(out)
}
struct Layout{types:Closure,preserve:Vec<String>}
fn layout(m:&Meta,s:&typed_record::CheckedSource,d:&Document,records:ValueId,check_entry:bool)->R<Layout>{
 let state=record(s,&m.state)?;let request=record(s,&m.request)?;let revision=record(s,&m.revision)?;
 let types=owned(s,d,records,&[state,request,revision])?;
 if check_entry{let f=s.functions().iter().find(|f|f.name()==m.entry).ok_or(no("CS_REFERENCE"))?;need(s.functions()[s.entry()].name()==m.entry&&f.parameters().len()==2&&f.parameters()[0].ty()==Type::Record(state as u8)&&f.parameters()[1].ty()==Type::Record(request as u8)&&f.result()==Type::Record(state as u8),"CS_SIGNATURE")?;}
 let id1=member(s,state,&m.state_id,"CS_IDENTITY")?;let id2=member(s,request,&m.request_id,"CS_IDENTITY")?;need(id1==id2&&matches!(id1,Type::Record(_)),"CS_IDENTITY")?;
 need(member(s,request,&m.revision_field,"CS_REVISION")?==Type::Record(revision as u8),"CS_REVISION")?;let rev=s.record_definitions()[revision].fields();need(rev.len()==1&&rev[0].0=="value"&&rev[0].1==Type::Int64,"CS_REVISION")?;
 let fields=s.record_definitions()[state].fields();need(!m.replace.is_empty()&&m.replace.len()<=8&&m.replace.windows(2).all(|p|p[0]<p[1]),"CS_EFFECT")?;need(m.replace.iter().all(|n|n!=&m.state_id&&fields.iter().any(|(f,_)|f==n)),"CS_EFFECT")?;
 let preserve=fields.iter().filter(|(name,_)|!m.replace.contains(name)).map(|(n,_)|n.clone()).collect();Ok(Layout{types,preserve})
}
/// Construction stays private; descriptive checking does not admit execution.
pub struct CheckedComponent{source:typed_record::CheckedSource,meta:Meta,layout:Layout,identity:String}
fn checked(bytes:&[u8])->R<CheckedComponent>{
 let d=parse(bytes)?;let root=exact(&d,d.root,&["schema","program","component"])?;need(text(&d,field(root,"schema")?)?=="bagaev-component-source/1","CS_VERSION")?;
 let definition=exact(&d,field(root,"component")?,&["name","operation","state_type","request_type","revision_type","entry","identity_binding","revision_binding","replace_fields"])?;let m=meta(&d,definition,false)?;
 let program=field(root,"program")?;let pure=canonical::program_bytes(&d,program).map_err(|_|no("CS_CORE"))?;let source=core(&pure)?;
 let records=field(object(&d,program)?,"records")?;let l=layout(&m,&source,&d,records,true)?;
 let canonical=canonical::program_bytes(&d,d.root).map_err(|_|Failure::Environment("checked component canonical form"))?;
 Ok(CheckedComponent{source,meta:m,layout:l,identity:sha256::digest(&canonical)})
}
fn policy_inner(c:&CheckedComponent,bytes:&[u8])->R<bool>{
 let d=parse(bytes)?;let root=exact(&d,d.root,&["schema","component","operation","state_type","request_type","revision_type","identity_binding","revision_binding","replace_fields","records"])?;need(text(&d,field(root,"schema")?)?=="bagaev-component-policy/1","CS_FORMAT")?;let m=meta(&d,root,true)?;
 let records=field(root,"records")?;let record_bytes=canonical::program_bytes(&d,records).map_err(|_|no("CS_FORMAT"))?;
 let mut pure=b"{\"schema\":\"bagaev-typed-record/10\",\"records\":".to_vec();pure.extend(record_bytes);pure.extend_from_slice(b",\"lists\":{},\"variants\":{},\"entry\":\"main\",\"functions\":{\"main\":{\"params\":[],\"result\":\"Bool\",\"body\":[\"bool\",true]}}}");
 let s=core(&pure)?;let l=layout(&m,&s,&d,records,false)?;need(l.types.len()==object(&d,records)?.len(),"CS_FORMAT")?;
 Ok(m.name==c.meta.name&&m.operation==c.meta.operation&&m.state==c.meta.state&&m.request==c.meta.request&&m.revision==c.meta.revision&&m.state_id==c.meta.state_id&&m.request_id==c.meta.request_id&&m.revision_field==c.meta.revision_field&&l.types==c.layout.types&&c.meta.replace.iter().all(|n|m.replace.contains(n)))
}
fn string(s:&str,out:&mut String){canonical::quote(s,out)}
fn array(a:&[String],out:&mut String){out.push('[');for(i,s)in a.iter().enumerate(){if i>0{out.push(',');}string(s,out);}out.push(']');}
fn refused(reason:&str,policy:bool)->Vec<u8>{let mut out=String::from("{\"schema\":\"bagaev-component-check/1\",\"status\":");string(if policy{"source-checked-policy-refused"}else{"refused"},&mut out);out.push_str(",\"reason\":");string(reason,&mut out);out.push_str(",\"execution_admission\":false}\n");out.into_bytes()}
fn bare_digest(s:&str)->Result<&str,&'static str>{let h=s.strip_prefix("sha256:").ok_or("digest prefix")?;if h.len()!=64||!h.bytes().all(|b|b.is_ascii_digit()||(b'a'..=b'f').contains(&b)){return Err("digest encoding");}Ok(h)}
fn wire(c:&CheckedComponent,policy_digest:Option<&str>)->Result<Vec<u8>,&'static str>{let mut o=String::from("{\"schema\":\"bagaev-component-check/1\",\"status\":\"checked\",\"execution_admission\":false");
 for(k,v)in [("name",c.meta.name.as_str()),("operation",c.meta.operation.as_str()),("source_sha256",bare_digest(&c.identity)?),("program_sha256",bare_digest(c.source.identity())?),("state_type",c.meta.state.as_str()),("request_type",c.meta.request.as_str()),("revision_type",c.meta.revision.as_str()),("revision_binding",c.meta.revision_field.as_str())]{o.push(',');string(k,&mut o);o.push(':');string(v,&mut o);}
 o.push_str(",\"identity_binding\":{\"state\":");string(&c.meta.state_id,&mut o);o.push_str(",\"request\":");string(&c.meta.request_id,&mut o);o.push_str("},\"replace_fields\":");array(&c.meta.replace,&mut o);o.push_str(",\"preserve_fields\":");array(&c.layout.preserve,&mut o);o.push_str(",\"policy_compatible\":");o.push_str(if policy_digest.is_some(){"true"}else{"null"});o.push_str(",\"policy_sha256\":");if let Some(h)=policy_digest{string(bare_digest(h)?,&mut o);}else{o.push_str("null");}o.push_str("}\n");Ok(o.into_bytes())}
/// Parses/checks data only. No candidate text, function or policy is executed.
pub fn process(source:&[u8],policy:Option<&[u8]>)->Result<Vec<u8>,&'static str>{
 let c=match checked(source){Ok(c)=>c,Err(Failure::Refused(r))=>return Ok(refused(r,false)),Err(Failure::Environment(e))=>return Err(e)};
 if let Some(p)=policy{match policy_inner(&c,p){Ok(true)=>{},Ok(false)=>return Ok(refused("CS_POLICY",true)),Err(Failure::Refused(_))=>return Ok(refused("CS_POLICY_FORMAT",true)),Err(Failure::Environment(e))=>return Err(e)}}
 let digest=if let Some(p)=policy{let d=transport::parse(p).map_err(|_|"checked policy parsing")?;let bytes=canonical::program_bytes(&d,d.root)?;Some(sha256::digest(&bytes))}else{None};
 wire(&c,digest.as_deref())
}
