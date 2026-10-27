"""Интерфейс встроенных модулей std для проверки (spec/language/checking.md §2).

Модули записаны на bagaev. Функция с телом `{}` — примитив машины `std.<модуль>.<имя>@1`
(spec/runtime/machine.md); функции высшего порядка написаны на bagaev поверх примитивов и проверяются
как обычный код. Состав — каталог STDLIB-API-0.1 (spec/stdlib/api.md) с заменами r25,
перечисленными в examples/README.md: обобщённые map/fold/map_error с эффект-переменной (D70),
std.store по таблицам (D81, EFF-07), test.expect/expect_equal, json.quote. Типы — spec/stdlib/types.md;
варианты с полезной нагрузкой Unit записаны вариантами без нагрузки.
"""

STD_SOURCES: dict[str, str] = {
    "std.bool": """
module std.bool
""",                                   # STD-001 bool.not не выразима: not — зарезервированное слово (SURF-34)
    "std.i64": """
module std.i64
pub type ArithmeticError = enum { Overflow, DivisionByZero }
pub type ParseSyntaxReason = enum { Empty, SignOnly, LeadingZero, InvalidDigit }
pub type ParseSyntax = record { index: Int64, reason: ParseSyntaxReason }
pub type ParseIntError = enum { InvalidSyntax(ParseSyntax), OutOfRange }
pub fn eq(a: Int64, b: Int64) -> Bool {}
pub fn lt(a: Int64, b: Int64) -> Bool {}
pub fn add(a: Int64, b: Int64) -> Result<Int64, ArithmeticError> {}
pub fn sub(a: Int64, b: Int64) -> Result<Int64, ArithmeticError> {}
pub fn mul(a: Int64, b: Int64) -> Result<Int64, ArithmeticError> {}
pub fn div(a: Int64, b: Int64) -> Result<Int64, ArithmeticError> {}
pub fn rem(a: Int64, b: Int64) -> Result<Int64, ArithmeticError> {}
pub fn neg(a: Int64) -> Result<Int64, ArithmeticError> {}
pub fn parse_decimal(s: String) -> Result<Int64, ParseIntError> {}
pub fn format_decimal(n: Int64) -> String {}
""",
    "std.value": """
module std.value
pub fn equal<T: Eq>(a: T, b: T) -> Bool {}
pub fn compare<T: Key>(a: T, b: T) -> Int64 {}
""",
    "std.data": """
module std.data
pub type BoundsError = record { length: Int64, start: Int64, end: Int64 }
pub type ScalarError = record { index: Int64, value: Int64 }
pub type OctetError = record { index: Int64, value: Int64 }
pub type DataErrorCode = enum {
  DuplicateKey, Utf8Leading, Utf8Continuation, Utf8Overlong, Utf8Surrogate, Utf8Range, Utf8Truncated,
  UnexpectedEnd, ContextMismatch, InvalidEncoding, UnknownVariant, NonCanonicalMap, TrailingBytes,
}
pub type DataError = record { code: DataErrorCode, first: Int64, second: Int64 }
""",
    "std.option": """
module std.option
pub fn is_some<T>(o: Option<T>) -> Bool {}
pub fn value_or<T>(o: Option<T>, default: T) -> T {}
pub fn map<A, B, !e>(o: Option<A>, f: fn(A) -> B uses e) -> Option<B> uses e {
  match o {
    None => None,
    Some(x) => Some(f(x)),
  }
}
""",
    "std.result": """
module std.result
pub fn is_ok<T, E>(r: Result<T, E>) -> Bool {}
pub fn map<A, B, E, !e>(r: Result<A, E>, f: fn(A) -> B uses e) -> Result<B, E> uses e {
  match r {
    Ok(x) => Ok(f(x)),
    Err(y) => Err(y),
  }
}
pub fn map_error<T, E, F, !e>(r: Result<T, E>, f: fn(E) -> F uses e) -> Result<T, F> uses e {
  match r {
    Ok(x) => Ok(x),
    Err(y) => Err(f(y)),
  }
}
""",
    "std.seq": """
module std.seq
use std.data.{BoundsError}
pub fn length<T>(xs: Seq<T>) -> Int64 {}
pub fn get<T>(xs: Seq<T>, i: Int64) -> Option<T> {}
pub fn append<T>(xs: Seq<T>, x: T) -> Seq<T> {}
pub fn concat<T>(a: Seq<T>, b: Seq<T>) -> Seq<T> {}
pub fn slice<T>(xs: Seq<T>, start: Int64, end: Int64) -> Result<Seq<T>, BoundsError> {}
pub fn map<T, U, !e>(xs: Seq<T>, f: fn(T) -> U uses e) -> Seq<U> uses e {
  map_from(xs, f, 0, [])
}
fn map_from<T, U, !e>(xs: Seq<T>, f: fn(T) -> U uses e, i: Int64, acc: Seq<U>) -> Seq<U> uses e {
  match get(xs, i) {
    None => acc,
    Some(x) => map_from(xs, f, i + 1, append(acc, f(x))),
  }
}
pub fn fold<T, A, !e>(xs: Seq<T>, init: A, f: fn(A, T) -> A uses e) -> A uses e {
  fold_from(xs, init, f, 0)
}
fn fold_from<T, A, !e>(xs: Seq<T>, acc: A, f: fn(A, T) -> A uses e, i: Int64) -> A uses e {
  match get(xs, i) {
    None => acc,
    Some(x) => fold_from(xs, f(acc, x), f, i + 1),
  }
}
""",
    "std.map": """
module std.map
use std.data.{DataError}
pub type Entry<K, V> = record { key: K, value: V }
pub fn build<K: Key, V>(entries: Seq<Entry<K, V>>) -> Result<Map<K, V>, DataError> {}
pub fn get<K: Key, V>(m: Map<K, V>, k: K) -> Option<V> {}
pub fn length<K: Key, V>(m: Map<K, V>) -> Int64 {}
pub fn entries<K: Key, V>(m: Map<K, V>) -> Seq<Entry<K, V>> {}
pub fn put<K: Key, V>(m: Map<K, V>, k: K, v: V) -> Map<K, V> {}
pub fn remove<K: Key, V>(m: Map<K, V>, k: K) -> Map<K, V> {}
""",
    "std.string": """
module std.string
use std.data.{BoundsError, ScalarError}
pub fn scalar_length(s: String) -> Int64 {}
pub fn scalar_get(s: String, i: Int64) -> Option<Int64> {}
pub fn slice(s: String, start: Int64, end: Int64) -> Result<String, BoundsError> {}
pub fn concat(a: String, b: String) -> String {}
pub fn from_scalars(xs: Seq<Int64>) -> Result<String, ScalarError> {}
pub fn to_scalars(s: String) -> Seq<Int64> {}
""",
    "std.bytes": """
module std.bytes
use std.data.{BoundsError, OctetError}
pub fn length(b: Bytes) -> Int64 {}
pub fn get(b: Bytes, i: Int64) -> Option<Int64> {}
pub fn slice(b: Bytes, start: Int64, end: Int64) -> Result<Bytes, BoundsError> {}
pub fn concat(a: Bytes, b: Bytes) -> Bytes {}
pub fn from_octets(xs: Seq<Int64>) -> Result<Bytes, OctetError> {}
pub fn to_octets(b: Bytes) -> Seq<Int64> {}
""",
    "std.utf8": """
module std.utf8
use std.data.{DataError}
pub fn encode(s: String) -> Bytes {}
pub fn decode(b: Bytes) -> Result<String, DataError> {}
""",
    "std.codec": """
module std.codec
use std.data.{DataError}
pub fn encode<T: Persistable>(v: T) -> Bytes {}
pub fn decode<T: Persistable>(b: Bytes) -> Result<T, DataError> {}
""",
    "std.json": """
module std.json
pub fn quote(s: String) -> String {}
""",
    "std.test": """
module std.test
pub fn expect(label: String, condition: Bool) -> () {}
pub fn expect_equal<T: Eq>(label: String, actual: T, expected: T) -> () {}
""",
    "std.store": """
module std.store
pub fn get<K: Key, V>(t: Table<K, V>, k: K) -> Option<V> uses { reads t } {}
pub fn contains<K: Key, V>(t: Table<K, V>, k: K) -> Bool uses { reads t } {}
pub fn all<K: Key, V>(t: Table<K, V>) -> Map<K, V> uses { reads t } {}
pub fn put<K: Key, V>(t: Table<K, V>, k: K, v: V) -> () uses { writes t } {}
pub fn remove<K: Key, V>(t: Table<K, V>, k: K) -> () uses { writes t } {}
pub fn replace_all<K: Key, V>(t: Table<K, V>, m: Map<K, V>) -> () uses { writes t } {}
""",
}
