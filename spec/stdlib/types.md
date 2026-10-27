# STDLIB-TYPES-0.1 — типы, ошибки и владение

**Проект R24.** Имена ниже — стабильные проектные идентификаторы деклараций `bagaev.std/0.1/<name>`, не вычисленные content hashes. Production registry связывает каждый ID с exact body/revision/codec до допуска; нет совпадения типов только по display name. Смена body требует другой revision. Это метанотация контрактов, не окончательный синтаксис языка.

## 1. Уже существующие типы

Bool, Int64, Unit, String, Bytes, Seq, Map, Option, Result и Fn имеют значения и whole-type predicates из DATA-TYPES-0.1. Встроенные structural constructors сохраняются. Для Option порядок декларации None(Unit)=0, Some(T)=1; для Result — **Ok(T)=0, Err(E)=1**, как в точном DATA/R07 API §2. Перечисление имён вариантов в обзорном data-values.md не меняет явно заданные ordinals API. Новая registry фиксирует это явно; старый CORE shorthand `Result<T>` не переинтерпретируется. Типы несущих эффектов функций содержат закрытое finite множество, без effect-row polymorphism.

Все pure library значения неизменяемы. Нет передачи ownership или ресурса через DATA-копирование. Seq/Option/Result могут содержать closures внутри VM, но их Eq/Key/Persistable по-прежнему запрещены, если запрещён весь тип. Никакая std-функция не сериализует capability/handle/closure. `map_pure` не делает захваченный ресурс сериализуемым.

## 2. Полный перечень дополнительных публичных типов

Поля перечислены в declaration order. Generic arguments, не хранящиеся в payload, остаются частью exact nominal identity. Sum tags перечислены в declaration order. Вариант без содержательных данных несёт Unit. Примитивные/стандартные Option и Result не переобъявляются этим перечнем.

| Тип | Закрытая форма |
| --- | --- |
| Entry<K,V> | record `{key:K, value:V}` |
| ArithmeticError | sum `Overflow(Unit), DivisionByZero(Unit)`; точная смысловая связь с ERR-0.1 |
| BoundsError | record `{length:Int64, start:Int64, end:Int64}` |
| ScalarError | record `{index:Int64, value:Int64}` |
| OctetError | record `{index:Int64, value:Int64}` |
| ParseSyntaxReason | sum `Empty(Unit), SignOnly(Unit), LeadingZero(Unit), InvalidDigit(Unit)` |
| ParseSyntax | record `{index:Int64, reason:ParseSyntaxReason}` |
| ParseIntError | sum `InvalidSyntax(ParseSyntax), OutOfRange(Unit)` |
| DataErrorCode | closed sum tags из списка ниже, каждый с Unit |
| DataError | record `{code:DataErrorCode, first:Int64, second:Int64}` |
| TestFailureCode | sum `ConditionFalse(Unit), ValueMismatch(Unit)` |
| TestFailure | record `{case_id:String, code:TestFailureCode}` |
| Check | sum `Pass(String), Fail(TestFailure)` |
| FailedCheck | record `{index:Int64, failure:TestFailure}` |
| CheckSummary | record `{total:Int64, passed:Int64, failed:Int64, failures:Seq<FailedCheck>}` |
| ActiveRef<S> | record `{store_id:Bytes, authority_epoch:Int64, generation:Int64, state_version:Bytes, schema_ref:Bytes}` |
| StateView<S> | record `{active:ActiveRef<S>, value:S}` |
| KeyRef | record `{project_id:String, namespace_id:String, generation:Int64, key:String}`; validation и authority — отдельный APP-IDEMPOTENCY-V1 |
| NewEvent<E> | record `{event_id:Bytes, payload:E}` |
| EventRef<E> | record `{log_id:Bytes, event_id:Bytes, payload_digest:Bytes, schema_ref:Bytes}` |
| EventCursor<E> | record `{log_id:Bytes, authority_epoch:Int64, position:Int64, schema_ref:Bytes}` |
| EventEnvelope<E> | record `{ref:EventRef<E>, position:Int64, payload:E}` |
| EventPage<E> | record `{entries:Seq<EventEnvelope<E>>, next:EventCursor<E>, frontier:EventCursor<E>}` |
| CommitReceipt<S> | record `{intent_id:Bytes, request_digest:Bytes, previous:ActiveRef<S>, current:ActiveRef<S>, event_ids:Seq<Bytes>}` |
| CommitKnowledge<S> | sum `Applied(CommitReceipt<S>), Pending(Bytes), Unknown(Bytes), ClosedWithoutPayload(Bytes), KnownNotAdmitted(Unit)` |
| StoreErrorCode | sum `PermissionDenied, AuthorityUnavailable, SchemaMismatch, StaleState, KeyConflict, AdmissionClosed, KeyNotIssued, InvalidArgument, RecoveryRequired, CapacityExceeded, InputUnavailable`; каждый с Unit |
| StoreError | record `{code:StoreErrorCode, related_ref:Option<Bytes>}` |
| EventErrorCode | sum `PermissionDenied, AuthorityUnavailable, SchemaMismatch, InvalidCursor, InvalidLimit, JournalGap, InputUnavailable, RecoveryRequired`; каждый с Unit |
| EventError | record `{code:EventErrorCode, related_ref:Option<Bytes>}` |
| ReadCap<S> | opaque authority object: точная root/schema, разрешённые read operations, scope и live authority; не record для caller construction |
| WriteCap<S,E> | opaque authority object с отдельными read/write/outbox operation rights |
| EventReadCap<E> | opaque authority object точного event log/schema и read scope |
| ConsumerCap<S,E,O> | opaque authority object точного consumer ID, root/input/output schemas и отдельных consume, root-write, output-append, status/read rights |

