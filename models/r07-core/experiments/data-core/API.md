# DATA-0.1 — согласованный API R07

**Рабочий исследовательский контракт.** Это самостоятельные typed jobs над готовыми неизменяемыми значениями, а не source AST, расширение замороженного CORE или реализация всего V1. Проверка source expressions, функций, эффектов и durable state здесь не выполняется. Общие правила: [данные](../../spec/language/data-values.md), [TYPES](../../spec/language/types.md), [SEM](../../spec/language/semantic-core.md). Конкретные поля и charges этого API относятся только к DATA-0.1.

`PROFILE_REVISION='data-core/r07-v1'`, `CODEC_REVISION='data-wire/r07-v1'`.

## 1. Artifact, registry, типы

```text
Job(source_id, revision, schemas, operation,
    profile_revision=PROFILE_REVISION)
decode_job(raw_object) -> Job
prepare(job) -> Prepared
launch(job_or_prepared, budget, *, cancel_at=None, cancel_request_id='cancel') -> Machine
step(machine) -> Machine
run(job_or_prepared, budget, *, cancel_at=None, cancel_request_id='cancel') -> Execution
execution(machine) -> Execution                 # только terminal machine
execution_json(execution) -> JSON
value_json(value) -> {type:T, data:Payload}
predicate(schemas, type_json, name) -> bool     # Eq / Key / Persistable
canonical(value) -> JSON-compatible value
digest(value) -> SHA256 hex
```

Raw Job имеет ровно пять полей: `source_id`, `revision`, `schemas`, `operation`, `profile_revision`. Все вложенные входы глубоко фиксируются. Labels source_id/revision не являются доказательством идентичности: `content_digest` вычисляется из всего actual artifact. `Prepared` содержит проверенные индексы; launch повторно проверяет frozen Job и не доверяет присланным вручную summaries/indexes.

Тип `T` — одна из закрытых форм:

```text
"Bool" | "Int64" | "Unit" | "String" | "Bytes" | "DataError"
| "Capability" | "HostHandle"
{"tag":"var", "id":TypeParamId}
{"tag":"fn", "params":[T,...], "result":T}
{"tag":"seq", "item":T}
{"tag":"map", "key":T, "value":T}
{"tag":"option", "item":T}
{"tag":"result", "ok":T, "err":T}
{"tag":"nominal", "id":TypeId, "revision":Revision, "args":[T,...]}
```

Capability/HostHandle/Fn допускаются в type metadata, но не имеют создаваемых runtime values этого профиля. Поэтому пустой Seq<Fn> и Option<Fn>.None допустимы как готовые значения, а Eq/Key/Persistable для них ложны. `var` разрешён только в body объявившей parameter schema, не в ground operand. Forall и higher-kinded arguments отсутствуют.

Schema — exact object:

```text
record: {id, revision, kind:'record', type_params:[Parameter,...],
         codec:CODEC_REVISION|null, fields:[{id, type:T},...]}
sum:    {id, revision, kind:'sum', type_params:[Parameter,...],
         codec:CODEC_REVISION|null, variants:[{id, type:T},...]}
Parameter = {id:TypeParamId, bounds:[PredicateName,...]}
```

Exact `(id,revision)` уникален; разные revisions одного id могут сосуществовать как разные exact refs. Parameter IDs уникальны во всём registry; field/tag IDs уникальны внутри декларации. Record может быть пустым; sum непуст. Порядок declarations, parameters, fields и variants сохраняется и входит в binding. Bounds — уникальные элементы Eq/Key/Persistable; произвольная регистрация реализации predicates запрещена. `codec` принимает только указанную поддержанную revision или null. Все ссылки, arity и bounds проверяются до запуска; dependency graph по **всем** type positions должен быть DAG. Цикл → `PENDING_RECURSIVE_DATA`, не вывод о невозможности recursive types в V1.

Nominal predicate выводится после substitution по всем полям/всем payloads. Phantom parameter не является полем: `Phantom<Fn>{}` может иметь все три predicates. Exact Fn descriptor остаётся в identity и codec type digest; функция/closure не сериализуется. Eq/Key/Persistable следуют таблице TYPES §9; Map никогда не Key, Eq(Map) требует Key(K) и Eq(V). Registered codec дополнительно необходим для Persistable nominal. Metadata encodability проверяется отдельно и не даёт Persistable function value.

