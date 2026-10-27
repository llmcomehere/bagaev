# CODEC-0.1 — точное представление неизменяемых данных

**R07 · WORKING_DESIGN.** Ниже описан value codec исследовательского DATA, его условия корректности и границы интеграции. Exact transport, error codes/offset rules, limits и work-rule IDs задаёт [DATA API](../../models/r07-core/experiments/data-core/API.md). Это собственный ограниченный формат BD07, не CBOR/JSON и не заявление о совместимости с ними. Durable store layout, миграция/активация и внешний streaming IO остаются отдельными контрактами T07/T13.

## 1. Три разных наблюдения

Для одного и того же значения различаются:

1. `Value(T,v)` — типизированное семантическое значение.
2. `Wire(CodecRev,RegistryBinding,T,v)` — точная последовательность bytes.
3. `Work(ProfileRev,Operation,Inputs,Budget,CancelSchedule)` — исход и трасса вычисления.

Равенство values не доказывает равенство wire между schema/codec revisions. Равенство wire не доказывает равную work trace другого алгоритма. Граф dependencies и проверка изменений обязаны сохранять эти domains раздельно.

Codec принимает только `Persistable(T)` по всему типу. Structural predicate учитывает все variants и не зависит от actual value. Phantom type arguments остаются в exact type descriptor, даже если не влияют на payload layout. Type descriptor функции — метаданные; сериализация code pointer, captured environment, capability или host handle не разрешена.

## 2. Контекст и заголовок

Домен: fixed codec/profile revision, exact immutable schema registry, ground root type T и finite valid value данного T. Исследовательский wire начинается с пяти octets `42 44 30 37 01` (ASCII BD07 и binary version1), затем содержит 32-byte digest registry и 32-byte digest exact root type. После 69-byte header идёт один positional payload.

Digests вычисляются по exact canonical JSON metadata, полностью заданному API: UTF-8, sort_keys=True, separators=(',',':'), ensure_ascii=False, allow_nan=False. Массивы и declaration order сохраняются. Host default `repr`, randomized hash и произвольные JSON settings недопустимы. В metadata нет floats, NaN или function objects. Это лишь carrier метаданных, не общий JSON value codec bagaev.

Registry binding R07 включает **весь** supplied registry. Добавление даже неиспользуемой декларации меняет binding. Это консервативный выбор опыта, а не доказательство минимальных schema dependencies. Для чтения старого wire требуется exact archived registry; нельзя заменить его новым registry с похожим root name. Будущий codec с reachable schema closure требует отдельной revision, алгоритма closure и проверки совместимости.

Root type binding различает nominal entity/revision и ordered type arguments. Поэтому одинаковые восемь payload octets у ArticleId и PersonId не делают wire взаимозаменяемым. Совпавший header hash не является подписью или проверкой целостности payload: корректно сформированные другие данные в том же контексте остаются другими допустимыми данными. Authenticity/transport checksum — отдельный внешний протокол.

## 3. Payload grammar

Тип известен из ожидаемого T и exact registry. Сам payload не содержит свободно выбираемых self-description tags.

| Тип | Точное представление |
| --- | --- |
| Unit | ноль octets |
| Bool | один octet: 00=false, 01=true; остальные отвергаются |
| Int64 | ровно 8 octets, signed two's-complement, big-endian |
| String | unsigned big-endian U32 длина UTF-8 в octets, затем столько octets строгого UTF-8 |
| Bytes | U32 число octets, затем исходные octets |
| Seq<T> | U32 число элементов, затем payload каждого T по порядку |
| Map<K,V> | U32 число пар, затем payload K и V каждой пары в **semantic Key order** |
| Nominal record | payload каждого instantiated field по declaration order; field names не повторяются в wire |
| Nominal sum | U32 declaration tag ordinal, затем payload этого instantiated variant |
| Option / Result | sum layout согласно exact builtin tag table API данной revision |

U32 wire width не обещает, что исполнитель выделит любую указанную длину. Перед allocation/traversal действуют явно заявленные physical guards. Поддерживаемый semantic domain и implementation limits разделены.

Примеры **payload**, без 69-byte контекстного заголовка:

| Значение | Payload hex |
| --- | --- |
| Int64(0) | 0000000000000000 |
| Int64(-1) | ffffffffffffffff |
| Int64(7) | 0000000000000007 |
| String(U+00E9) | 00000002c3a9 |
| String(U+0065 U+0301) | 0000000365cc81 |
| Bytes([195,169]) | 00000002c3a9 |
| Seq<Int64>([]) | 00000000 |

String(U+00E9) и Bytes([195,169]) имеют одинаковый payload, но разные type binding в header. Никакого вывода типа по payload нет. Signed numeric order также не определяется лексикографическим сравнением этих bytes.

## 4. Encoder как work machine

Encoder использует explicit stack задач: node/type visit, component continuation, length/header bytes, scalar prepass и emission. Один work transition посещает ограниченный node/leaf либо читает/пишет один octet по exact registry правил.

1. Подготовка проверяет тип, ready value, bounds и immutable bindings. Это ограниченная prelaunch validation; её работа не списывается с runtime budget и не объявляется отменяемой runtime schedule.
2. Runtime формирует header через charged work rules, сохраняя byte cursor.
3. При входе в composite value сохраняет continuation для следующего child; не разворачивает всё поддерево eager.
4. Для String предварительно считает UTF-8 octet length по одному scalar (1–4 octets), затем пишет length и преобразует скаляры в bounded chunks. Полная строка не кодируется в скрытом host call до первого runtime шага.
5. Каждый emitted octet проходит output-size guard до записи. Accumulator внутренний и не опубликован.
6. После последнего payload byte завершение имеет определённую rule boundary. Только полный результат становится Returned(Bytes).

