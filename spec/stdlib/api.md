# STDLIB-API-0.1 — закрытый каталог библиотеки

**R24 · WORKING_DESIGN · полный предлагаемый перечень функций минимальной библиотеки; реализация V1 NOT_RUN.** Исходный предмет — T13-C05, обязательство V1-F060. Здесь сохраняются арифметика, коллекции, текст/байты, Option/Result, кодирование, транзакции, события и проверки. Полный source/IR/runtime/storage contract остаётся самостоятельной зависимостью: его отсутствие останавливает запуск как INPUT_NOT_READY, не превращает required-функцию в исключённую.

Это версия проекта для реализации в эталоне и последующей приёмки, а не односторонний релиз языка.

**r26: каталог пересматривается при встраивании (Ф3–Ф4).** До этого в нём действуют известные расхождения с решениями r25. Исполнять их по букве каталога нельзя:
- `map_pure`/`fold_pure`/`map_error_pure` заменяются обобщёнными функциями с эффект-переменной (D70, EFF-06);
- `ReadCap`/`WriteCap`/`EventReadCap`/`ConsumerCap` и STD-052…057 заменяются эффектами по таблицам, `std.store.get/put/all/replace_all`, формой `emit` и объявлением `handler` (D81, EFF-07, EFF-11);
- строки `std.float`, `std.bigint`, `std.recursive_data` ниже заменены решениями D69/D71;
- коды областей выражаются кодами [DIAG-1](../diagnostics/registry.json) (псевдонимы).

Модули типов: `Entry` — `std.map`; `ArithmeticError` и `ParseIntError` — `std.i64`; `BoundsError`, `ScalarError`, `OctetError`, `DataError`, `DataErrorCode` — общий модуль `std.data`. Перечень функций, которых не хватает примерам, — [examples/README.md](../../examples/README.md). Никакая обязательная категория V1 не удалена. Конструкторы records/sums/Option/Result/Seq и Match — формы языка из DATA-IR, не скрытые функции std. Нижеследующий реестр содержит все callable std exports; типов касается [types.md](types.md), выполнения — [work.md](work.md), сервисов — [services.md](services.md), разрешения имён — [resolution.md](resolution.md). Канонический перечень — [stdlib-catalog.json](../../registry/data/stdlib/catalog.json).

Сигнатуры здесь — метанотация: `<T:Eq>` задаёт rank-1 generic и whole-type bound; Fn явно имеет закрытый effect set. Это не обещание окончательного source spelling. Все аргументы вычисляются слева направо до входа функции. `map_pure` и `fold_pure` принимают только Fn с эффектами `{}`; полиморфизм строк эффектов не добавляется. Ошибки Result являются значениями, а budget/cancel/internal stops сохраняют категории ERR-0.1.

Включение имени в каталог не является current capability и не означает готовой машинной реализации. Критерий про перечисление API не подменяется результатами проверок runtime. Неизвестный std symbol отвергается на resolve даже в невзятых ветвях и неиспользуемых декларациях; нет dynamic fallback, скрытых импортов и автоматически подключаемых функций prelude.

## Состояние в эталоне (r30)

