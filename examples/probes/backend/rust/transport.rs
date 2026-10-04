//! Complete JSON transport in a flat arena; no recursive parser or recursive drop.
use std::collections::BTreeMap;

pub const FRAME_LIMIT: usize = 1_048_576;
pub type ValueId = usize;

/// Decoded code points, including escaped isolated surrogate code units.
/// Raw UTF-8 surrogates are never accepted. Pairing follows JSON string decoding.
#[derive(Clone, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub struct JsonString(pub Vec<u32>);

impl JsonString {
    pub fn from_str(s: &str) -> Self { Self(s.chars().map(u32::from).collect()) }
    pub fn scalar_string(&self) -> Option<String> {
        self.0.iter().map(|&n| char::from_u32(n)).collect()
    }
}

#[derive(Debug)]
pub enum Value {
    Null,
    Bool(bool),
    Integer(String),
    Number(String),
    String(JsonString),
    Array(Vec<ValueId>),
    Object(BTreeMap<JsonString, ValueId>),
}

#[derive(Debug)]
pub struct Document { pub values: Vec<Value>, pub root: ValueId }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TransportError { Bounds, Json }

struct Frame { id: ValueId, state: u8, key: Option<JsonString> }
struct Parser<'a> { source: &'a str, pos: usize, values: Vec<Value>, stack: Vec<Frame> }

