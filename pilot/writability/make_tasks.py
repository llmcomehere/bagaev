#!/usr/bin/env python3
"""Задачи пробника пишемости (план, Ф2; протокол — protocol.md). Источник истины для tasks/.

Каждая задача одинакова по смыслу для двух плеч:
- C — bagaev, модель видит только spec/language/guide-llm.md;
- T — TypeScript strict.

Для каждой задачи и плеча пишутся: условие и требуемый интерфейс (task.md), файлы контекста,
эталонное решение (reference/, модели не показывается) и скрытая проверка интерфейса (probe/):
модуль, который вызывает требуемые функции с точными типами, или ожидаемые сигнатуры точек входа и связи.
Метка `@@` в bagaev-контексте и проверке заменяется детерминированным @id.

  python3 pilot/writability/make_tasks.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "tasks"
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"
TASKS: list[dict] = []

TS_RESULT = """export type Result<T, E> = { readonly ok: true; readonly value: T } | { readonly ok: false; readonly error: E };
export const ok = <T, E = never>(value: T): Result<T, E> => ({ ok: true, value });
export const err = <E, T = never>(error: E): Result<T, E> => ({ ok: false, error });
"""


def with_ids(tag: str, src: str) -> str:
    parts = src.split("@@")
    out = []
    for i, part in enumerate(parts):
        out.append(part)
        if i < len(parts) - 1:
            h = int(hashlib.sha256(f"{tag}/{i}".encode()).hexdigest(), 16)
            out.append('@id("' + "".join(CROCKFORD[(h >> (5 * j)) & 31] for j in range(6)) + '")')
    return "".join(out)


def task(tid: str, kind: str, title: str, statement: str, *, c_target: str, c_interface: str, c_reference: str,
         t_target: str, t_interface: str, t_reference: str, c_probe: str | None = None, t_probe: str | None = None,
         c_context: dict | None = None, t_context: dict | None = None, c_expect: dict | None = None):
    TASKS.append(dict(id=tid, kind=kind, title=title, statement=statement, c_target=c_target, c_interface=c_interface,
                      c_reference=c_reference, c_probe=c_probe, c_context=c_context or {}, c_expect=c_expect or {},
                      t_target=t_target, t_interface=t_interface, t_reference=t_reference, t_probe=t_probe,
                      t_context=t_context or {}))


def c_probe(uses: str, body: str) -> str:
    return "@@\nmodule probe\n\n" + uses + "\n\n" + body


# ---------------------------------------------------------------------------- чистые функции
task("W01", "write", "Сумма", "Напишите функцию `sum`: сумма всех элементов последовательности целых; для пустой — 0.",
     c_target="main.bag", c_interface="module main\npub fn sum(xs: Seq<Int64>) -> Int64",
     c_reference="""module main

use std.seq

pub fn sum(xs: Seq<Int64>) -> Int64 {
  seq.fold(xs, 0, fn(acc, x) => acc + x)
}
""", c_probe=c_probe("use main", "@@\nfn check(xs: Seq<Int64>) -> Int64 {\n  main.sum(xs)\n}\n"),
     t_target="main.ts", t_interface="export function sum(xs: readonly number[]): number",
     t_reference="export function sum(xs: readonly number[]): number {\n  return xs.reduce((a, x) => a + x, 0);\n}\n",
     t_probe='import { sum } from "./main";\nconst f: (xs: readonly number[]) => number = sum;\nvoid f;\n')

task("W02", "write", "Максимум или значение по умолчанию",
     "Напишите `max_or`: наибольший элемент последовательности; для пустой — значение `d`.",
     c_target="main.bag", c_interface="module main\npub fn max_or(xs: Seq<Int64>, d: Int64) -> Int64",
     c_reference="""module main

use std.seq

pub fn max_or(xs: Seq<Int64>, d: Int64) -> Int64 {
  match seq.get(xs, 0) {
    None => d,
    Some(first) => seq.fold(xs, first, fn(m, x) => if x > m {
      x
    } else {
      m
    }),
  }
}
""", c_probe=c_probe("use main", "@@\nfn check(xs: Seq<Int64>) -> Int64 {\n  main.max_or(xs, 0)\n}\n"),
     t_target="main.ts", t_interface="export function maxOr(xs: readonly number[], d: number): number",
     t_reference="export function maxOr(xs: readonly number[], d: number): number {\n"
                 "  return xs.length === 0 ? d : xs.reduce((m, x) => (x > m ? x : m), xs[0]!);\n}\n",
     t_probe='import { maxOr } from "./main";\nconst f: (xs: readonly number[], d: number) => number = maxOr;\nvoid f;\n')

task("W03", "write", "Фигуры", """Определите типы и функцию площади:
- запись `Size` с целыми полями `w` и `h`;
- перечисление `Shape` с вариантами `Circle` (радиус, целое) и `Rect` (размер `Size`);
- функция `area`: для круга `3 * r * r`, для прямоугольника `w * h`.""",
     c_target="main.bag", c_interface="""module main
pub type Size = record { w: Int64, h: Int64 }
pub type Shape = enum { Circle(Int64), Rect(Size) }
pub fn area(s: Shape) -> Int64""",
     c_reference="""module main

pub type Size = record {
  w: Int64,
  h: Int64,
}

pub type Shape = enum {
  Circle(Int64),
  Rect(Size),
}