Стратегия prepass допустима, поскольку String immutable. Она имеет собственные charged rules; нельзя забыть эту стоимость при оптимизации или повторном запуске. Уже известные bounded metadata могут читаться константной работой, но семантическая нормализация/сортировка не прячется в prelaunch cache.

## 5. Decoder и canonicality

Decoder получает expected T и raw Bytes, а не доверенный tagged value. Он проверяет header и затем исполняет typed parse tasks по explicit stack.

- Каждый read octet имеет work boundary. EOF, invalid Bool/tag/UTF8/context получают exact typed error, когда соответствующее правило обнаруживает нарушение.
- Length field читается полностью перед проверкой его domain/physical limit. Огромное значение не используется как аргумент allocation до проверки.
- Composite child декодируется в private slot; его parent не публикуется частично.
- Для каждого Map key после первого применяется resumable `compare_K(previous,current)`. Требуется строго Less. Equal означает duplicate, Greater — noncanonical order. Сортировать wire на входе или принимать последнюю запись запрещено.
- После root payload обязателен exact EOF. Trailing bytes отвергаются; valid prefix не является успешно декодированным whole value.
- String decoder не добавляет/удаляет BOM, не нормализует и не заменяет malformed UTF-8.

Неполный/неканонический wire и несовпавший context возвращают обычный `Err` типа decoder. Physical limit даёт ImplementationStop; budget/cancel имеют собственные terminal outcomes. Если одновременно возможны несколько дефектов, приоритет задаёт последовательность parser/work transitions, а не произвольный поиск всех ошибок. Конкретные codes и byte offsets принадлежат exact API.

## 6. Проверяемые законы и предпосылки

При фиксированных RegistryBinding/T/CodecRev, valid Persistable value и достаточных semantic/physical ресурсах:

```text
decode(T, encode(T,v)) = Ok(v)
```

Для принятого **канонического полного** wire b в тех же условиях:

```text
decode(T,b) = Ok(v)  implies  encode(T,v) = b
```

Второй закон запрещает permissive acceptance альтернативных integer widths, normalized strings, reordered/duplicate maps и ignored suffix. Принятые границы важны: успешный encode должен выдавать Bytes, допустимые как decode operand данного профиля; output/input size caps согласуются. Нельзя заявлять закон для пары API, где encoder возвращает wire, который decoder отвергает только по несовместимому собственному лимиту.

### Headroom для точного DATA roundtrip

Одинакового MAX_BYTES недостаточно: decode request содержит registry/type metadata, а результат оборачивается в Result.Ok. Поэтому encode использует дополнительный admissibility guard:

1. Payload value резервирует один node/depth level для Ok wrapper: максимум4095 data nodes и depth31 при общих4096/32. Derived type `Result<T,DataError>` также должен помещаться в type-depth/node limits.
2. Prepare строит **метаданные** prospective decode request с теми же labels/registry/type и пустым Bytes operand. Body не кодируется. Exact raw-node count (по API) определяет оставшееся место для byte list.
3. Runtime encoder ограничивает wire величиной `min(MAX_BYTES, MAX_RAW_NODES - raw_nodes(empty_decode_envelope))`; каждый octet добавляет один raw scalar node. Guard действует до публикации лишнего byte.
4. Decoder самостоятельно проверяет все обычные guards. Достаточный semantic budget остаётся отдельной предпосылкой; max request budget DATA не заимствуется из frozen CORE.

Эта политика осознанно сужает admissible encoder input по физическому профилю, но не объявляет граничное значение ошибочным типом V1. Exact diagnostics/threshold accounting фиксируются API. Новый policy должен иметь собственные boundary cases, включая Result wrapping и registry headroom.

Для Map permutation без duplicate изменение порядка готовых input pairs сохраняет resulting map и wire в fixed context, но может изменить request digest, work cost и trace. Для authorship Seq перестановка авторов меняет value; её запрещено маскировать сортировкой.

Законы задают цели conformance. Конечный report проверяет лишь перечисленные instances. Всеобщее injectivity/roundtrip доказательство и разные промышленно независимые targets здесь не предъявлены.

## 7. Источники и принятые различия

[Unicode 16.0 chapter3](https://www.unicode.org/versions/Unicode16.0.0/core-spec/chapter-3/) определяет scalar values и UTF-8 constraints; [RFC3629](https://www.rfc-editor.org/rfc/rfc3629) даёт совместимую byte grammar и требования отказа malformed forms. R07 выбирает строгий Result decoder вместо replacement-mode.

[RFC8949 §§4.2 и5.6](https://www.rfc-editor.org/rfc/rfc8949.html) полезен как первичный источник требований deterministic encoding и проблем duplicate map keys. BD07 не использует его wire grammar; в частности, map order здесь семантический типизированный, не CBOR bytewise encoding order. Цитирование RFC не является заявлением conformance.

## 8. Durable integration остаётся отдельной

Persistable и canonical bytes не обеспечивают atomic commit, schema activation, migration, event ordering или permission. Durable envelope должен дополнительно связать storage namespace, exact schema/codec references, domain identity/revision и integrity/authentication по своему контракту. Reader выбирает exact registered decoder; unknown revision не читается best-effort текущим типом.

Обновление schema требует явного migration plan и проверки новых value invariants. Хранение старого registry позволяет декодировать старую revision, но само по себе не переводит её в новую. Codec cursor — private состояние текущего job, не durable checkpoint protocol. Никакие bytes не отправляются во внешний stream по мере encoder steps; внешний streaming/partial-write recovery здесь не реализован.