DataErrorCode: DuplicateKey, Utf8Leading, Utf8Continuation, Utf8Overlong, Utf8Surrogate, Utf8Range, Utf8Truncated, UnexpectedEnd, ContextMismatch, InvalidEncoding, UnknownVariant, NonCanonicalMap, TrailingBytes. UTF8 first — offset байта; second=−1. DuplicateKey first/second — индексы исходных пар. Codec использует значения first/second только по exact VALUE-CODEC-V1; отсутствие этого контракта блокирует codec API. Изобретать новое значение по одному знакомому имени запрещено.

**Явное изменение представления:** в research DATA/R07 поле DataError.code было String с закрытым набором labels. В новом STD-TYPES оно становится nominal closed sum DataErrorCode с ordinals0..12 в порядке списка. Translation каждому допустимому старому label L сопоставляет variant L(Unit); неизвестный label отвергается. Это не same-type cast и не byte-compatible codec; Key order нового code определяется declaration ordinal, а не прежним String comparator. Любой перенос historical error evidence требует этой явной typed projection и не обещает совпадения bytes/cost. Общие V1 primitive forms используют именно одну новую DataError declaration вместе с библиотекой.

Это исчерпывающий перечень публичных type declarations данного библиотечного проекта: 33 имени экспортируются как `std.types.<Name>`, с точной arity из public_types каталога. Sum tags и record fields доступны через обычные constructor/Match/Field языка; дополнительные callable constructors не появляются. IDs nominal деклараций не делают эту таблицу уже реализованной wire schema.

ArithmeticError — единственная каноническая декларация новой registry, используемая и library i64, и общими arithmetic forms нового V1. R06 `ArithmeticError` остаётся историческим research type: для reuse нужна явная embedding/translation старого CORE в новую registry. Один только одинаковый список tag не разрешает без cast/translation смешивать nominal values двух редакций. Exact type identity и declared error tags входят в SymbolContract; библиотека не создаёт второй несовместимый тип под тем же именем внутри одного V1 snapshot.

## 3. Проверка ref/value границ