pub fn area(s: Shape) -> Int64 {
  match s {
    Shape.Circle(r) => 3 * r * r,
    Shape.Rect(z) => z.w * z.h,
  }
}
""", c_probe=c_probe("use main", "@@\nfn check() -> Int64 {\n"
                                "  main.area(main.Shape.Circle(2)) + main.area(main.Shape.Rect(main.Size { w: 2, h: 3 }))\n}\n"),
     t_target="main.ts", t_interface="""export interface Size { readonly w: number; readonly h: number }
export type Shape = { readonly kind: "circle"; readonly r: number } | { readonly kind: "rect"; readonly size: Size }
export function area(s: Shape): number""",
     t_reference="""export interface Size { readonly w: number; readonly h: number }
export type Shape = { readonly kind: "circle"; readonly r: number } | { readonly kind: "rect"; readonly size: Size };
export function area(s: Shape): number {
  switch (s.kind) {
    case "circle": return 3 * s.r * s.r;
    case "rect": return s.size.w * s.size.h;
  }
}
""", t_probe='import { area, Shape } from "./main";\nconst s: Shape = { kind: "rect", size: { w: 2, h: 3 } };\n'
             'const n: number = area(s) + area({ kind: "circle", r: 2 });\nvoid n;\n')

task("W04", "write", "Сложение десятичных строк", """Напишите `add_decimal`: разобрать две строки как десятичные целые и сложить.
- Ошибки — перечисление `AddError`: `BadNumber` со строкой, которую не удалось разобрать, и `Overflow` (переполнение суммы).
- Используйте разбор и проверяемое сложение стандартной библиотеки.""",
     c_target="main.bag", c_interface="""module main
pub type AddError = enum { BadNumber(String), Overflow }
pub fn add_decimal(a: String, b: String) -> Result<Int64, AddError>""",
     c_reference="""module main

use std.i64

pub type AddError = enum {
  BadNumber(String),
  Overflow,
}

pub fn add_decimal(a: String, b: String) -> Result<Int64, AddError> {
  let x = parse(a)?;
  let y = parse(b)?;
  match i64.add(x, y) {
    Ok(v) => Ok(v),
    Err(_) => Err(AddError.Overflow),
  }
}

fn parse(s: String) -> Result<Int64, AddError> {
  match i64.parse_decimal(s) {
    Ok(v) => Ok(v),
    Err(_) => Err(AddError.BadNumber(s)),
  }
}
""", c_probe=c_probe("use main", """@@
fn check() -> Result<Int64, main.AddError> {
  main.add_decimal("1", "2")
}

@@
fn names(e: main.AddError) -> String {
  match e {
    main.AddError.BadNumber(s) => s,
    main.AddError.Overflow => "overflow",
  }
}
"""),
     t_target="main.ts", t_context={"result.ts": TS_RESULT},
     t_interface="""import { Result } from "./result";
export type AddError = { readonly kind: "bad-number"; readonly text: string } | { readonly kind: "overflow" }
export function addDecimal(a: string, b: string): Result<number, AddError>""",
     t_reference="""import { Result, ok, err } from "./result";
export type AddError = { readonly kind: "bad-number"; readonly text: string } | { readonly kind: "overflow" };
function parse(s: string): Result<number, AddError> {
  if (!/^-?(0|[1-9][0-9]*)$/.test(s)) return err({ kind: "bad-number", text: s });
  const v = Number(s);
  return Number.isSafeInteger(v) ? ok(v) : err({ kind: "bad-number", text: s });
}
export function addDecimal(a: string, b: string): Result<number, AddError> {
  const x = parse(a);
  if (!x.ok) return x;
  const y = parse(b);
  if (!y.ok) return y;
  const s = x.value + y.value;
  return Number.isSafeInteger(s) ? ok(s) : err({ kind: "overflow" });
}
""", t_probe='import { addDecimal, AddError } from "./main";\nimport { Result } from "./result";\n'
             'const r: Result<number, AddError> = addDecimal("1", "2");\nvoid r;\n')

task("W05", "write", "Подсчёт по условию", "Напишите обобщённую `count_if`: сколько элементов последовательности удовлетворяют предикату `p`.",
     c_target="main.bag", c_interface="module main\npub fn count_if<T>(xs: Seq<T>, p: fn(T) -> Bool) -> Int64",
     c_reference="""module main

use std.seq

pub fn count_if<T>(xs: Seq<T>, p: fn(T) -> Bool) -> Int64 {
  seq.fold(xs, 0, fn(n, x) => if p(x) {
    n + 1
  } else {
    n
  })
}
""", c_probe=c_probe("use main", "@@\nfn check(xs: Seq<String>) -> Int64 {\n  main.count_if(xs, fn(s) => s == \"a\")\n}\n"),
     t_target="main.ts", t_interface="export function countIf<T>(xs: readonly T[], p: (x: T) => boolean): number",
     t_reference="export function countIf<T>(xs: readonly T[], p: (x: T) => boolean): number {\n"
                 "  return xs.filter(p).length;\n}\n",
     t_probe='import { countIf } from "./main";\nconst n: number = countIf(["a", "b"], (s) => s === "a");\nvoid n;\n')

task("W06", "write", "Обобщённое отображение с эффектами",
     """Напишите `map_all`: применить `f` к каждому элементу и вернуть результаты в том же порядке. Функция `f` может иметь эффекты (например, читать таблицу) — `map_all` должна быть полиморфна по ним. Не используйте `seq.map`: напишите обход сами.""",
     c_target="main.bag", c_interface="module main\npub fn map_all<T, U, !e>(xs: Seq<T>, f: fn(T) -> U uses e) -> Seq<U> uses e",
     c_reference="""module main

use std.seq

