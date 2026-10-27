# MACHINE-1 — машина исполнения BIR-1

**r30 · WORKING_DESIGN (D76, D77).** Единая CEK-машина исполняет [BIR-1](../ir/bir.md). На подмножестве CORE-0.1 (константы Bool/Int64/Unit, `let`, `if`, `lambda`, вызов, примитивы `i64.*`, `Result` и `match` по нему) правила и стоимости совпадают с [MACHINE-CORE-0.1](core-machine.md) с точностью до переименования (§7). Поэтому замороженный исполнитель модели R07 остаётся независимым оракулом L1. Правила имеют идентификаторы `MCH-nn`.

## 1. Уровни соответствия (D76)

**MCH-01.**
- **L2** — то, что сравнивается для любой реализации: исход (OUT-01), значение (CANON-11), код и место FAULT, эффекты.
- **L1** — дополнительно число шагов и трасса правил. Требуется только от эталона. Реализация-компилятор исчерпание топлива сообщает защитным `IMPLEMENTATION_STOP RESOURCE_LIMIT` (OUT-01).

## 2. Состояние и значения

**MCH-02. Состояние** — `(режим, окружение, K, rk, шаги)`:
- режим: Eval(узел) или Value(значение);
- окружение — неизменяемый связный список значений (BIR-04);
- K — неизменяемый стек кадров продолжения;
- rk — регистр возврата: продолжение, в которое `Return` доставляет значение.

Каждый кадр хранит окружение и rk, которые восстанавливаются, когда он принимает значение. Для управления рекурсия хоста не используется: пользовательская рекурсия ограничена только бюджетом. Операции над значениями (равенство, порядок, наблюдение) у эталона рекурсивны: значение глубже защитного предела даёт `IMPLEMENTATION_STOP RESOURCE_LIMIT`, а не исход программы.

**MCH-03. Значения:** Bool, Int64, String (Unicode scalar values), Bytes, Unit, запись (поля в порядке объявления), вариант (ordinal, тег, нагрузка), Seq, Map (порядок записей — Key), замыкание `(тело, арность, окружение)`. Opaque представлен своим значением. Значение типа не хранит (D75).

## 3. Шаг

**MCH-04.** Перед каждым переходом, без списания шага и без записи в трассу, проверяется по порядку:
1. Value при пустом K — исход `RETURNED`;
2. видимая отмена (`cancel_at` = число выполненных переходов) — `SEMANTIC_STOP CANCELLED`;
3. исчерпан бюджет — `SEMANTIC_STOP BUDGET_EXCEEDED`.

Иначе выполняется ровно одно правило §4: шаг +1 и одна запись трассы `(правило, nid)`. Связывание группы функций модуля (BIR-01) и вход в точку входа шагов не тратят: исполнение начинается с Eval тела точки входа при пустом K.

## 4. Закрытый каталог правил

**MCH-05.** Каждое правило стоит 1. Других переходов нет.

| Правило | Переход |
| --- | --- |
| `CONST` | Eval Const → Value |
| `VAR` | Eval Local/Global → Value (поиск в окружении; функция группы — замыкание без окружения) |
| `LAMBDA` | Eval Lambda → замыкание с текущим окружением |
| `LET_ENTER` / `LET_BIND` | Eval Let → Eval значения, кадр Let / значение + кадр → Eval тела со связыванием |
| `IF_ENTER` / `IF_THEN` / `IF_ELSE` | Eval If → Eval условия / выбор ветви по Bool |
| `CALL_ENTER` | Eval Call → Eval функции, кадр CallFn |
| `CALL_ARGS` / `CALL_NEXT` | замыкание (есть аргументы) → Eval первого аргумента / готовый не последний аргумент → Eval следующего |
| `CALL_BODY` | последний аргумент (или замыкание без аргументов) → Eval тела в окружении замыкания + аргументы; rk := продолжение вызова |
| `PRIM_ENTER` / `PRIM_NEXT` / `PRIM_APPLY` | как CALL для аргументов; последний аргумент → значение примитива или FAULT |
| `VARIANT_ENTER` / `VARIANT_WRAP` | Eval Variant → Eval нагрузки / нагрузка → вариант (opaque — то же значение) |
| `MATCH_ENTER` / `MATCH_ARM` | Eval Match → Eval значения / выбор ветви по тегу, связывание нагрузки |
| `RECORD_ENTER` / `RECORD_NEXT` / `RECORD_BUILD` | поля в исходном порядке; без полей ENTER сразу даёт запись |
| `FIELD_ENTER` / `FIELD_GET` | Eval Field → Eval записи / запись → поле |
| `SEQ_ENTER` / `SEQ_NEXT` / `SEQ_BUILD` | элементы слева направо; пустой — сразу значение |
| `MAP_ENTER` / `MAP_NEXT` / `MAP_BUILD` | ключ, затем значение каждой пары слева направо; BUILD — карта или FAULT `DUPLICATE_KEY` |
| `RETURN_ENTER` / `RETURN_EXIT` | Eval Return → Eval значения / значение → доставка в rk кадра Return |