## 2. Готовые operand values

Operand `V` — exact `{type:T, data:Payload}`. Это внешний ввод: prepare заново проверяет весь payload, а не принимает его за trusted Value. `value_json` позволяет явно перенести результат следующему job как такой ввод. Прямой внутренний Value с прежним registry не принимается вместо JSON operand. Registry и type binding каждого job вычисляются заново.

| Тип | Payload |
| --- | --- |
| Bool / Int64 / Unit | exact bool / int в signed64, bool запрещён / null |
| String | Unicode scalar string; surrogates запрещены, normalization отсутствует |
| Bytes | array exact ints 0…255, bool запрещён |
| Seq<T> | array payloads T |
| Map<K,V> | array `{key:PayloadK,value:PayloadV}` в строго возрастающем semantic Key order |
| Record | object ровно объявленных field IDs; порядок object keys не является порядком выражений |
| Sum / Option / Result | exact `{tag:TagId, value:Payload}` |
| DataError | exact `{code:ErrorCode, first:Int64, second:Int64}` |

Option ordinals: None(Unit)=0, Some(T)=1. Result ordinals: Ok(T)=0, Err(E)=1. Nominal sum ordinals — declaration order. Field order DataError: code:String, first:Int64, second:Int64. Для него все predicates true; значение code ограничено опубликованными ErrorCode ниже. Внешнее значение DataError допускает любые signed64 first/second, включая отрицательные; ограничения offset/witness являются postconditions ошибок, создаваемых операциями, а не зависимым инвариантом этого типа. Encoder и decoder принимают одинаковый домен. Кодирование DataError использует эти три поля, а не host exception text.

Проверка готового Map отвергает duplicate/неупорядоченный payload **до запуска**; для построения из произвольного source order существует map_build. Типовая проверка, порядок готового map и physical input validation выполняются вне runtime step budget и имеют собственные конечные guards. Они не вычисляют equal/compare/codec result выбранной операции.

## 3. Закрытые операции

Ниже указаны все поля объекта operation; неизвестное или пропущенное поле — диагностика. V означает готовый typed operand, не выражение.

| op | Остальные поля | Результат |
| --- | --- | --- |
| `record` | `type:T`, `fields:[{id,value:V},...]` | указанный nominal record; exact набор полей, inputs в данном порядке |
| `variant` | `type:T`, `tag`, `value:V` | nominal sum / Option / Result |
| `sequence` | `item_type:T`, `items:[V,...]` | Seq<T> |
| `map_build` | `key_type:K`, `value_type:VType`, `entries:[{key:V,value:V},...]` | Result<Map<K,VType>,DataError> |
| `field` | `record:V`, `field:FieldId` | тип поля nominal record |
| `equal` | `left:V`, `right:V` | Bool; exact одинаковый Eq type |
| `compare` | `left:V`, `right:V` | Int64 −1/0/1; exact одинаковый Key type |
| `length` | `value:V` | Int64; String scalars, Bytes octets, Seq items либо Map entries |
| `seq_get` | `sequence:V`, `index:V` | Option<T>; index:Int64; negative/out-of-range → None |
| `seq_append` | `sequence:V`, `value:V` | Seq<T>; новый immutable результат |
| `map_get` | `map:V`, `key:V` | Option<VType> |
| `utf8_encode` | `value:V` | Bytes; value:String |
| `utf8_decode` | `value:V` | Result<String,DataError>; value:Bytes |
| `encode` | `value:V` | Bytes; require Persistable(type) |
| `decode` | `type:T`, `bytes:V` | Result<T,DataError>; bytes:Bytes; require Persistable(T) |

Cross-nominal comparison → `TYPE_MISMATCH`, не Returned false. Phantom schema bounds проверяются даже при пустом body. Для map_build все готовые pairs сначала stage в input order; только затем начинается сортировка. Первая повторная входная позиция j возвращает Err с `first=i`, `second=j`, где i — самая ранняя предшествующая равная позиция. Индексы с нуля. Ключ не включается в fixed metadata error. Нет last-write-wins. Поздние source expressions отсутствуют в DATA; их выполнение перед duplicate check остаётся обязанностью интеграции V1.

## 4. Reference work и сравнение