pub fn map_all<T, U, !e>(xs: Seq<T>, f: fn(T) -> U uses e) -> Seq<U>
  uses e
{
  go(xs, f, 0, [])
}

fn go<T, U, !e>(xs: Seq<T>, f: fn(T) -> U uses e, i: Int64, out: Seq<U>) -> Seq<U>
  uses e
{
  match seq.get(xs, i) {
    None => out,
    Some(x) => go(xs, f, i + 1, seq.append(out, f(x))),
  }
}
""", c_probe=c_probe("use main\nuse std.store", """@@
store P {
  @@ table t: Map<Int64, Int64>
}

@@
fn pure(xs: Seq<Int64>) -> Seq<Int64> {
  main.map_all(xs, fn(x) => x + 1)
}

@@
fn reading(xs: Seq<Int64>) -> Seq<Option<Int64>>
  uses { reads P.t }
{
  main.map_all(xs, fn(k) => store.get(P.t, k))
}
"""),
     t_target="main.ts", t_interface="export function mapAll<T, U>(xs: readonly T[], f: (x: T) => U): U[]",
     t_reference="export function mapAll<T, U>(xs: readonly T[], f: (x: T) => U): U[] {\n"
                 "  const out: U[] = [];\n  for (const x of xs) out.push(f(x));\n  return out;\n}\n",
     t_probe='import { mapAll } from "./main";\nconst r: string[] = mapAll([1, 2], (x) => String(x));\nvoid r;\n')

task("W07", "write", "Частоты слов", "Напишите `frequencies`: для каждого слова — сколько раз оно встречается.",
     c_target="main.bag", c_interface="module main\npub fn frequencies(words: Seq<String>) -> Map<String, Int64>",
     c_reference="""module main

use std.seq
use std.map
use std.option

pub fn frequencies(words: Seq<String>) -> Map<String, Int64> {
  seq.fold(words, Map {}, fn(m, w) => map.put(m, w, option.value_or(map.get(m, w), 0) + 1))
}
""", c_probe=c_probe("use main", "@@\nfn check(ws: Seq<String>) -> Map<String, Int64> {\n  main.frequencies(ws)\n}\n"),
     t_target="main.ts", t_interface="export function frequencies(words: readonly string[]): ReadonlyMap<string, number>",
     t_reference="export function frequencies(words: readonly string[]): ReadonlyMap<string, number> {\n"
                 "  const m = new Map<string, number>();\n  for (const w of words) m.set(w, (m.get(w) ?? 0) + 1);\n"
                 "  return m;\n}\n",
     t_probe='import { frequencies } from "./main";\nconst m: ReadonlyMap<string, number> = frequencies(["a"]);\nvoid m;\n')

task("W08", "write", "Адрес почты как непрозрачный тип", """Определите непрозрачный тип `Email` поверх строки:
- `make_email(s)` возвращает значение, только если в строке есть символ `@` (код 64), иначе — отсутствие значения;
- `email_text(e)` возвращает исходную строку.
Код вне модуля не должен иметь возможности создать `Email` в обход проверки.""",
     c_target="main.bag", c_interface="""module main
pub type Email = opaque String
pub fn make_email(s: String) -> Option<Email>
pub fn email_text(e: Email) -> String""",
     c_reference="""module main

use std.string

pub type Email = opaque String

pub fn make_email(s: String) -> Option<Email> {
  if has_at(s, 0) {
    Some(Email(s))
  } else {
    None
  }
}

pub fn email_text(e: Email) -> String {
  match e {
    Email(s) => s,
  }
}

fn has_at(s: String, i: Int64) -> Bool {
  match string.scalar_get(s, i) {
    None => false,
    Some(c) => c == 64 or has_at(s, i + 1),
  }
}
""", c_probe=c_probe("use main", "@@\nfn check(s: String) -> String {\n  match main.make_email(s) {\n"
                                "    Some(e) => main.email_text(e),\n    None => \"\",\n  }\n}\n"),
     t_target="main.ts", t_interface="""export type Email = string & { readonly __brand: "Email" }
export function makeEmail(s: string): Email | undefined
export function emailText(e: Email): string""",
     t_reference="""export type Email = string & { readonly __brand: "Email" };
export function makeEmail(s: string): Email | undefined {
  return s.includes("@") ? (s as Email) : undefined;
}
export function emailText(e: Email): string {
  return e;
}
""", t_probe='import { makeEmail, emailText } from "./main";\nconst e = makeEmail("a@b");\n'
             'const s: string = e === undefined ? "" : emailText(e);\nvoid s;\n')

task("W09", "write", "Связный список", """Определите рекурсивный список целых и две функции:
- перечисление `IntList` с вариантами `Nil` и `Cons` (узел `IntNode`), запись `IntNode` с полями `head: Int64` и `tail: IntList`;
- `list_sum(l)` — сумма элементов;
- `from_seq(xs)` — список с теми же элементами в том же порядке.""",
     c_target="main.bag", c_interface="""module main
pub type IntList = enum { Nil, Cons(IntNode) }
pub type IntNode = record { head: Int64, tail: IntList }
pub fn list_sum(l: IntList) -> Int64
pub fn from_seq(xs: Seq<Int64>) -> IntList""",
     c_reference="""module main

use std.seq

pub type IntList = enum {
  Nil,
  Cons(IntNode),
}

pub type IntNode = record {
  head: Int64,
  tail: IntList,
}

pub fn list_sum(l: IntList) -> Int64 {
  match l {
    IntList.Nil => 0,
    IntList.Cons(n) => n.head + list_sum(n.tail),
  }
}