Действующий состав std задаёт [CHECK-1 §2](../language/checking.md#2-встроенные-модули-std). Исполнение — [MACHINE-1 §5](../runtime/machine.md#5-примитивы-и-fault). Ниже каталог R24 — исторический перечень с расхождениями r25.

| Модуль | Состояние | Примечание |
| --- | --- | --- |
| `std.i64`, `std.value`, `std.seq`, `std.map`, `std.string`, `std.bytes`, `std.utf8`, `std.json`, `std.option`, `std.result` | реализовано (примитивы и функции на bagaev) | приёмка SA-002…SA-046 (кроме SA-001 — `std.bool`) и векторы DATA-0.1 — случаи `conformance/cases/stdlib` |
| `std.bool` | исключено | `not` — зарезервированное слово; оператор `not` (SURF-34) |
| `std.test` | реализовано: `expect`, `expect_equal` (FAULT `TEST_ASSERTION`) | STD-049…051 (`check`, `check_equal`, `all`) заменены |
| `std.codec` | позже: `IMPLEMENTATION_STOP NOT_IMPLEMENTED` | VALUE-CODEC-V1 не закрыт (BD07) |
| `std.store` | реализовано: хост (r31, HST-08) | заменяет STD-052…054 (D81, EFF-07, [services.md](services.md)) |
| `std.events` | исключено | форма `emit` и объявление `handler` (D81) |
| `map_pure`, `fold_pure`, `map_error_pure` | заменены | `seq.map`, `seq.fold`, `option.map`, `result.map`, `result.map_error` с эффект-переменной (D70) |

## Перечень функций

### std.bool

**STD-001 `std.bool.not`** — `(Bool) -> Bool`

true ↦ false; false ↦ true. Оба допустимых значения; никаких преобразований Int64→Bool.

Эффекты: `{}`; work schedule: `SCALAR`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Оба допустимых значения; никаких преобразований Int64→Bool.

### std.i64

**STD-002 `std.i64.eq`** — `(Int64, Int64) -> Bool`

Математическое равенство. MIN, MAX, −1, 0; bool не является Int64.

Эффекты: `{}`; work schedule: `SCALAR`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: MIN, MAX, −1, 0; bool не является Int64.

**STD-003 `std.i64.lt`** — `(Int64, Int64) -> Bool`

Математическое строгое signed-сравнение. MIN, MAX, −1, 0; bool не является Int64.

Эффекты: `{}`; work schedule: `SCALAR`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: MIN, MAX, −1, 0; bool не является Int64.

**STD-004 `std.i64.add`** — `(Int64, Int64) -> Result<Int64, ArithmeticError>`

Проверить представимость математического a+b. MAX+1 → Err(Overflow).

Эффекты: `{}`; work schedule: `SCALAR`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: MAX+1 → Err(Overflow).

**STD-005 `std.i64.sub`** — `(Int64, Int64) -> Result<Int64, ArithmeticError>`

Проверить представимость математического a−b. MIN−1 → Err(Overflow).

Эффекты: `{}`; work schedule: `SCALAR`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: MIN−1 → Err(Overflow).

**STD-006 `std.i64.mul`** — `(Int64, Int64) -> Result<Int64, ArithmeticError>`

Проверить представимость математического a×b. MIN×−1 → Err(Overflow); MIN×0 → Ok(0).

Эффекты: `{}`; work schedule: `SCALAR`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: MIN×−1 → Err(Overflow); MIN×0 → Ok(0).

**STD-007 `std.i64.div`** — `(Int64, Int64) -> Result<Int64, ArithmeticError>`

Сначала b=0; затем математическое частное с усечением к нулю; проверить Int64. MIN/−1 → Err(Overflow); 0/0 → Err(DivisionByZero).

Эффекты: `{}`; work schedule: `SCALAR`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: MIN/−1 → Err(Overflow); 0/0 → Err(DivisionByZero).

**STD-008 `std.i64.rem`** — `(Int64, Int64) -> Result<Int64, ArithmeticError>`

Сначала b=0; r=a−trunc(a/b)×b, без промежуточного Int64 quotient. MIN rem −1 → Ok(0); −7 rem 3 → Ok(−1).

Эффекты: `{}`; work schedule: `SCALAR`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: MIN rem −1 → Ok(0); −7 rem 3 → Ok(−1).

**STD-009 `std.i64.neg`** — `(Int64) -> Result<Int64, ArithmeticError>`

Проверить представимость математического −a. MIN → Err(Overflow).

Эффекты: `{}`; work schedule: `SCALAR`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: MIN → Err(Overflow).

**STD-010 `std.i64.parse_decimal`** — `(String) -> Result<Int64, ParseIntError>`

Сначала полностью проверить ASCII-грамматику -?(0|[1-9][0-9]*); затем отрицательное накопление цифр с пределом MIN для минуса, −MAX иначе; -0 допустим и даёт 0. Нет пробелов, +, Unicode digits, separators и leading zero; первая syntax error имеет приоритет над overflow в более раннем префиксе.

Эффекты: `{}`; work schedule: `PARSE_DECIMAL`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Граничные десятичные строки MIN/MAX; сверхдиапазонный префикс с последующей буквой даёт InvalidSyntax, не Overflow.

**STD-011 `std.i64.format_decimal`** — `(Int64) -> String`

Каноническая ASCII запись без плюса/leading zero; ноль — 0; отрицательное накопление избегает abs(MIN). parse_decimal(format_decimal(x))=Ok(x).

Эффекты: `{}`; work schedule: `FORMAT_DECIMAL`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: parse_decimal(format_decimal(x))=Ok(x).

### std.value

**STD-012 `std.value.equal`** — `<T:Eq>(T,T) -> Bool`

Структурный Eq по полному exact типу и правилам DATA-TYPES, включая Map. Option<Fn>.None и Seq<Fn>[] не получают Eq по пустоте.

Эффекты: `{}`; work schedule: `COMPARE`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Независимый математический Eq; nominal mismatch — type diagnostic до работы.

**STD-013 `std.value.compare`** — `<T:Key>(T,T) -> Int64`

Полный semantic Key order; результат строго −1, 0 либо 1. Int64 сравнивается signed; порядок не заменяется порядком wire bytes.

Эффекты: `{}`; work schedule: `COMPARE`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Int64 сравнивается signed; порядок не заменяется порядком wire bytes.

### std.option

**STD-014 `std.option.is_some`** — `<T>(Option<T>) -> Bool`

None → false; Some → true; payload не обходится. None имеет заранее известный T.

Эффекты: `{}`; work schedule: `TAG`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: None имеет заранее известный T.

**STD-015 `std.option.value_or`** — `<T>(Option<T>,T) -> T`

Some(x) → x; None → второй уже вычисленный аргумент. default вычисляется строго даже для Some; ленивого эффекта здесь нет.

Эффекты: `{}`; work schedule: `TAG`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: default вычисляется строго даже для Some; ленивого эффекта здесь нет.

**STD-016 `std.option.map_pure`** — `<A,B>(Option<A>, Fn([A],B,{})) -> Option<B>`

None → None без вызова closure; Some(x) → Some(f(x)). Closure argument создаётся строго; body для None не исполняется.

Эффекты: `{}`; work schedule: `MAP_OPTION`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Closure argument создаётся строго; body для None не исполняется.

### std.result

**STD-017 `std.result.is_ok`** — `<T,E>(Result<T,E>) -> Bool`

Ok → true; Err → false. Err — обычное значение.

Эффекты: `{}`; work schedule: `TAG`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Err — обычное значение.

**STD-018 `std.result.map_pure`** — `<A,B,E>(Result<A,E>, Fn([A],B,{})) -> Result<B,E>`

Err(e) → Err(e); Ok(x) → Ok(f(x)). Невзятая ветвь не вызывает f; semantic stop f не превращается в Err(E).

Эффекты: `{}`; work schedule: `MAP_RESULT`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Невзятая ветвь не вызывает f; semantic stop f не превращается в Err(E).

**STD-019 `std.result.map_error_pure`** — `<T,E,F>(Result<T,E>, Fn([E],F,{})) -> Result<T,F>`

Ok(x) → Ok(x); Err(e) → Err(f(e)). Результат f не является скрытым exception.

Эффекты: `{}`; work schedule: `MAP_ERROR`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Результат f не является скрытым exception.

### std.seq

**STD-020 `std.seq.length`** — `<T>(Seq<T>) -> Int64`

Число элементов; visiting order слева направо. Пустая последовательность → 0.

Эффекты: `{}`; work schedule: `LENGTH`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Пустая последовательность → 0.

**STD-021 `std.seq.get`** — `<T>(Seq<T>,Int64) -> Option<T>`

Some(xs[i]) при 0≤i<n, иначе None. Отрицательный индекс не считает от конца.

Эффекты: `{}`; work schedule: `GET`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Отрицательный индекс не считает от конца.

**STD-022 `std.seq.append`** — `<T>(Seq<T>,T) -> Seq<T>`

Все прежние элементы, затем новый. Старое значение сохраняется; превышение runtime cap — ImplementationStop.

Эффекты: `{}`; work schedule: `APPEND`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Старое значение сохраняется; превышение runtime cap — ImplementationStop.

**STD-023 `std.seq.concat`** — `<T>(Seq<T>,Seq<T>) -> Seq<T>`

Элементы левого, затем правого операнда. Оба аргумента вычислены; overflow размера не wrap.

Эффекты: `{}`; work schedule: `CONCAT`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Оба аргумента вычислены; overflow размера не wrap.

**STD-024 `std.seq.slice`** — `<T>(Seq<T>,Int64,Int64) -> Result<Seq<T>,BoundsError>`

Half-open [start,end); valid iff 0≤start≤end≤n. [n,n) — Ok([]); никакого clamp.

Эффекты: `{}`; work schedule: `SLICE`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: [n,n) — Ok([]); никакого clamp.

**STD-025 `std.seq.map_pure`** — `<A,B>(Seq<A>,Fn([A],B,{})) -> Seq<B>`

Последовательно f(xs[0]), f(xs[1]), …; каждый вызов ровно один. Никакого parallel map или сброса бюджета; empty не вызывает f.

Эффекты: `{}`; work schedule: `MAP_SEQ`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Никакого parallel map или сброса бюджета; empty не вызывает f.

**STD-026 `std.seq.fold_pure`** — `<A,B>(Seq<A>,B,Fn([B,A],B,{})) -> B`

Левый fold: a0=initial; a(i+1)=f(ai,xs[i]). Empty → initial; порядок отличается от fold_right.

Эффекты: `{}`; work schedule: `FOLD_SEQ`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Empty → initial; порядок отличается от fold_right.

### std.map

**STD-027 `std.map.build`** — `<K:Key,V>(Seq<Entry<K,V>>) -> Result<Map<K,V>,DataError>`

Готовые Entry(key,value) stage в исходном порядке; canonical insertion по Key. При дубликате вернуть первую повторную позицию j и самый ранний равный i. Никакого last-write-wins; все source operands вычислены до поиска duplicate.

Эффекты: `{}`; work schedule: `MAP_BUILD`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Никакого last-write-wins; все source operands вычислены до поиска duplicate.

**STD-028 `std.map.get`** — `<K:Key,V>(Map<K,V>,K) -> Option<V>`

Поиск semantic equal key в каноническом порядке. Номинально другой K не преобразуется.

Эффекты: `{}`; work schedule: `MAP_GET`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Номинально другой K не преобразуется.

**STD-029 `std.map.length`** — `<K:Key,V>(Map<K,V>) -> Int64`

Число canonical entries. Пустая карта → 0.

Эффекты: `{}`; work schedule: `LENGTH`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Пустая карта → 0.

**STD-030 `std.map.entries`** — `<K:Key,V>(Map<K,V>) -> Seq<Entry<K,V>>`

Копировать entries в возрастании Key. Insertion order/hash seed не видны.

Эффекты: `{}`; work schedule: `MAP_ENTRIES`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Insertion order/hash seed не видны.

**STD-031 `std.map.put`** — `<K:Key,V>(Map<K,V>,K,V) -> Map<K,V>`

Поиск слева направо; существующий равный ключ заменить новым key/value, иначе вставить в canonical position. Это явная операция замены, отличная от duplicate-отказа build.

Эффекты: `{}`; work schedule: `MAP_PUT`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Это явная операция замены, отличная от duplicate-отказа build.

**STD-032 `std.map.remove`** — `<K:Key,V>(Map<K,V>,K) -> Map<K,V>`

Удалить semantic equal entry, если есть; остальные сохранить. Отсутствующий ключ возвращает равное прежнему значение.

Эффекты: `{}`; work schedule: `MAP_REMOVE`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Отсутствующий ключ возвращает равное прежнему значение.

### std.string

**STD-033 `std.string.scalar_length`** — `(String) -> Int64`

Число Unicode scalar values, без normalization/locale. Один non-BMP scalar имеет длину 1; combining sequence может иметь длину 2.

Эффекты: `{}`; work schedule: `LENGTH`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Один non-BMP scalar имеет длину 1; combining sequence может иметь длину 2.

**STD-034 `std.string.scalar_get`** — `(String,Int64) -> Option<Int64>`

Числовой scalar на позиции i либо None вне диапазона. Возвращается scalar number, не UTF8 byte и не grapheme.

Эффекты: `{}`; work schedule: `GET`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Возвращается scalar number, не UTF8 byte и не grapheme.

**STD-035 `std.string.slice`** — `(String,Int64,Int64) -> Result<String,BoundsError>`

Half-open [start,end) в scalar positions. Канонически эквивалентные строки не отождествляются.

Эффекты: `{}`; work schedule: `SLICE`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Канонически эквивалентные строки не отождествляются.

**STD-036 `std.string.concat`** — `(String,String) -> String`

Последовательность scalars левого, затем правого значения. Нет normalization на границе склейки.

Эффекты: `{}`; work schedule: `CONCAT`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Нет normalization на границе склейки.

**STD-037 `std.string.from_scalars`** — `(Seq<Int64>) -> Result<String,ScalarError>`

Слева направо; принимать 0..D7FF и E000..10FFFF; первая неверная позиция. Surrogate и отрицательные значения → Err; noncharacters разрешены.

Эффекты: `{}`; work schedule: `VALIDATE_ITEMS`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Surrogate и отрицательные значения → Err; noncharacters разрешены.

**STD-038 `std.string.to_scalars`** — `(String) -> Seq<Int64>`

Числовые значения scalars в исходном порядке. from_scalars(to_scalars(s))=Ok(s).

Эффекты: `{}`; work schedule: `COPY_ITEMS`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: from_scalars(to_scalars(s))=Ok(s).

### std.bytes

**STD-039 `std.bytes.length`** — `(Bytes) -> Int64`

Число octets. Не UTF8 scalar length.

Эффекты: `{}`; work schedule: `LENGTH`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Не UTF8 scalar length.

**STD-040 `std.bytes.get`** — `(Bytes,Int64) -> Option<Int64>`

Some(unsigned octet 0..255) либо None вне диапазона. Отрицательный индекс не отсчитывается от конца.

Эффекты: `{}`; work schedule: `GET`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Отрицательный индекс не отсчитывается от конца.

**STD-041 `std.bytes.slice`** — `(Bytes,Int64,Int64) -> Result<Bytes,BoundsError>`

Half-open [start,end) по bytes. Можно разрезать UTF8 sequence; Bytes от этого не некорректны.

Эффекты: `{}`; work schedule: `SLICE`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Можно разрезать UTF8 sequence; Bytes от этого не некорректны.

**STD-042 `std.bytes.concat`** — `(Bytes,Bytes) -> Bytes`

Все octets левого, затем правого. Никакой перекодировки.

Эффекты: `{}`; work schedule: `CONCAT`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Никакой перекодировки.

**STD-043 `std.bytes.from_octets`** — `(Seq<Int64>) -> Result<Bytes,OctetError>`

Слева направо; принимать 0..255; первая неверная позиция. 256 и −1 → Err; нет modulo256.

Эффекты: `{}`; work schedule: `VALIDATE_ITEMS`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: 256 и −1 → Err; нет modulo256.

**STD-044 `std.bytes.to_octets`** — `(Bytes) -> Seq<Int64>`

Unsigned octets в исходном порядке. from_octets(to_octets(b))=Ok(b).

Эффекты: `{}`; work schedule: `COPY_ITEMS`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: from_octets(to_octets(b))=Ok(b).

### std.utf8

**STD-045 `std.utf8.encode`** — `(String) -> Bytes`

Строгий UTF8, без добавления BOM; точные RFC3629 scalars и R07 error-independent encoder. U+FEFF сохраняется как данные.

Эффекты: `{}`; work schedule: `UTF8_ENCODE`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`, `UTF8-WORK-0.1`. Независимая проверка: U+FEFF сохраняется как данные.

**STD-046 `std.utf8.decode`** — `(Bytes) -> Result<String,DataError>`

Строгий decoder и first-offset errors R07; никакого replacement mode. C0/C1 → Utf8Leading; truncated → offset начала sequence.

Эффекты: `{}`; work schedule: `UTF8_DECODE`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`, `UTF8-WORK-0.1`. Независимая проверка: C0/C1 → Utf8Leading; truncated → offset начала sequence.

### std.codec

**STD-047 `std.codec.encode`** — `<T:Persistable>(T) -> Bytes`

Canonical value encoding exact VALUE-CODEC-V1 из MeaningLock; полная registry/type binding. R07 DATA-wire не объявляется автоматически долговечным V1 codec.

Эффекты: `{}`; work schedule: `LOCKED_CODEC`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`, `VALUE-CODEC-V1`. Независимая проверка: R07 DATA-wire не объявляется автоматически долговечным V1 codec.

**STD-048 `std.codec.decode`** — `<T:Persistable>(Bytes) -> Result<T,DataError>`

Decoder exact VALUE-CODEC-V1; validate header/type/context/full consumption/canonical order; publish whole value. Unknown schema не выбирает ближайшую; пустой Seq<Fn> не проходит bound.

Эффекты: `{}`; work schedule: `LOCKED_CODEC`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`, `VALUE-CODEC-V1`. Независимая проверка: Unknown schema не выбирает ближайшую; пустой Seq<Fn> не проходит bound.

### std.test

**STD-049 `std.test.check`** — `(String,Bool) -> Check`

case_id и Bool → Pass(case_id) либо Fail(TestFailure{case_id,code=ConditionFalse(Unit)}). Check не является AcceptanceRecord и не снимает unknown.

Эффекты: `{}`; work schedule: `TEST_CHECK`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Check не является AcceptanceRecord и не снимает unknown.

**STD-050 `std.test.check_equal`** — `<T:Eq>(String,T,T) -> Check`

По semantic Eq сформировать Pass/Fail(ValueMismatch); не сериализовать значения/секреты в failure. Типы exact, не display-string comparison.

Эффекты: `{}`; work schedule: `TEST_EQUAL`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Типы exact, не display-string comparison.

**STD-051 `std.test.all`** — `(Seq<Check>) -> CheckSummary`

Перечислить все проверки, сохранить исходный порядок и индексы failed; total/passed/failed. Пустой набор имеет total0; отчёт не доказывает наличие обязательных проверок.

Эффекты: `{}`; work schedule: `TEST_ALL`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`. Независимая проверка: Пустой набор имеет total0; отчёт не доказывает наличие обязательных проверок.

### std.store

**STD-052 `std.store.snapshot`** — `<S:Persistable>(ReadCap<S>) -> Result<StateView<S>,StoreError>`

Под текущим read gate получить одну согласованную ActiveRef и root S; вернуть оба атомарно как одно наблюдение. Ref без current capability недостаточен; чтение не запускает приложение/миграцию.

Эффекты: `StoreRead(cap.store) `; work schedule: `SERVICE_READ`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`, `STORE-V1`, `CAPABILITY-V1`, `JOURNAL-V1`, `REGISTERED-SERVICE-V1`. Независимая проверка: Ref без current capability недостаточен; чтение не запускает приложение/миграцию.

**STD-053 `std.store.commit`** — `<S:Persistable,E:Persistable>(WriteCap<S,E>,ActiveRef<S>,KeyRef,S,Seq<NewEvent<E>>) -> Result<CommitKnowledge<S>,StoreError>`

Один local atomic commit: expected ActiveRef+generation, replacement root, ordered outbox, command digest/receipt. Exact existing key lookup перед fresh guards; no auto retry. Потеря ответа → lookup того же key; caller stop не делает NotApplied; подробности services.md.

Эффекты: `StoreCommit(cap.store), EventAppend(cap.output_log) `; work schedule: `SERVICE_WRITE`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`, `STORE-V1`, `EVENTS-V1`, `APP-IDEMPOTENCY-V1`, `CAPABILITY-V1`, `JOURNAL-V1`, `REGISTERED-SERVICE-V1`. Независимая проверка: Потеря ответа → lookup того же key; caller stop не делает NotApplied; подробности services.md.

**STD-054 `std.store.status`** — `<S:Persistable>(ReadCap<S>,KeyRef) -> Result<CommitKnowledge<S>,StoreError>`

Прочитать сохранённое знание об intent по текущим read rights, без выполнения команды. Отсутствие payload/expired key не означает NotApplied; generation closure сохранён.

Эффекты: `StoreRead(cap.store) `; work schedule: `SERVICE_READ`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`, `STORE-V1`, `APP-IDEMPOTENCY-V1`, `CAPABILITY-V1`, `JOURNAL-V1`, `REGISTERED-SERVICE-V1`. Независимая проверка: Отсутствие payload/expired key не означает NotApplied; generation closure сохранён.

### std.events

**STD-055 `std.events.read`** — `<E:Persistable>(EventReadCap<E>,EventCursor<E>,Int64) -> Result<EventPage<E>,EventError>`

Читать immutable журнал данной identity начиная после cursor, в commit order и ordinal внутри commit; limit1..256. Page закрепляет прочитанный frontier; новая запись не меняет прежнюю страницу; gap не empty success.

Эффекты: `EventRead(cap.input_log) `; work schedule: `SERVICE_READ`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`, `EVENTS-V1`, `CAPABILITY-V1`, `JOURNAL-V1`, `REGISTERED-SERVICE-V1`. Независимая проверка: Page закрепляет прочитанный frontier; новая запись не меняет прежнюю страницу; gap не empty success.

**STD-056 `std.events.apply`** — `<S:Persistable,E:Persistable,O:Persistable>(ConsumerCap<S,E,O>,ActiveRef<S>,EventRef<E>,S,Seq<NewEvent<O>>) -> Result<CommitKnowledge<S>,StoreError>`

Атомарно связать (consumer identity,event identity) с exact event digest, новым root, outbox и receipt. Duplicate returns prior receipt; payload conflict refuses; no external action in transaction. Повтор после изменения state не выполняет доменную правку заново; обновлённый consumer code не создаёт новый consumer автоматически.

Эффекты: `StoreCommit(cap.store), EventConsume(cap.input_log,cap.consumer), EventAppend(cap.output_log) `; work schedule: `SERVICE_WRITE`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`, `STORE-V1`, `EVENTS-V1`, `APP-IDEMPOTENCY-V1`, `CAPABILITY-V1`, `JOURNAL-V1`, `REGISTERED-SERVICE-V1`. Независимая проверка: Повтор после изменения state не выполняет доменную правку заново; обновлённый consumer code не создаёт новый consumer автоматически.

**STD-057 `std.events.status`** — `<S:Persistable,E:Persistable,O:Persistable>(ConsumerCap<S,E,O>,EventRef<E>) -> Result<CommitKnowledge<S>,StoreError>`

Read-only lookup dedup identity+event digest с текущим отдельным read permission. Наличие ConsumerCap без read operation не раскрывает receipt.

Эффекты: `EventRead(cap.input_log,cap.consumer) `; work schedule: `SERVICE_READ`. Требуемые контракты: `TYPE-V1`, `MACHINE-V1`, `STDLIB-API-0.1`, `EVENTS-V1`, `APP-IDEMPOTENCY-V1`, `CAPABILITY-V1`, `JOURNAL-V1`, `REGISTERED-SERVICE-V1`. Независимая проверка: Наличие ConsumerCap без read operation не раскрывает receipt.

## Явные диагностические области

| Префикс / имя | Код | Основание |
| --- | --- | --- |
| `std.float` | `UNSUPPORTED_FEATURE` | r26: Float исключён из V1 (D71). |
| `std.bigint` | `UNSUPPORTED_FEATURE` | r26: BigInt исключён из V1 (D71). |
| `std.recursive_data` | — | r26: модуль не нужен — рекурсивные типы — форма языка (D69). |
| `std.gpu` | `UNSUPPORTED_PROFILE` | Отдельный профиль T20. |
| `std.distributed` | `UNSUPPORTED_PROFILE` | Отдельный профиль T19. |
| `std.live_update` | `UNSUPPORTED_PROFILE` | Отдельный профиль T19. |
| `std.threads` | `UNSUPPORTED_FEATURE` | Shared mutable threads запрещены в V1. |
| `std.dynamic_load` | `UNSUPPORTED_FEATURE` | Произвольная dynamic loading запрещена в V1. |
| `std.io` | `REGISTERED_ADAPTER_REQUIRED` | Ввод/вывод объявляется exact typed host adapter, не ambient std export. |
| `std.net` | `REGISTERED_ADAPTER_REQUIRED` | Сеть только через зарегистрированный adapter/capability. |
| `std.shell` | `REGISTERED_ADAPTER_REQUIRED` | Нет ambient shell; явный adapter требует самостоятельного admission. |
| `std.env` | `REGISTERED_ADAPTER_REQUIRED` | Чтение environment — явный effect с exact adapter. |
| `std.clock` | `REGISTERED_ADAPTER_REQUIRED` | Нет скрытых часов; explicit adapter+journal. |
| `std.random` | `REGISTERED_ADAPTER_REQUIRED` | Нет hidden randomness; explicit adapter+journal. |
| `std.regex` | `UNSUPPORTED_STDLIB_API` | Regex не входит в этот минимальный каталог. |
| `std.unicode` | `UNSUPPORTED_STDLIB_API` | Locale/casefold/normalization/graphemes требуют отдельного exact package. |
| `std.result.unwrap` | `UNSUPPORTED_STDLIB_API` | Использовать полный Match; hidden panic отсутствует. |
| `std.option.unwrap` | `UNSUPPORTED_STDLIB_API` | Использовать полный Match; hidden panic отсутствует. |

Любое другое ненайденное имя получает UNKNOWN_STDLIB_SYMBOL, а известное имя с отсутствующим exact required contract — INPUT_NOT_READY с полным списком missing contract IDs. Границы префикса — сегменты пути, не startswith по буквам: std.gpuX не является std.gpu. Полные правила приоритета приведены в resolution.md.