**MCH-06. Perform** (r31) исполняет хост в транзакции точки входа ([HOST-1](host.md) HST-08, EFF-08):

| Правило | Переход |
| --- | --- |
| `PERFORM_ENTER` | Eval Perform с аргументами → Eval первого аргумента, кадр Perform |
| `PERFORM_NEXT` | готовый не последний аргумент → Eval следующего |
| `PERFORM_APPLY` | последний аргумент (или Perform без аргументов) → ответ хоста как значение |

- Аргументы вычисляются слева направо; ресурс (таблица или событие) — часть узла, а не аргумент.
- Отказ хоста (`ACCESS_DENIED`, `REPLAY_DIVERGENCE`) даёт `IMPLEMENTATION_STOP` с кодом хоста. Переход `PERFORM_APPLY` при этом не публикуется и шага не списывает.
- Без хоста (`bag run` чистой функции, мост CORE-0.1) Perform даёт `IMPLEMENTATION_STOP NOT_IMPLEMENTED`; до запуска это исключено проверкой `HOST_EFFECT_OUTSIDE_TRANSACTION` (MCH-09).

## 5. Примитивы и FAULT

**MCH-07.** Применение примитива — одно правило `PRIM_APPLY`, независимо от размера данных. Поштучная цена сравнения и сборки (DATA-0.1, [data-work.md](data-work.md)) в MACHINE-1 не входит: это исследовательский профиль. Каталог примитивов — `std.*` с телом `{}` ([CHECK-1 §2](../language/checking.md)) и операторы BIR-08. Семантика — [stdlib/api.md](../stdlib/api.md) и приёмочные примеры [stdlib/acceptance.md](../stdlib/acceptance.md) (SA-001…SA-046) с уточнениями:
- `parse_decimal` — по [stdlib/types.md §4](../stdlib/types.md). Сначала синтаксис всей строки, затем диапазон; index — позиция scalar value:
  - пустая строка — `Empty` с индексом 0;
  - единственный минус — `SignOnly` с индексом 1;
  - начальный плюс или не-ASCII-цифра — `InvalidDigit` на её позиции;
  - после первого нуля любой следующий символ — `LeadingZero` на его позиции;
  - после ненулевой первой цифры первая не-цифра — `InvalidDigit`;
- `slice` всех коллекций: `Ok`, если `0 ≤ start ≤ end ≤ length`, иначе `Err(BoundsError{length, start, end})` без подрезки;
- `utf8.decode`: первая ошибка по смещению, `DataError{code, first, second = −1}`. `first` указывает на ошибочный октет (Continuation, Overlong, Surrogate, Range — следующий за ведущим), а для Leading и Truncated — на начало последовательности (DATA-0.1, векторы `data-core.json`);
- `std.codec.*` — `IMPLEMENTATION_STOP NOT_IMPLEMENTED`, пока не закрыт VALUE-CODEC-V1 (BD07).

**MCH-08. FAULT** — терминальный исход с кодом, местом (`site`: файл и диапазон узла) и `data`. Правило, на котором он возник, публикуется и списывает шаг.