pub fn from_seq(xs: Seq<Int64>) -> IntList {
  build(xs, seq.length(xs) - 1, IntList.Nil)
}

fn build(xs: Seq<Int64>, i: Int64, acc: IntList) -> IntList {
  match seq.get(xs, i) {
    None => acc,
    Some(x) => build(xs, i - 1, IntList.Cons(IntNode { head: x, tail: acc })),
  }
}
""", c_probe=c_probe("use main", "@@\nfn check() -> Int64 {\n  main.list_sum(main.from_seq([1, 2, 3]))\n}\n"),
     t_target="main.ts", t_interface="""export type IntList = { readonly kind: "nil" } | { readonly kind: "cons"; readonly head: number; readonly tail: IntList }
export function listSum(l: IntList): number
export function fromArray(xs: readonly number[]): IntList""",
     t_reference="""export type IntList = { readonly kind: "nil" } | { readonly kind: "cons"; readonly head: number; readonly tail: IntList };
export function listSum(l: IntList): number {
  return l.kind === "nil" ? 0 : l.head + listSum(l.tail);
}
export function fromArray(xs: readonly number[]): IntList {
  let acc: IntList = { kind: "nil" };
  for (let i = xs.length - 1; i >= 0; i--) acc = { kind: "cons", head: xs[i]!, tail: acc };
  return acc;
}
""", t_probe='import { listSum, fromArray } from "./main";\nconst n: number = listSum(fromArray([1, 2]));\nvoid n;\n')

task("W10", "write", "Запрос к хранилищу",
     "В модуле `shop.api` напишите точку входа-запрос `price`: цена товара по имени из таблицы `Shop.items` модуля `shop.db`; если товара нет — отсутствие значения.",
     c_target="shop/api.bag", c_interface="module shop.api\npub query price(name: String) -> Option<Int64>",
     c_context={"shop/db.bag": """@@
module shop.db

@@
pub type Item = record {
  @@ price: Int64,
  @@ stock: Int64,
}

@@
pub store Shop {
  @@ table items: Map<String, Item>
}
"""},
     c_reference="""module shop.api

use std.store
use shop.db.{Shop}

pub query price(name: String) -> Option<Int64>
  uses { reads Shop.items }
{
  match store.get(Shop.items, name) {
    Some(it) => Some(it.price),
    None => None,
  }
}
""", c_expect={"decls": {"price": {"kind": "query", "params": ["String"], "ret": "Option<Int64>",
                                   "actual": ["reads shop.db.Shop.items"]}}},
     t_target="shop/api.ts", t_context={"shop/db.ts": """export interface Item { readonly price: number; readonly stock: number }
export interface ShopDb { readonly items: Map<string, Item> }
"""}, t_interface='import { ShopDb } from "./db";\nexport function price(db: ShopDb, name: string): number | undefined',
     t_reference='import { ShopDb } from "./db";\nexport function price(db: ShopDb, name: string): number | undefined {\n'
                 '  return db.items.get(name)?.price;\n}\n',
     t_probe='import { price } from "./api";\nimport { ShopDb } from "./db";\n'
             'declare const db: ShopDb;\nconst p: number | undefined = price(db, "x");\nvoid p;\n')

SHOP_CTX = {"shop/db.bag": """@@
module shop.db

@@
pub type Item = record {
  @@ price: Int64,
  @@ stock: Int64,
}

@@
pub event PriceChanged {
  @@ name: String,
  @@ old: Int64,
  @@ new: Int64,
}

@@
pub store Shop {
  @@ table items: Map<String, Item>
  @@ table history: Map<String, Seq<Int64>>
}
"""}
SHOP_TS = {"shop/db.ts": """export interface Item { readonly price: number; readonly stock: number }
export interface PriceChanged { readonly name: string; readonly old: number; readonly new: number }
export interface ShopDb { readonly items: Map<string, Item>; readonly history: Map<string, readonly number[]> }
export interface Outbox { emit(ev: PriceChanged): void }
""", "result.ts": TS_RESULT}

task("W11", "write", "Команда с проверкой",
     """В модуле `shop.api` напишите команду `set_price(name, value)`: записать новую цену товара в `Shop.items`.
- Ошибки — перечисление `PriceError` в том же модуле: `Negative` (цена меньше нуля) и `UnknownItem` (товара нет).
- Остальные поля товара не меняются.""",
     c_target="shop/api.bag", c_context=SHOP_CTX,
     c_interface="module shop.api\npub type PriceError = enum { Negative, UnknownItem }\n"
                 "pub command set_price(name: String, value: Int64) -> Result<(), PriceError>",
     c_reference="""module shop.api

use std.store
use shop.db.{Shop, Item}

pub type PriceError = enum {
  Negative,
  UnknownItem,
}

pub command set_price(name: String, value: Int64) -> Result<(), PriceError>
  uses { reads Shop.items, writes Shop.items }
{
  if value < 0 {
    return Err(PriceError.Negative)
  }
  match store.get(Shop.items, name) {
    None => Err(PriceError.UnknownItem),
    Some(it) => {
      store.put(Shop.items, name, Item { ..it, price: value });
      Ok(())
    },
  }
}
""", c_expect={"decls": {"set_price": {"kind": "command", "params": ["String", "Int64"],
                                       "ret": "Result<(), shop.api.PriceError>",
                                       "actual": ["reads shop.db.Shop.items", "writes shop.db.Shop.items"]}}},
     t_target="shop/api.ts", t_context=SHOP_TS,
     t_interface='import { ShopDb } from "./db";\nimport { Result } from "../result";\n'
                 'export type PriceError = "negative" | "unknown-item"\n'
                 'export function setPrice(db: ShopDb, name: string, value: number): Result<void, PriceError>',
     t_reference="""import { ShopDb } from "./db";
