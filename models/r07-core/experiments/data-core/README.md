# DATA-0.1: номинальные данные и прерываемая работа

Этот каталог содержит отдельную исследовательскую машину Python stdlib для **готовых типизированных значений**. Она проверяет согласованность небольшой алгебры данных, структурных predicates, canonical Map, строгого UTF-8 и частного codec с точной последовательностью semantic steps. Она не исполняет source expressions bagaev и не меняет замороженный CORE R06. Точные поля, правила, ошибки и ограничения находятся в [API.md](API.md).

## Что выполняется

Профиль поддерживает Bool/Int64/Unit/String/Bytes, Seq/Map, Option/Result, nominal records/sums и явные generic type arguments. Объявления образуют конечный DAG. Exact ref содержит TypeId и revision; actual registry content также входит в digest. Подмена декларации при сохранении её labels не сохраняет codec context.

Eq, Key и Persistable выводятся из всех объявленных полей или payloads после substitution. Они не выводятся только из текущего payload: например, Option<Fn>.None и пустой Seq<Fn> не становятся Persistable. У phantom parameter, отсутствующего в полях, другая структура: зарегистрированный Phantom<Fn>{} может сериализоваться, сохраняя exact Fn metadata в type binding. Реальные function values, capabilities и host handles в этом профиле не создаются.

Есть 15 закрытых jobs: constructors record/variant/sequence/map_build; field, equal/compare, length, seq_get/seq_append/map_get; UTF-8 encode/decode; wire encode/decode. Аргументы уже вычислены. MapBuild сначала посещает все входные пары, затем выполняет явную insertion procedure. Duplicate возвращает обычный Result.Err с первой повторной входной позицией и самой ранней равной предшествующей позицией; он не перезаписывает прежнее значение. Canonical order — semantic Key order, включая signed order Int64, а не порядок wire bytes.

## Машина и границы стоимости

`prepare` глубоко фиксирует Job и проверяет его форму, nominal references, bounds и ready values. Это отдельная ограниченная prelaunch фаза. Она может проверять порядок уже готового Map, но не вычисляет ответ/трассу выбранного runtime job. Labels source_id/revision остаются labels; receipt содержит digest фактического artifact.

`launch`, `step`, `run` работают через явный стек задач и continuation records. Сравнение посещает следующий scalar/child только своим правилом. Codec обрабатывает следующий node/octet после проверки guards; UTF-8 хранит незавершённую sequence; map insertion явно сравнивает и копирует очередную пару. Большой результат или trace не готовятся перед первым шагом. Внутренние административные continuations только передают уже завершённые результаты; новые посещения получают отдельный rule.

Каждое из 40 правил стоит ровно один step и записывает индекс, RuleId и logical operand path. JOB_START и успешный JOB_FINISH также charged. Typed runtime error публикуется своим обнаружившим правилом без дополнительного JOB_FINISH. Byte buffers и trace используют persistent links; их финальное диагностическое представление не является заявлением о стоимости CPU или allocation.

На каждой границе порядок фиксирован: terminal, затем cancellation, затем нулевой budget, затем physical guard следующей работы. `cancel_at=k` виден после k завершённых правил. Ни stop, ни отказавший physical unit не получают дополнительного charge. Частичный decoded value или wire output в Execution не публикуется. Вернувшийся Result.Err является обычным typed value, а не SEMANTIC_STOP.

Входные и runtime ограничения опубликованы в API. В частности, step/cancel cap равен 262144, Bytes/output cap — 32768, ready data nodes — 4096, depth — 32, Seq/Map length — 256. Raw JSON и metadata имеют отдельные guards. Это пределы исполнимого профиля, а не нормативные пределы полного V1. Работа с источниками, рекурсивными nominal данными, эффектами, durable state, concurrency и native compiler остаётся вне этой машины.

## Частный codec и roundtrip

Wire начинается с `BD07\x01`, SHA-256 всего registry и SHA-256 exact ground type. Далее используется type-directed positional payload с fixed-width lengths/ordinals. Это исследовательский формат `data-wire/r07-v1`, **не CBOR**. Header закрепляет context, но не аутентифицирует payload и не выполняет schema migration. Даже изменение неиспользованной декларации меняет whole-registry binding.

Encoder резервирует место для будущего decode Ok wrapper, metadata Result<T,DataError> и точного prospective decode input envelope. Wire cap дополнительно сужается по свободным raw JSON nodes этого envelope. Поэтому успешные Bytes можно передать в согласованный decode Job с теми же labels/registry/type и достаточным budget; изменение transport wrappers или лимитов требует собственной проверки. Payload не кодируется заранее ради расчёта cap.

Decoder проверяет строгий UTF-8, ordinal, boolean encoding, closed DataError code, возрастающий порядок map keys и отсутствие trailing bytes. Malformed wire возвращает typed Result.Err с точной позицией. Опубликованный physical bound может остановить oversized input без вывода о том, что wire семантически некорректен. Внешние first/second поля DataError имеют обычный signed64 домен; offset/witness ограничения относятся к ошибкам, создаваемым операциями.

## Воспроизведение и независимое сравнение

Из корня R07:

```sh
python -B experiments/data-core/verify.py --output results/data-core/report.json
```

Независимый oracle, authored fixtures и verifier поддерживает другой участник исследования. Oracle не импортирует этот engine, его predicates или work implementation. Сравнение включает весь опубликованный outcome и точную trace, отдельные malformed inputs, budget/cancel boundaries, wire vectors, реальные различающие mutations и внешнюю pure authorship композицию обычных jobs. Команда `--smoke` выполняет ограниченное integration сравнение без записи финального report.

Фактические counts, source hashes, граница конечного корпуса и результаты находятся в [машинном отчёте](../../results/data-core/report.json), создаваемом verifier после freeze источников. README не подменяет этот отчёт заранее объявленными числами. Pure authorship bridge не является новым builtin: каждый его шаг передаёт обычный typed job и получает обычный receipt. Он проверяет атрибуцию и построение индекса; ACL и durable транзакции остаются отдельными контрактами.

В evidence сохраняются `bagaev_execution=false`, `research_data_execution=true`, `source_expression_execution=false`, `hypothesis_tested=false`, `full_v1_conformance=false`, `universal_proof=false`, `database_execution=false`. Конечная проверка может обнаружить расхождение конкретных двух реализаций и authored expectations. Она не доказывает универсальную корректность языка, performance gain, полный V1, интеграцию source expression ordering или полезность bagaev в T15 A/B/C.
