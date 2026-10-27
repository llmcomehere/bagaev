# bagaev за 5 минут — шпаргалка

Ненормативная выжимка: при расхождении действуют [surface.md](surface.md), [effects.md](effects.md), [lexical.md](lexical.md), [grammar.ebnf](grammar.ebnf). По этой шпаргалке LLM пишет код в пробнике пишемости (план, Ф2).

## Файл

```bagaev
/// Документирующий комментарий относится к следующей декларации.
@id("k3m9qa")                    // устойчивый ID; новый ставит `bag fmt --assign-ids`, не придумывайте
module shop.cart                 // файл shop/cart.bag

use std.seq                      // модуль: вызовы seq.map(…)
use shop.items.{Item, ItemId}    // отдельные pub-объявления

@id("p7x2vd")
pub fn total(items: Seq<Item>) -> Int64 {     // сигнатуры верхнего уровня — полные
  seq.fold(items, 0, fn(acc, it) => acc + it.price)
}
```

- Отступы незначимы, блоки в `{}`, операторы через `;`.
- Последнее выражение блока — его значение.
- `if`, `match` и `{…}` в позиции оператора `;` не требуют.
- Комментарии `//` и `///`; блочных нет.

## Типы

```bagaev
@id("…") pub type ItemId = opaque String         // новый тип; конструктор ItemId(s) и разбор match id { ItemId(s) => s } — только в этом модуле
@id("…") pub type Item = record { @id("…") id: ItemId, @id("…") price: Int64 }    // @id у каждого поля и варианта
@id("…") pub type Size = enum { @id("…") Small, @id("…") Large, @id("…") Custom(Int64) }   // у варианта 0 или 1 значение
@id("…") pub type List<T> = enum { @id("…") Nil, @id("…") Cons(Node<T>) }   // рекурсия разрешена
@id("…") pub type Node<T> = record { @id("…") head: T, @id("…") tail: List<T> }
```

| Что есть | Чего нет |
| --- | --- |
| `Bool Int64 String Bytes () Option<T> Result<T,E> Seq<T> Map<K,V> fn(A) -> B` | Float, BigInt, кортежи, null, синонимы типов |

## Выражения

```bagaev
let x: Int64 = 1 + 2 * 3;           // let неизменяем; аннотация необязательна
let p = Item { id: id, price: 10 }; // все поля, в любом порядке
let q = Item { ..p, price: 12 };    // копия с изменением
let s = Size.Custom(5);             // вариант — через тип
let xs = [1, 2, 3];                 // Seq
let m = Map { "a" => 1, "b" => 2 }; // Map; повтор ключа-константы — ошибка проверки, вычисленного — FAULT
let ok = a == b and not (c < d);    // and/or не смешивать без скобок
let t = "Привет, " ++ name;         // ++ для String, Bytes, Seq
let f = fn(v: Int64) => v * 2;      // лямбда; тип параметра можно не писать, если он ожидаем
if n > 0 { "+" } else if n < 0 { "-" } else { "0" }
match s {                           // все варианты, без «_ =>»; шаблон плоский
  Size.Small => 1,
  Size.Large => 2,
  Size.Custom(v) => v,
}
```

| Тема | Правило |
| --- | --- |
| Арифметика | `+ - * / %` над Int64: переполнение и деление на ноль — FAULT (остановка). Нужен Result — `std.i64.add(a, b)` |
| Сравнение | `==` нужен Eq, `<` нужен Key. Функции не сравниваются. Разные номинальные типы не сравниваются |
| Пути | `модуль.функция`, `Тип.Вариант`, `запись.поле`, `Хранилище.таблица` |
| Методов нет | пишите `seq.length(xs)`, а не `xs.length()` |
| Циклов нет | повторение — рекурсия (`fn go(xs, i, acc)` с `seq.get(xs, i)`) или `seq.fold` / `seq.map` |
| `pub` | нужен для использования из другого модуля, включая entity и contract; у `handler`, `migration`, `test` не пишется |
| `@id` | у модуля, каждой декларации, поля, варианта, таблицы, правила. Новый код можно писать без них: `bag fmt --assign-ids` вставит |

## Ошибки: Result и `?`

```bagaev
@id("…") pub type ParseError = enum { @id("…") Empty, @id("…") Bad(String) }

@id("…")
pub fn parse_two(a: String, b: String) -> Result<Int64, ParseError> {
  if a == "" { return Err(ParseError.Empty) }
  let x = parse(a)?;              // при Err — немедленный return Err того же типа E
  let y = parse(b)?;
  Ok(x + y)
}
```

- Преобразования ошибок нет: другой тип ошибки переводите явно через `result.map_error(r, fn(e) => …)?`.
- `e;` с Result — ошибка `RESULT_DISCARDED`. Чтобы намеренно отбросить значение, пишите `let _ = e;`.

## Эффекты и данные