import { Result, ok, err } from "../result";
export type PriceError = "negative" | "unknown-item";
export function setPrice(db: ShopDb, name: string, value: number): Result<void, PriceError> {
  if (value < 0) return err("negative");
  const it = db.items.get(name);
  if (it === undefined) return err("unknown-item");
  db.items.set(name, { ...it, price: value });
  return ok(undefined);
}
""", t_probe='import { setPrice, PriceError } from "./api";\nimport { ShopDb } from "./db";\nimport { Result } from "../result";\n'
             'declare const db: ShopDb;\nconst r: Result<void, PriceError> = setPrice(db, "x", 1);\nvoid r;\n')

task("W12", "write", "Событие и обработчик", """В модуле `shop.api`:
- команда `reprice(name, value)`: записать новую цену товара и выпустить событие `PriceChanged` (имя, старая и новая цена); если товара нет — ошибка-строка `"нет товара"`;
- обработчик `on_price_changed` события `PriceChanged`: дописать новую цену в конец истории товара в таблице `Shop.history`.""",
     c_target="shop/api.bag", c_context=SHOP_CTX,
     c_interface="module shop.api\npub command reprice(name: String, value: Int64) -> Result<(), String>\n"
                 "handler on_price_changed(ev: PriceChanged)",
     c_reference="""module shop.api

use std.store
use std.seq
use std.option
use shop.db.{Shop, Item, PriceChanged}

pub command reprice(name: String, value: Int64) -> Result<(), String>
  uses { reads Shop.items, writes Shop.items, emits PriceChanged }
{
  match store.get(Shop.items, name) {
    None => Err("нет товара"),
    Some(it) => {
      store.put(Shop.items, name, Item { ..it, price: value });
      emit PriceChanged { name: name, old: it.price, new: value };
      Ok(())
    },
  }
}

handler on_price_changed(ev: PriceChanged)
  uses { reads Shop.history, writes Shop.history }
{
  let prev = option.value_or(store.get(Shop.history, ev.name), []);
  store.put(Shop.history, ev.name, seq.append(prev, ev.new));
}
""", c_expect={"decls": {
         "reprice": {"kind": "command", "params": ["String", "Int64"], "ret": "Result<(), String>",
                     "actual": ["reads shop.db.Shop.items", "writes shop.db.Shop.items", "emits shop.db.PriceChanged"]},
         "on_price_changed": {"kind": "handler", "params": ["shop.db.PriceChanged"], "ret": "()",
                              "actual": ["writes shop.db.Shop.history"]}}},
     t_target="shop/api.ts", t_context=SHOP_TS,
     t_interface='import { ShopDb, Outbox, PriceChanged } from "./db";\nimport { Result } from "../result";\n'
                 'export function reprice(db: ShopDb, out: Outbox, name: string, value: number): Result<void, string>\n'
                 'export function onPriceChanged(db: ShopDb, ev: PriceChanged): void',
     t_reference="""import { ShopDb, Outbox, PriceChanged } from "./db";
import { Result, ok, err } from "../result";
export function reprice(db: ShopDb, out: Outbox, name: string, value: number): Result<void, string> {
  const it = db.items.get(name);
  if (it === undefined) return err("нет товара");
  db.items.set(name, { ...it, price: value });
  out.emit({ name, old: it.price, new: value });
  return ok(undefined);
}
export function onPriceChanged(db: ShopDb, ev: PriceChanged): void {
  db.history.set(ev.name, [...(db.history.get(ev.name) ?? []), ev.new]);
}
""", t_probe='import { reprice, onPriceChanged } from "./api";\nimport { ShopDb, Outbox } from "./db";\n'
             'declare const db: ShopDb;\ndeclare const out: Outbox;\nconst r = reprice(db, out, "x", 1);\n'
             'onPriceChanged(db, { name: "x", old: 1, new: 2 });\nvoid r;\n')

task("W13", "write", "Контракт, реализация и тест", """В модуле `pricing` уже объявлены сущность `Pricing` и контракт `PriceRules` с правилами `non_negative` и `rounding`.
- Напишите `round_price(p)`: отрицательная цена → 0; иначе округление вверх до кратного 10. Объявите, что функция реализует оба правила контракта.
- Напишите тест `round_price_rules`, который проверяет оба правила (не меньше трёх проверок).""",
     c_target="pricing.bag", c_context={},
     c_interface="""module pricing
(сохраните entity Pricing и contract PriceRules как есть)
pub fn round_price(p: Int64) -> Int64   — implements PriceRules.non_negative, PriceRules.rounding
test round_price_rules                  — checks PriceRules.non_negative, PriceRules.rounding""",
     c_reference="""@@
module pricing

use std.test

@@
entity Pricing {
  purpose "Цены товаров: какие значения допустимы и как они округляются."
}

@@
contract PriceRules about Pricing {
  @@ rule non_negative "цена не меньше нуля"
  @@ rule rounding "цена кратна 10 и округляется вверх"
}

pub fn round_price(p: Int64) -> Int64
  implements PriceRules.non_negative, PriceRules.rounding
{
  if p <= 0 {
    0
  } else {
    (p + 9) / 10 * 10
  }
}