Для std service DTO `store_id/log_id/event_id/intent_id/request_digest/state_version/schema_ref/payload_digest` — ровно 32 octets; здесь используется точная semantic identity, не host pointer. Digest — SHA-256 exact canonical payload соответствующего закреплённого codec; arbitrary bytes, похожие на hash, не доказывают существование/допуск предмета. StateVersion, ProgramSnapshot и EventRef имеют разные типы и роли. Generation/authority_epoch положительны, position неотрицательна; все ≤MAX(Int64). Generation не wrap. У KeyRef числа переходят в decimal strings только в R16-style transport adapter, не в языке автоматически. ASCII/длины KeyRef — правила R16 §3.

Перед возвращением service проверяет DTO целиком, identity/schema/content binding, отсутствие лишних полей и ограничения значений. Malformed reply = boundary fault/ImplementationStop, не StoreError приложения. Входные значения правильного nominal type могут содержать невалидные ref bytes: проверка внешней identity даёт InvalidArgument/InvalidCursor до нового допуска. Capability выдаётся только доверенным runtime; его нельзя получить через data constructor или decode. Переданная ссылка всё равно проходит current authority gate.

Nominal wrappers здесь не добавляют неявные casts; например, EventRef одного schema нельзя использовать как другого. Field layout, tags и codec revisions входят в type identity. Ref может пережить конец сессии как данные, но не даёт authority и не обещает доступности/актуальности сохранённого состояния.

ReadCap/WriteCap/EventReadCap/ConsumerCap имеют semantic kind **Capability**, а не nominal data record без полей. Для каждого: Eq=false, Key=false, Persistable=false; container/Option/Result whole-type правила сохраняют запрет. Их type descriptors могут присутствовать в допустимом phantom metadata, но actual authority payload никогда не кодируется. Data DTO с настоящими phantom arguments, например ActiveRef<S>, оцениваются по своим полям, без добавления скрытого S payload; capability object при этом не возникает.

## 4. Ошибки и прекращение выполнения

Prelaunch type/bound/unknown symbol/missing contract диагностики не исполняют программу. Для допустимых аргументов BoundsError/ScalarError/OctetError/ParseIntError/DataError — Result values. При invalid slice сохраняются исходные start/end и фактическая length; проверка `start<0`, затем `end<start`, затем `end>n` не меняет shape error.

Parse decimal: пустая строка — InvalidSyntax(index0,Empty); единственный минус — index1,SignOnly; начальный плюс/не-ASCII-digit — первый invalid index; после первого нуля наличие следующего символа даёт LeadingZero на его позиции; после ненулевой первой цифры первая недесятичная scalar даёт InvalidDigit. Только полностью синтаксически корректный ввод проверяется на диапазон. Например, `99999999999999999999x` даёт InvalidDigit на позиции x, а такая же строка без x — OutOfRange.

Бюджет/отмена могут прекратить traversal раньше синтаксического вывода; это SemanticStop, не выдуманный результат Result. Физические caps, stack/allocator/process failure — ImplementationStop. Уже допущенное store/event намерение сохраняет собственное знание и обязательства после caller stop. StoreError не означает автоматически, что другая доставка того же ключа ничего не выполнила: точная интерпретация — [services.md](services.md).

## 5. Пределы и публикация

Общий MeaningLock содержит конкретные RuntimeLimits, ValueLimits, WorkContract, CodecContract. R24 не выдаёт малые DATA/R07 caps за production V1. Перед созданием нового значения проверяются prospective node/depth/scalar/octet/length bounds, включая оболочки Option/Result/Check/StateView. Checked addition до allocation; никакого wrap. Failure не публикует частичный authoritative value. Даже Unit и empty record требуют value nodes/arena units, несмотря на нулевой wire payload.

Service-specific limits: event page1..256; NewEvent batch≤256; event IDs в одном batch уникальны; итоговый payload и DTO дополнительно ограничены exact runtime/wire contracts. Увеличение этих пределов — новая contract revision. Общие value sizes не обещают конкретный CPU time/heap bound; platform limits отдельны.