| Код | Где | `data` |
| --- | --- | --- |
| `ARITHMETIC_OVERFLOW` | `op.add/sub/mul/div/neg`: результат вне Int64, `MIN / −1` | — |
| `DIVISION_BY_ZERO` | `op.div`, `op.rem`: делитель 0 | — |
| `DUPLICATE_KEY` | `MAP_BUILD`: повтор ключа | `first`, `second` — индексы пар по data-values §4 |
| `TEST_ASSERTION` | `test.expect`, `test.expect_equal` | `label` |

`op.rem`: `MIN % −1 = 0`, знак результата — у делимого (SURF-35).

## 6. Запуск

**MCH-09. `bag run <корень> <модуль>.<функция>`** — проверка (CHECK-1), понижение, исполнение тела.
- Точка входа — `pub fn` без параметров, без обобщений и с пустым рядом:
  - иначе `UNKNOWN_ENTRYPOINT`, `ENTRYPOINT_SIGNATURE` (параметры или обобщения: тип результата должен быть известен до запуска) или `HOST_EFFECT_OUTSIDE_TRANSACTION`;
  - эти коды выдаются исходом `PRELAUNCH`; у существующей функции диапазон — её имя, у неизвестной места нет (`file` пуст).
- Наблюдение: `outcome`, `value` (CANON-11, по объявленному типу результата) или `code`; у FAULT — `site` и `data`; `effects: []`.
- С `--trace` (L1) добавляются `steps` и `trace_l1` — последовательность правил. Бюджет по умолчанию — 10 000 000 шагов; отрицательный бюджет — ошибка вызова.
- Вывод — обычный JSON (как наблюдения conformance); значение имеет форму CANON-11. Байтовая форма BAG-CJSON-1 обязательна там, где значение хешируется или хранится (HOST-1: строки таблиц, квитанции, журнал).

**MCH-10. `bag test <корень>`** исполняет каждое объявление `test` отдельно:
- `RETURNED` — PASS;
- `FAULT` — FAIL с кодом, местом и `data`, если она есть;
- `SEMANTIC_STOP` и `IMPLEMENTATION_STOP` — ERROR с кодом: тест не дал ответа;
- тест с эффектами хранилища исполняется на отдельном пустом хранилище в памяти (HST-18, r31).

## 7. Соответствие CORE-0.1

**MCH-11.** На подмножестве CORE-0.1:
- переименование правил: `VARIANT_ENTER` ↔ `RESULT_ENTER`, `VARIANT_WRAP` ↔ `RESULT_WRAP`, `MATCH_ARM` ↔ `MATCH_OK` / `MATCH_ERR` по тегу; остальные совпадают;
- `LETREC` CORE соответствует бесплатному связыванию группы модуля (MCH-04): программа модуля в CORE-0.1 — `letrec` всех функций вокруг тела точки входа, и единственный её `LETREC` из трассы CORE удаляется;
- примитивы `std.i64.{eq,lt,add,sub,div,rem}` ↔ `i64.*` CORE.

Мост [conformance/bridges/core01.py](../../conformance/bridges/core01.py) переводит понижённую программу из этого подмножества в CORE-0.1 JSON. Затем он исполняет её **замороженным** `models/r07-core/experiments/core-machine/engine.py` и сравнивает значение, исход и трассу с точностью до этого переименования. Завершимость и длину решает оракул; программа вне подмножества — SKIP.

Границы моста:
- он проверяет машину, а не понижение: перевод идёт из уже понижённого BIR-1, по тем же индексам `Local` и nid. Ошибки понижения (связывания, порядок вычисления, развёртки BIR-05…07) ловит корпус `conformance/cases`;
- в CORE нет `return`, записей, вариантов кроме Result, последовательностей и карт: эти правила проверяют корпус и мутационная проверка `conformance/bridges/mutants.py`.

## Приложение A. Функции std на bagaev

**MCH-12.** Тела функций высшего порядка std нормативны: они определяют значения и трассу L1 программ, которые их вызывают (BIR-09). Здесь `get` и `append` — примитивы `std.seq.get@1`, `std.seq.append@1`. Совпадение с эталоном проверяет `ref/tests/test_machine.py`.

```bagaev
// std.seq
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

// std.option
pub fn map<A, B, !e>(o: Option<A>, f: fn(A) -> B uses e) -> Option<B> uses e {
  match o {
    None => None,
    Some(x) => Some(f(x)),
  }
}

// std.result
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
```