test round_price_rules
  checks PriceRules.non_negative, PriceRules.rounding
{
  test.expect_equal("отрицательная", round_price(-5), 0);
  test.expect_equal("кратная", round_price(30), 30);
  test.expect_equal("вверх", round_price(31), 40);
}
""", c_expect={"links": {"round_price": {"implements": ["PriceRules.non_negative", "PriceRules.rounding"]},
                          "round_price_rules": {"checks": ["PriceRules.non_negative", "PriceRules.rounding"]}},
                "keep_ids_from_context": "pricing.bag"},
     t_target="pricing.ts", t_interface="""/** @implements PriceRules.non_negative, PriceRules.rounding */
export function roundPrice(p: number): number
export function testRoundPriceRules(): void  // бросает Error при нарушении""",
     t_reference="""/** @implements PriceRules.non_negative, PriceRules.rounding */
export function roundPrice(p: number): number {
  return p <= 0 ? 0 : Math.ceil(p / 10) * 10;
}
/** @checks PriceRules.non_negative, PriceRules.rounding */
export function testRoundPriceRules(): void {
  const cases: Array<[number, number]> = [[-5, 0], [30, 30], [31, 40]];
  for (const [x, want] of cases) if (roundPrice(x) !== want) throw new Error(`roundPrice(${x})`);
}
""", t_probe='import { roundPrice, testRoundPriceRules } from "./pricing";\nconst n: number = roundPrice(1);\n'
             'testRoundPriceRules();\nvoid n;\n')
# Контекст W13 для bagaev — файл с сущностью и контрактом, который модель дополняет.
TASKS[-1]["c_context"] = {"pricing.bag": """@@
module pricing

@@
entity Pricing {
  purpose "Цены товаров: какие значения допустимы и как они округляются."
}

@@
contract PriceRules about Pricing {
  @@ rule non_negative "цена не меньше нуля"
  @@ rule rounding "цена кратна 10 и округляется вверх"
}
"""}
TASKS[-1]["t_context"] = {"pricing.ts": "// Правила PriceRules: non_negative — цена не меньше нуля; rounding — кратна 10, округление вверх.\n"}

# ---------------------------------------------------------------------------- правки существующего кода
STATUS = """@@
module main

@@
pub type Status = enum {
  @@ Draft,
  @@ Published,
}

@@
pub fn label(s: Status) -> String {
  match s {
    Status.Draft => "черновик",
    Status.Published => "опубликовано",
  }
}

@@
pub fn is_visible(s: Status) -> Bool {
  match s {
    Status.Draft => false,
    Status.Published => true,
  }
}
"""
task("W14", "edit", "Новый вариант перечисления",
     "Добавьте в `Status` вариант `Archived`: подпись `\"архив\"`, не виден. Остальное поведение не меняется.",
     c_target="main.bag", c_context={"main.bag": STATUS}, c_interface="module main\npub type Status = enum { Draft, Published, Archived }",
     c_reference=STATUS.replace("  @@ Published,\n}", "  @@ Published,\n  Archived,\n}")
     .replace('    Status.Published => "опубликовано",\n', '    Status.Published => "опубликовано",\n    Status.Archived => "архив",\n')
     .replace("    Status.Published => true,\n", "    Status.Published => true,\n    Status.Archived => false,\n"),
     c_probe=c_probe("use main", "@@\nfn check() -> String {\n  main.label(main.Status.Archived)\n}\n"),
     c_expect={"keep_ids_from_context": "main.bag"},
     t_target="main.ts", t_context={"main.ts": """export type Status = "draft" | "published";
export function label(s: Status): string {
  switch (s) {
    case "draft": return "черновик";
    case "published": return "опубликовано";
  }
}
export function isVisible(s: Status): boolean {
  switch (s) {
    case "draft": return false;
    case "published": return true;
  }
}
"""}, t_interface='export type Status = "draft" | "published" | "archived"',
     t_reference="""export type Status = "draft" | "published" | "archived";
export function label(s: Status): string {
  switch (s) {
    case "draft": return "черновик";
    case "published": return "опубликовано";
    case "archived": return "архив";
  }
}
export function isVisible(s: Status): boolean {
  switch (s) {
    case "draft": return false;
    case "published": return true;
    case "archived": return false;
  }
}
""", t_probe='import { label } from "./main";\nconst s: string = label("archived");\nvoid s;\n')

ARTICLE = """@@
module main

@@
pub type Article = record {
  @@ title: String,
  @@ words: Int64,
}

@@
pub fn headline(a: Article) -> String {
  a.title ++ " (" ++ i64.format_decimal(a.words) ++ ")"
}

@@
pub fn retitle(a: Article, t: String) -> Article {
  Article { ..a, title: t }
}
"""
task("W15", "edit", "Переименование поля",
     "Переименуйте поле `title` записи `Article` в `name` во всём модуле. Поведение не меняется.",
     c_target="main.bag", c_context={"main.bag": ARTICLE.replace("@@\nmodule main\n", "@@\nmodule main\n\nuse std.i64\n")},
     c_interface="module main\npub type Article = record { name: String, words: Int64 }",
     c_reference=ARTICLE.replace("@@\nmodule main\n", "@@\nmodule main\n\nuse std.i64\n")
     .replace("@@ title: String", "@@ name: String").replace("a.title", "a.name").replace("title: t", "name: t"),
     c_probe=c_probe("use main", "@@\nfn check(a: main.Article) -> String {\n  a.name\n}\n"),
     c_expect={"keep_ids_from_context": "main.bag", "renamed": {"title": "name"}},
     t_target="main.ts", t_context={"main.ts": """export interface Article { readonly title: string; readonly words: number }
export function headline(a: Article): string {
  return `${a.title} (${a.words})`;
}
export function retitle(a: Article, t: string): Article {
  return { ...a, title: t };
}
"""}, t_interface="export interface Article { readonly name: string; readonly words: number }",
     t_reference="""export interface Article { readonly name: string; readonly words: number }
export function headline(a: Article): string {
  return `${a.name} (${a.words})`;
}
export function retitle(a: Article, t: string): Article {
  return { ...a, name: t };
}
""", t_probe='import { Article } from "./main";\ndeclare const a: Article;\nconst s: string = a.name;\nvoid s;\n')