TraceEntry — exact `{step_index,rule,path}`; index начинается с 1, path — array string/int компонентов, bool не является индексом. Пути ниже относятся к логическому operand, не обещают source spans. Каждое указанное правило стоит ровно один semantic step. Машина хранит незавершённые cursor/stack/buffer states и действительно выполняет следующий unit после guards; готовые результат/трасса bulk operation заранее не вычисляются.

Каждый job начинает `JOB_START` на `[]`. Успех публикуется правилом `JOB_FINISH` на `[]`; оно образует typed result из завершённой работы. После него нет дополнительного RETURN charge. Обнаруженный во время работы typed error публикует Err в том же faulting charged rule, без JOB_FINISH. Semantic/physical stops не публикуют частичный decoded value.

### 4.1. Простые операции

- record: `RECORD_FIELD` для каждого input field на `["fields",i]`, затем JOB_FINISH; canonical result fields в declaration order.
- variant: `VARIANT_WRAP` на `["value"]`, затем JOB_FINISH.
- sequence: `SEQUENCE_ITEM` для каждого i на `["items",i]`, затем JOB_FINISH.
- field: `FIELD_SELECT` на `["record",field_id]`, затем JOB_FINISH.
- length: `LENGTH_ITEM` для каждого scalar/octet/item/entry на `["value",i]`, затем JOB_FINISH. Пустое значение не выполняет LENGTH_ITEM.
- seq_get: `SEQ_GET` на `["sequence"]`, затем JOB_FINISH.
- seq_append: `SEQUENCE_ITEM` для каждого прежнего элемента на `["sequence",i]`, `SEQUENCE_APPEND` на `["value"]`, затем JOB_FINISH.

### 4.2. Comparator

equal/compare вызывают один structural comparator с root `["compare"]`. `COMPARE_NODE` посещает каждую сравниваемую пару значений. Для Bool/Int64/Unit он даёт ответ сразу. Для sum он сравнивает ordinal; при разных tags payload не посещается. Для String/Bytes каждый очередной scalar/octet пары сравнивается `COMPARE_UNIT` на path+[i]. После равного общего prefix `COMPARE_END` сравнивает длины.

Для Seq/Record/одного sum payload `COMPARE_NEXT` на child path выбирает ровно одного следующего child, затем выполняется его COMPARE_NODE. Child paths: Seq +[i], Record +[field_id], Sum +[tag]. После равного общего prefix `COMPARE_END` возвращает length comparison для Seq либо 0 для Record/Sum. Первый ненулевой child result прекращает дальнейший обход без дополнительных END rules.

Eq(Map) при разных длинах возвращает false непосредственно в COMPARE_NODE. Иначе сравнивает canonical pairs: key, затем value; children +[i,"key"] / +[i,"value"], каждый через COMPARE_NEXT и recursive comparison; после всех равных children выполняет COMPARE_END на map path. Здесь nonzero означает неравенство и не объявляется Key order для Map. DataError сравнивается как record из трёх полей. Скалярный String comparison использует ord, Bytes — unsigned byte, Int64 — signed mathematical order; codec bytes не заменяют Key order.

### 4.3. Map work

map_build выполняет `MAP_STAGE` на `["entries",j]` для всех pairs. Затем вставляет j=0…n−1 в уже отсортированный prefix. Для каждого probe i слева направо: `MAP_PROBE` на `["entries",j,"probe",i]`, comparator на том же path, `MAP_DECIDE` на том же path. Равенство публикует DuplicateKey с earliest original source position сохранённой пары. Greater продолжает поиск; Less выбирает insertion position. Конец prefix выбирает append без probe.

Пересборка после выбора позиции выполняет `MAP_COPY` для каждой старой пары на `["entries",j,"copy",i]` и `MAP_ADD` для новой пары на `["entries",j]` в результирующем порядке; `MAP_COMMIT` на `["entries",j]` публикует новый sorted prefix. Ни host sort, ни bulk semantic insertion не заменяют эти rules. После всех j JOB_FINISH образует Ok(map). map_get использует `MAP_LOOKUP` + comparator + `MAP_LOOKUP_DECIDE` на `["map",i]`; equality → Some, искомый key меньше текущего → None; исчерпание entries — `MAP_LOOKUP_END` на `["map"]`, затем JOB_FINISH.

## 5. UTF-8