impl<'a> Parser<'a> {
    fn peek(&self) -> Option<u8> { self.source.as_bytes().get(self.pos).copied() }
    fn whitespace(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\t' | b'\r' | b'\n')) { self.pos += 1; }
    }
    fn hex4(&mut self) -> Result<u32, TransportError> {
        let mut n = 0;
        for _ in 0..4 {
            let b = self.peek().ok_or(TransportError::Json)?;
            n = n * 16 + match b {
                b'0'..=b'9' => (b - b'0') as u32,
                b'a'..=b'f' => (b - b'a' + 10) as u32,
                b'A'..=b'F' => (b - b'A' + 10) as u32,
                _ => return Err(TransportError::Json),
            };
            self.pos += 1;
        }
        Ok(n)
    }
    fn string(&mut self) -> Result<JsonString, TransportError> {
        if self.peek() != Some(b'"') { return Err(TransportError::Json); }
        self.pos += 1;
        let mut points = Vec::new();
        loop {
            let b = self.peek().ok_or(TransportError::Json)?;
            match b {
                b'"' => { self.pos += 1; return Ok(JsonString(points)); }
                0..=31 => return Err(TransportError::Json),
                b'\\' => {
                    self.pos += 1;
                    let escape = self.peek().ok_or(TransportError::Json)?;
                    self.pos += 1;
                    let mut point = match escape {
                        b'"' => 34, b'\\' => 92, b'/' => 47,
                        b'b' => 8, b'f' => 12, b'n' => 10, b'r' => 13, b't' => 9,
                        b'u' => self.hex4()?,
                        _ => return Err(TransportError::Json),
                    };
                    if (0xd800..=0xdbff).contains(&point)
                        && self.source.as_bytes().get(self.pos..self.pos + 2) == Some(b"\\u")
                    {
                        let saved = self.pos;
                        self.pos += 2;
                        let low = self.hex4()?;
                        if (0xdc00..=0xdfff).contains(&low) {
                            point = 0x10000 + ((point - 0xd800) << 10) + low - 0xdc00;
                        } else { self.pos = saved; }
                    }
                    points.push(point);
                }
                _ => {
                    let c = self.source[self.pos..].chars().next().ok_or(TransportError::Json)?;
                    self.pos += c.len_utf8();
                    points.push(u32::from(c));
                }
            }
        }
    }
    fn number(&mut self) -> Result<Value, TransportError> {
        let start = self.pos;
        if self.peek() == Some(b'-') { self.pos += 1; }
        match self.peek() {
            Some(b'0') => self.pos += 1,
            Some(b'1'..=b'9') => {
                self.pos += 1;
                while matches!(self.peek(), Some(b'0'..=b'9')) { self.pos += 1; }
            }
            _ => return Err(TransportError::Json),
        }
        let mut integer = true;
        if self.peek() == Some(b'.') {
            integer = false;
            self.pos += 1;
            let start_digits = self.pos;
            while matches!(self.peek(), Some(b'0'..=b'9')) { self.pos += 1; }
            if start_digits == self.pos { return Err(TransportError::Json); }
        }
        if matches!(self.peek(), Some(b'e' | b'E')) {
            integer = false;
            self.pos += 1;
            if matches!(self.peek(), Some(b'+' | b'-')) { self.pos += 1; }
            let start_digits = self.pos;
            while matches!(self.peek(), Some(b'0'..=b'9')) { self.pos += 1; }
            if start_digits == self.pos { return Err(TransportError::Json); }
        }
        let token = self.source[start..self.pos].to_owned();
        Ok(if integer { Value::Integer(token) } else { Value::Number(token) })
    }
    /// Attach immediately to the parent, then push a container frame if needed.
    fn value(&mut self) -> Result<ValueId, TransportError> {
        self.whitespace();
        let (value, container) = match self.peek() {
            Some(b'[') => { self.pos += 1; (Value::Array(Vec::new()), true) }
            Some(b'{') => { self.pos += 1; (Value::Object(BTreeMap::new()), true) }
            Some(b'"') => (Value::String(self.string()?), false),
            Some(b'-' | b'0'..=b'9') => (self.number()?, false),
            Some(b'n') if self.source[self.pos..].starts_with("null") => {
                self.pos += 4; (Value::Null, false)
            }
            Some(b't') if self.source[self.pos..].starts_with("true") => {
                self.pos += 4; (Value::Bool(true), false)
            }
            Some(b'f') if self.source[self.pos..].starts_with("false") => {
                self.pos += 5; (Value::Bool(false), false)
            }
            _ => return Err(TransportError::Json),
        };
        let id = self.values.len();
        self.values.push(value);
        if let Some(parent) = self.stack.last_mut() {
            match &mut self.values[parent.id] {
                Value::Array(items) => { items.push(id); parent.state = 1; }
                Value::Object(items) => {
                    let key = parent.key.take().ok_or(TransportError::Json)?;
                    if items.insert(key, id).is_some() { return Err(TransportError::Json); }
                    parent.state = 3;
                }
                _ => return Err(TransportError::Json),
            }
        }
        if container { self.stack.push(Frame { id, state: 0, key: None }); }
        Ok(id)
    }
    fn document(mut self) -> Result<Document, TransportError> {
        let root = self.value()?;
        while let Some(frame) = self.stack.last() {
            let id = frame.id;
            let state = frame.state;
            let array = matches!(&self.values[id], Value::Array(_));
            self.whitespace();
            let token = self.peek();
            if array {
                match state {
                    0 if token == Some(b']') => { self.pos += 1; self.stack.pop(); }
                    0 | 2 => { self.value()?; }
                    1 if token == Some(b']') => { self.pos += 1; self.stack.pop(); }
                    1 if token == Some(b',') => {
                        self.pos += 1; self.stack.last_mut().unwrap().state = 2;
                    }
                    _ => return Err(TransportError::Json),
                }
            } else {
                match state {
                    0 if token == Some(b'}') => { self.pos += 1; self.stack.pop(); }
                    0 | 4 => {
                        let key = self.string()?;
                        // Duplicates are transport failures even in unused/unknown fields.
                        if let Value::Object(items) = &self.values[id] {
                            if items.contains_key(&key) { return Err(TransportError::Json); }
                        }
                        let frame = self.stack.last_mut().unwrap();
                        frame.key = Some(key); frame.state = 1;
                    }
                    1 if token == Some(b':') => {
                        self.pos += 1; self.stack.last_mut().unwrap().state = 2;
                    }
                    2 => { self.value()?; }
                    3 if token == Some(b'}') => { self.pos += 1; self.stack.pop(); }
                    3 if token == Some(b',') => {
                        self.pos += 1; self.stack.last_mut().unwrap().state = 4;
                    }
                    _ => return Err(TransportError::Json),
                }
            }
        }
        self.whitespace();
        if self.pos != self.source.len() { return Err(TransportError::Json); }
        Ok(Document { values: self.values, root })
    }
}

pub fn parse(bytes: &[u8]) -> Result<Document, TransportError> {
    if bytes.len() > FRAME_LIMIT { return Err(TransportError::Bounds); }
    let source = std::str::from_utf8(bytes).map_err(|_| TransportError::Json)?;
    Parser { source, pos: 0, values: Vec::new(), stack: Vec::new() }.document()
}