CATALOG = """@@
module main

@@
pub store Catalog {
  @@ table discounts: Map<String, Int64>
}

@@
pub fn final_price(name: String, base: Int64) -> Int64 {
  base
}

@@
pub query quote(name: String, base: Int64) -> Int64 {
  final_price(name, base)
}
"""
task("W16", "edit", "Новый эффект",
     "Пусть `final_price` вычитает из базовой цены скидку товара из таблицы `Catalog.discounts` (нет записи — скидка 0). Запрос `quote` должен продолжать работать.",
     c_target="main.bag", c_context={"main.bag": CATALOG},
     c_interface="module main\npub fn final_price(name: String, base: Int64) -> Int64 (с нужным рядом uses)\n"
                 "pub query quote(name: String, base: Int64) -> Int64",
     c_reference=CATALOG.replace("@@\nmodule main\n", "@@\nmodule main\n\nuse std.store\nuse std.option\n")
     .replace("pub fn final_price(name: String, base: Int64) -> Int64 {\n  base\n}",
              "pub fn final_price(name: String, base: Int64) -> Int64\n  uses { reads Catalog.discounts }\n{\n"
              "  base - option.value_or(store.get(Catalog.discounts, name), 0)\n}")
     .replace("pub query quote(name: String, base: Int64) -> Int64 {",
              "pub query quote(name: String, base: Int64) -> Int64\n  uses { reads Catalog.discounts }\n{"),
     c_expect={"keep_ids_from_context": "main.bag",
               "decls": {"final_price": {"kind": "fn", "params": ["String", "Int64"], "ret": "Int64",
                                         "actual": ["reads main.Catalog.discounts"]},
                         "quote": {"kind": "query", "params": ["String", "Int64"], "ret": "Int64",
                                   "actual": ["reads main.Catalog.discounts"]}}},
     t_target="main.ts", t_context={"main.ts": """export interface CatalogDb { readonly discounts: Map<string, number> }
export function finalPrice(name: string, base: number): number {
  return base;
}
export function quote(name: string, base: number): number {
  return finalPrice(name, base);
}
"""}, t_interface="export function finalPrice(db: CatalogDb, name: string, base: number): number\n"
                  "export function quote(db: CatalogDb, name: string, base: number): number",
     t_reference="""export interface CatalogDb { readonly discounts: Map<string, number> }
export function finalPrice(db: CatalogDb, name: string, base: number): number {
  return base - (db.discounts.get(name) ?? 0);
}
export function quote(db: CatalogDb, name: string, base: number): number {
  return finalPrice(db, name, base);
}
""", t_probe='import { quote, CatalogDb } from "./main";\ndeclare const db: CatalogDb;\nconst n: number = quote(db, "x", 1);\nvoid n;\n')

# ---------------------------------------------------------------------------- снова чистые функции
task("W17", "write", "Нарастающие суммы", "Напишите `running_totals`: i-й элемент результата — сумма первых i+1 элементов входа.",
     c_target="main.bag", c_interface="module main\npub fn running_totals(xs: Seq<Int64>) -> Seq<Int64>",
     c_reference="""module main

use std.seq
use std.option

pub fn running_totals(xs: Seq<Int64>) -> Seq<Int64> {
  seq.fold(xs, [], fn(acc, x) => seq.append(acc, x + last(acc)))
}

fn last(xs: Seq<Int64>) -> Int64 {
  option.value_or(seq.get(xs, seq.length(xs) - 1), 0)
}
""", c_probe=c_probe("use main", "@@\nfn check(xs: Seq<Int64>) -> Seq<Int64> {\n  main.running_totals(xs)\n}\n"),
     t_target="main.ts", t_interface="export function runningTotals(xs: readonly number[]): number[]",
     t_reference="export function runningTotals(xs: readonly number[]): number[] {\n  let s = 0;\n"
                 "  return xs.map((x) => (s += x));\n}\n",
     t_probe='import { runningTotals } from "./main";\nconst r: number[] = runningTotals([1]);\nvoid r;\n')

task("W18", "write", "Описание вложенного результата",
     """Напишите `describe`: нет значения → `"нет"`; успех → число десятичной записью; ошибка e → `"ошибка: "` и текст e.""",
     c_target="main.bag", c_interface="module main\npub fn describe(r: Option<Result<Int64, String>>) -> String",
     c_reference="""module main

use std.i64

pub fn describe(r: Option<Result<Int64, String>>) -> String {
  match r {
    None => "нет",
    Some(x) => match x {
      Ok(v) => i64.format_decimal(v),
      Err(e) => "ошибка: " ++ e,
    },
  }
}
""", c_probe=c_probe("use main", "@@\nfn check() -> String {\n  main.describe(Some(Err(\"x\")))\n}\n"),
     t_target="main.ts", t_context={"result.ts": TS_RESULT},
     t_interface='import { Result } from "./result";\nexport function describe(r: Result<number, string> | undefined): string',
     t_reference='import { Result } from "./result";\nexport function describe(r: Result<number, string> | undefined): string {\n'
                 '  if (r === undefined) return "нет";\n  return r.ok ? String(r.value) : `ошибка: ${r.error}`;\n}\n',
     t_probe='import { describe } from "./main";\nconst s: string = describe(undefined);\nvoid s;\n')