utf8_encode: каждый Unicode scalar обрабатывается `UTF8_SCALAR` на `["value",i]`, создавая не более четырёх pending octets; каждый octet добавляется `UTF8_WRITE` на `["bytes",j]`. BOM не добавляется. Затем JOB_FINISH.

utf8_decode: один входной octet за `UTF8_READ` на `["bytes",j]`. После всех bytes `UTF8_END` на `["bytes"]` проверяет незавершённую sequence; затем JOB_FINISH. Decoder хранит start offset, expected continuation count и accumulator. Invalid leading byte → Utf8Leading; не-continuation внутри sequence → Utf8Continuation. Для E0/ED/F0/F4 ограничения второго octet проверяются при его чтении: Utf8Overlong / Utf8Surrogate / Utf8Range. F5…FF дают Utf8Leading. Неполная sequence в конце → Utf8Truncated. Ошибка first указывает offending octet; для truncated — начало незавершённой sequence. second всегда −1. C0/C1 — Utf8Leading. U+0000/U+FEFF и noncharacters допустимы; normalization отсутствует.

## 6. Частный canonical wire codec

Это **не CBOR**, не долговечный формат полного V1 и не миграция schemas. Header:

```text
ASCII BD07 + octet 01 + registry_digest (32 raw bytes) + type_digest (32 raw bytes)
```

Всего 69 octets. Type digest относится к exact ground T; metadata Fn внутри Phantom допустима. Registry digest связывает **весь** registry: даже изменение неиспользованной декларации несовместимо с этим консервативным R07 envelope. Digest не аутентифицирует payload и не является MAC.

Payload type-directed:

| Тип | Wire |
| --- | --- |
| Bool | octet 0/1 |
| Int64 | 8 octets signed big-endian two's complement |
| Unit | пусто |
| String | unsigned BE32 UTF-8 byte length, затем exact UTF-8 |
| Bytes | unsigned BE32 length, затем octets |
| Seq | unsigned BE32 count, затем элементы |
| Map | unsigned BE32 count, затем key/value каждой canonical pair |
| Record / DataError | поля в declaration order без ID/count |
| Sum / Option / Result | unsigned BE32 tag ordinal, затем payload |

Encoder: header octets по `ENCODE_WRITE` на `["wire",offset]`; затем `ENCODE_NODE` на `["value"]`. Каждый recursive child предваряется `ENCODE_NEXT` на child path (paths как у comparator). Каждый реальный octet, включая fixed-width scalars и length prefixes, требует ENCODE_WRITE. String сначала считает encoded length: `ENCODE_SCAN` на path+[scalar_index] для каждого scalar; после BE32 каждый scalar проходит `ENCODE_SCALAR` на том же path и emits 1…4 octets. Bytes не требуют дополнительного per-byte semantic scan сверх WRITE. После root JOB_FINISH публикует Bytes.

Decoder: каждый ожидаемый octet читается `DECODE_READ` на `["wire",offset]`, включая попытку прочитать EOF, которая возвращает UnexpectedEnd с first=offset. Header mismatch → ContextMismatch с first=первый отличающийся offset. После header `DECODE_NODE` на `["value"]`; recursive child предваряется `DECODE_NEXT`. Fixed scalar после bytes завершается `DECODE_SCALAR`; length BE32 — `DECODE_LENGTH`; ordinal BE32 — `DECODE_TAG`. Unit завершается самим DECODE_NODE. String scalar UTF-8 state обновляется при каждом DECODE_READ; ошибки имеют абсолютный wire byte offset. Пустые/составные decoded containers закрываются `DECODE_ASSEMBLE` на их path. String/Bytes закрываются DECODE_SCALAR. Sum закрывается DECODE_ASSEMBLE после payload.

Decoded Map после каждой завершённой пары, кроме первой, сравнивает предыдущий и новый key: comparator path=map_path+[i,"order"], затем `DECODE_MAP_ORDER` на этом path. Требуется строго Less; иначе NonCanonicalMap с first=offset начала текущего key, second=−1. Эти comparisons включены в charges. После root `DECODE_END` на `["wire",consumed]` отвергает остаточные bytes (TrailingBytes, first=consumed), затем JOB_FINISH образует Ok(value).