```bagaev
use std.store                      // store.get / put / all / replace_all

@id("…")
pub store Shop {
  @id("…") table carts: Map<CartId, Cart>
  @id("…") table stats: Map<CartId, Int64>
}

@id("…")
pub event CartChanged { @id("…") cart: CartId, @id("…") total: Int64 }

@id("…")
pub command add_item(cart: CartId, item: Item) -> Result<(), CartError>   // транзакция: Ok — фиксация, иначе ничего
  uses { reads Shop.carts, writes Shop.carts, emits CartChanged }
{
  let c = match store.get(Shop.carts, cart) { Some(c) => c, None => return Err(CartError.NoCart) };
  let next = Cart { ..c, items: seq.append(c.items, item) };
  store.put(Shop.carts, cart, next);
  emit CartChanged { cart: cart, total: total(next.items) };
  Ok(())
}

@id("…") pub query cart_size(cart: CartId) -> Int64 uses { reads Shop.carts } { … }   // только чтение
@id("…") handler on_change(ev: CartChanged) uses { writes Shop.stats } { … }   // одна транзакция на событие; без pub
```

| Правило | Пояснение |
| --- | --- |
| Атомы `uses` | `reads S.t`, `writes S.t`, `emits E`. Функция без `uses` чистая. `writes` не включает `reads`: прочитать и записать — оба атома. Ряд пишет и функция, и вызывающая её точка входа |
| Таблица | указывается путём `Shop.carts`, не переменной |
| Обобщённые функции | `fn map<T, U, !e>(xs: Seq<T>, f: fn(T) -> U uses e) -> Seq<U> uses e` |
| Чего нет | часов, случайности, сети, файлов, FFI |

## Стандартная библиотека

Подключается `use std.<модуль>`, вызывается `модуль.функция(…)`. Неявного prelude функций нет.

```text
std.seq     length(xs) -> Int64 · get(xs, i) -> Option<T> · append(xs, x) · concat(a, b) · slice(xs, from, to) -> Result
            map(xs, f) · fold(xs, init, fn(acc, x) => …)          // f с эффектами допустима: ряд переходит к вызову
std.map     get(m, k) -> Option<V> · put(m, k, v) -> Map · remove(m, k) · length(m) · entries(m) -> Seq<map.Entry<K, V>> (поля key, value)
std.option  is_some(o) -> Bool · value_or(o, d) -> T · map(o, f)
std.result  is_ok(r) -> Bool · map(r, f) · map_error(r, f)
std.i64     add sub mul div rem (a, b) -> Result<Int64, i64.ArithmeticError> · neg(a) · parse_decimal(s) -> Result<Int64, i64.ParseIntError> · format_decimal(n) -> String
std.string  scalar_length(s) · scalar_get(s, i) -> Option<Int64> (код символа) · slice · concat · from_scalars · to_scalars
std.bytes   length · get · slice · concat · from_octets · to_octets
std.value   equal(a, b) · compare(a, b) -> Int64
std.json    quote(s) -> String
std.store   get(T, k) -> Option<V> · contains(T, k) · all(T) -> Map · put(T, k, v) · remove(T, k) · replace_all(T, m)   // T — путь таблицы
std.test    expect(label, cond) · expect_equal(label, actual, expected)
```

Варианты своих перечислений в шаблонах пишутся через тип (`Size.Small`), предопределённые — без него (`Some(x)`, `None`, `Ok(v)`, `Err(e)`).

## Смысловые связи

```bagaev
@id("…") pub entity Authorship { purpose "Авторская атрибуция статьи" not_about ["права редактора"] }
@id("…") pub contract AuthorsShape about Authorship { @id("…") rule nonempty "хотя бы один автор" }

@id("…") pub fn make(…) -> Result<Authors, AuthorsError> implements AuthorsShape.nonempty { … }
@id("…") test keeps_order checks AuthorsShape.nonempty { test.expect_equal("порядок", got, want) }
```

Вызовы, чтения и записи связи компилятор извлекает сам. Вручную пишутся только `implements` (отвечает за правило), `requires` (полагается на него), `checks` (тест проверяет), `supersedes "<id>"` (заменяет удалённую декларацию), `derived_from`.

## Частые ошибки

| Код | Причина |
| --- | --- |
| `NON_EXHAUSTIVE_MATCH` | не перечислены все варианты |
| `UNDECLARED_EFFECT` | тело читает или пишет то, чего нет в `uses` |
| `QUESTION_MARK_CONTEXT` | `?` в функции с другим типом ошибки |
| `AMBIGUOUS_TYPE_ARGUMENT` | `[]`, `None` или `Map {}` без ожидаемого типа: добавьте `let x: T = …` |
| `MISSING_ENTITY_ID` | у декларации нет `@id`: запустите `bag fmt --assign-ids` |
| `MIXED_AND_OR`, `NONASSOC_COMPARISON` | нужны скобки; `a < b < c` недопустимо |
| `RECORD_LITERAL_IN_CONDITION` | `if (p == Point { x: 0, y: 0 }) { … }` — литерал записи в условии в скобках |