task("W19", "write", "Проверка возраста", """Напишите `validate_age`:
- отрицательный → ошибка `Negative`;
- больше 150 → ошибка `TooLarge` с этим значением;
- иначе — само значение.
Ошибки — перечисление `AgeError`.""",
     c_target="main.bag", c_interface="module main\npub type AgeError = enum { Negative, TooLarge(Int64) }\n"
                                      "pub fn validate_age(a: Int64) -> Result<Int64, AgeError>",
     c_reference="""module main

pub type AgeError = enum {
  Negative,
  TooLarge(Int64),
}

pub fn validate_age(a: Int64) -> Result<Int64, AgeError> {
  if a < 0 {
    return Err(AgeError.Negative)
  }
  if a > 150 {
    return Err(AgeError.TooLarge(a))
  }
  Ok(a)
}
""", c_probe=c_probe("use main", "@@\nfn check(a: Int64) -> Bool {\n  match main.validate_age(a) {\n    Ok(_) => true,\n"
                                "    Err(e) => match e {\n      main.AgeError.Negative => false,\n"
                                "      main.AgeError.TooLarge(_) => false,\n    },\n  }\n}\n"),
     t_target="main.ts", t_context={"result.ts": TS_RESULT},
     t_interface='import { Result } from "./result";\n'
                 'export type AgeError = { readonly kind: "negative" } | { readonly kind: "too-large"; readonly value: number }\n'
                 'export function validateAge(a: number): Result<number, AgeError>',
     t_reference="""import { Result, ok, err } from "./result";
export type AgeError = { readonly kind: "negative" } | { readonly kind: "too-large"; readonly value: number };
export function validateAge(a: number): Result<number, AgeError> {
  if (a < 0) return err({ kind: "negative" });
  if (a > 150) return err({ kind: "too-large", value: a });
  return ok(a);
}
""", t_probe='import { validateAge, AgeError } from "./main";\nimport { Result } from "./result";\n'
             'const r: Result<number, AgeError> = validateAge(3);\nvoid r;\n')

task("W20", "write", "Удаление повторов", "Напишите обобщённую `dedupe`: оставить первое вхождение каждого значения, сохранив порядок.",
     c_target="main.bag", c_interface="module main\npub fn dedupe<T: Key>(xs: Seq<T>) -> Seq<T>",
     c_reference="""module main

use std.seq
use std.map
use std.option

pub fn dedupe<T: Key>(xs: Seq<T>) -> Seq<T> {
  go(xs, 0, Map {}, [])
}

fn go<T: Key>(xs: Seq<T>, i: Int64, seen: Map<T, Bool>, out: Seq<T>) -> Seq<T> {
  match seq.get(xs, i) {
    None => out,
    Some(x) => if option.is_some(map.get(seen, x)) {
      go(xs, i + 1, seen, out)
    } else {
      go(xs, i + 1, map.put(seen, x, true), seq.append(out, x))
    },
  }
}
""", c_probe=c_probe("use main", "@@\nfn check(xs: Seq<String>) -> Seq<String> {\n  main.dedupe(xs)\n}\n"),
     t_target="main.ts", t_interface="export function dedupe<T>(xs: readonly T[]): T[]",
     t_reference="export function dedupe<T>(xs: readonly T[]): T[] {\n  return [...new Set(xs)];\n}\n",
     t_probe='import { dedupe } from "./main";\nconst r: string[] = dedupe(["a"]);\nvoid r;\n')


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    index = []
    for t in TASKS:
        d = OUT / t["id"]
        tag = t["id"]
        for arm, ext in (("c", "bag"), ("t", "ts")):
            ctx = {f: (with_ids(f"{tag}/ctx/{f}", s) if arm == "c" else s) for f, s in t[f"{arm}_context"].items()}
            for f, s in ctx.items():
                p = d / arm / "context" / f
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(s, encoding="utf-8")
            ref = t[f"{arm}_reference"]
            if arm == "c":
                ref = with_ids(f"{tag}/ctx/{t['c_target']}", ref) if t["c_target"] in t["c_context"] else ref
            p = d / arm / "reference" / t[f"{arm}_target"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(ref, encoding="utf-8")
            probe = t[f"{arm}_probe"]
            if probe:
                name = "probe.bag" if arm == "c" else "probe.ts"
                if arm == "t" and "/" in t["t_target"]:
                    name = t["t_target"].rsplit("/", 1)[0] + "/probe.ts"
                p = d / arm / "probe" / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(with_ids(f"{tag}/probe", probe) if arm == "c" else probe, encoding="utf-8")
        md = [f"# {t['id']}. {t['title']}", "", t["statement"], ""]
        md += ["## bagaev", "", f"Файл: `{t['c_target']}`.", "", "```bagaev", t["c_interface"], "```", ""]
        md += ["## TypeScript", "", f"Файл: `{t['t_target']}`.", "", "```ts", t["t_interface"], "```", ""]
        (d / "task.md").write_text("\n".join(md), encoding="utf-8")
        meta = {k: t[k] for k in ("id", "kind", "title", "c_target", "t_target", "c_expect")}
        (d / "task.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index.append(meta)
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"задач: {len(TASKS)} ({sum(t['kind'] == 'edit' for t in TASKS)} правок)")


if __name__ == "__main__":
    main()