Недопустимый Bool byte, DataError code/shape → InvalidEncoding с first=начало соответствующего decoded value. Неизвестный sum ordinal → UnknownVariant с first=начало ordinal. Завершённый declared String byte span с незавершённой UTF-8 sequence даёт Utf8Truncated на DECODE_SCALAR с first=absolute start этой sequence; реальный EOF раньше declared length даёт UnexpectedEnd на DECODE_READ. Невозможный размер из объявленного length **сам по себе** не объявляется malformed wire: published physical guard может дать ImplementationStop до allocation. Все decode failures возвращают Result.Err без частичного value. Все bytes должны быть потреблены.

**Roundtrip headroom.** Encode до запуска требует payload nodes≤4 095, payload depth≤31 и admissible type metadata для производного `Result<T,DataError>` в пределах depth32/nodes8 192. Проверяется metadata prospective decode Job с теми же source_id/revision/profile_revision/schemas, operation=`{op:'decode',type:T,bytes:{type:'Bytes',data:[]}}`; тело value заранее не кодируется. `raw_node_count` считает каждый object, array и scalar ровно один раз; object keys не считаются nodes. Runtime cap encode равен `min(32 768, 65 536−raw_node_count(prospective_empty_decode_job))`. За один добавленный wire byte raw node count будущего Bytes operand увеличивается ровно на один. Этот cap проверяется до каждого ENCODE_WRITE; превышение → OUTPUT_LIMIT без charge. Следовательно, successful encode можно перенести в этот точный prospective decode envelope, сохранив input/type/value headroom. Другие labels/дополнительные transport wrappers не включены в это обещание. Roundtrip сравнивается при том же registry/type/codec, достаточном semantic budget и соблюдении остальных опубликованных work guards; это не универсально доказанный theorem.

ErrorCode: `DuplicateKey`, `Utf8Leading`, `Utf8Continuation`, `Utf8Overlong`, `Utf8Surrogate`, `Utf8Range`, `Utf8Truncated`, `UnexpectedEnd`, `ContextMismatch`, `InvalidEncoding`, `UnknownVariant`, `NonCanonicalMap`, `TrailingBytes`. Для ошибок, возвращаемых операциями, DuplicateKey first/second — позиции input entries; для остальных first — byte offset, second=−1. Это обычные значения DataError внутри Result; произвольно поданный DataError сохраняет домен §2.

## 7. Boundary, limits, receipts

Граница каждого step: уже terminal → visible cancellation → zero remaining budget → physical guard следующего unit → один charged unit. `cancel_at=k` виден после k completed transitions. Нулевой budget одновременно с cancel_at=0 даёт CANCELLED. Если последний charged unit уже опубликовал Returned, поздняя отмена его не заменяет. No-op step terminal machine не тратит ничего.

Execution — exact JSON-поля:

```text
profile_revision, codec_revision, content_digest, registry_digest,
termination, code, value, steps, remaining, trace, cancel_request_id
```

RETURNED/RETURNED содержит value_json (в том числе обычный Result.Err). SEMANTIC_STOP имеет code CANCELLED или BUDGET_EXCEEDED, value=null. IMPLEMENTATION_STOP имеет code VALUE_LIMIT, OUTPUT_LIMIT, WORK_LIMIT или MACHINE_INVARIANT, value=null. cancel_request_id заполнен только у CANCELLED. Physical refusal не добавляет charged entry отказавшего unit; ранее завершённые units сохраняются. Diagnostic receipt не содержит partial value/частичный wire output.

Входные guards: raw JSON ≤65 536 nodes, depth≤128; registry≤64 declarations, parameter≤8 на декларацию, fields/variants≤64, Fn params≤64; type metadata depth≤32, ID/labels≤128 scalars. Parsing имеет отдельный cumulative cap 8 192 посещений на registry и все operand types одного prepare (encode также резервирует prospective Bytes operand). Predicate derivation имеет собственный cumulative cap 8 192 посещений; каждый substituted layout member и derived result type отдельно проверяются на depth32/nodes8 192. Эти три guards не являются одним общим счётчиком. Для одного готового value: ≤4 096 data nodes, depth≤32, String≤1 024 scalars, Bytes≤32 768 octets, Seq/Map≤256 items/entries. Operation fields/items/entries≤256 (record всё равно ограничен schema). Budget и cancel_at — exact integer 0…262 144; bool запрещён. Это новая DATA граница; CORE сохраняет прежнюю. Prelaunch выход за bound → `PROFILE_LIMIT`, kind UnsupportedInputProfile; malformed/type input → PrelaunchDiagnostic. Guards не являются resource policy полного V1.

Глубина считается по рёбрам от root: scalar leaf и пустой data container имеют depth0; непустой container имеет 1+max(child depth). Каждый data value, включая leaf/пустой container, даёт один node; String scalars и Bytes octets проверяются отдельными length guards и не являются дочерними data nodes. Type metadata и raw JSON также считают root на depth0; их nodes следуют соответствующим деревьям, а не data payload.

Runtime: wire output≤32 768 octets (encode также имеет envelope cap выше), String/Bytes/container/value bounds такие же, pending work frames≤4 096. Guard проверяется до увеличения соответствующего результата/буфера. Decoder имеет cumulative counter посещённых data nodes; DECODE_NODE сверх4 096 или на depth>32 отказывается до charge. Производный Ok wrapper дополнительно проверяется при JOB_FINISH. После четырёх READ length>256 для Seq/Map, >4 096 для String byte span или >32 768 для Bytes отказывается в DECODE_LENGTH: VALUE_LIMIT, сам DECODE_LENGTH не charged. String scalar count проверяется также при каждом сформированном scalar. OUTPUT_LIMIT проверяется до ENCODE_WRITE/UTF8_WRITE. Сравнение и обход выполняют bounded logical unit; semantic cost не равен wall-clock time, allocation cost, hashing или диагностическому JSON rendering. Metadata hashing и prelaunch checking имеют свои пределы, не входят в runtime steps. Нет обещания speedup.

Prelaunch основные коды: UNSUPPORTED_PROFILE, UNSUPPORTED_CODEC, UNKNOWN_OPERATION, UNKNOWN_PREDICATE, UNKNOWN_FIELD, MISSING_FIELD, INVALID_SHAPE, INVALID_ID, INVALID_UNICODE_SCALAR, INVALID_LITERAL, INVALID_TYPE, UNKNOWN_TYPE, UNKNOWN_TAG, DUPLICATE_SCHEMA, DUPLICATE_TYPE_PARAMETER, DUPLICATE_FIELD, DUPLICATE_TAG, TYPE_ARGUMENT_ARITY, UNBOUND_TYPE_VARIABLE, PENDING_RECURSIVE_DATA, BOUND_NOT_SATISFIED, TYPE_MISMATCH, KEY_REQUIRED, EQ_REQUIRED, NOT_PERSISTABLE, UNSUPPORTED_VALUE_TYPE, NON_CANONICAL_MAP_INPUT, INVALID_BUDGET, INVALID_CANCELLATION, PROFILE_LIMIT. `DataCoreError(code,path=(),detail='',kind='PrelaunchDiagnostic')` не является Returned Err.

## 8. Canonical bindings и граница исследования

Canonical JSON: UTF-8; sort_keys=True; separators=(',',':'); ensure_ascii=False; allow_nan=False. Массивы сохраняют порядок. Registry preimage: `{profile_revision:PROFILE_REVISION,codec_revision:CODEC_REVISION,schemas:canonical(schemas)}`. Type preimage: `{profile_revision:PROFILE_REVISION,codec_revision:CODEC_REVISION,type:canonical(T)}`. Job content preimage: `{profile_revision:PROFILE_REVISION,codec_revision:CODEC_REVISION,job:canonical(job)}`. Flags codec=null и bounds включены без удаления; одинаковые произвольные labels с другими bytes дают другой digest.

API принимает уже разобранные JSON-compatible objects. Обнаружение повторяющихся object keys в исходном JSON text относится к транспортному parser, которого здесь нет; duplicate list fields/schema IDs проверяются непосредственно. Никакие record fields не утверждаются повторяемыми в positional wire.

Pure authorship demonstration — внешняя композиция этих обычных jobs с зафиксированными input/result refs; она не получает скрытый authorship builtin. Attribution не является ACL. В отчёте должны оставаться `bagaev_execution=false`, `research_data_execution=true`, `source_expression_execution=false`, `hypothesis_tested=false`, `full_v1_conformance=false`, `universal_proof=false`, `database_execution=false`. Никакая конечная матрица не закрывает T04/T06/T07/T13/T16 целиком.
