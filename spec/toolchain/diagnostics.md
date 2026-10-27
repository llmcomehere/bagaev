# DIAGNOSTIC-PIPE-0.1 — ошибки, координаты и исправления

**R21 · WORKING_DESIGN.** Контракт входа/выхода compiler stages, не полный CLI/editor protocol T14. Машинные записи описаны [schema](../metadata/pipeline.schema.json). Нормативная ссылка — exact FormatContractRef, а label нужен человеку.

## 1. Subject и структура

DiagnosticBatch содержит PipelinePlanRef, SourceBundleRef, MeaningLockRef, stage, exact DiagnosticContractRef, ordered diagnostics, `has_source_error`, `source_error_lower_bound`, `truncated`, `total_lower_bound` и `truncation_reason`. Непрерывно вычисляемый error summary расположен в ограниченном обязательном envelope **вне** обрезаемого списка. Для complete batch lower bound равен actual count, source error count точен, reason=null. Для truncated batch total lower bound больше выданного count; reason=ENTRY_LIMIT или BYTE_LIMIT; source_error_lower_bound не меньше числа выданных SOURCE/ERROR, не больше total lower bound и положителен ровно при has_source_error. При INVALID has_source_error=true даже если buffer не вместил ни одной error entry или выданы только warnings; status не выводится заново из обрезанного списка. Невозможность записать минимальный envelope даёт отдельный transport/capacity failure без публикации success.

Diagnostic record содержит stable-in-this-batch ID и уникальный deterministic ordinal, code/error-contract ref, severity ERROR|WARNING|INFO, category SOURCE|INPUT|TOOL|LIMIT|CANCEL|POLICY, primary anchor, related anchors, structured params. FixCandidate создаётся после immutable batch и ссылается на exact batch+diagnostic IDs; обратного embedded fix_ref в Diagnostic нет. User-visible message строится из pinned template/locale; message text не является machine code и не используется для логики. `params` — закрытый список `{name,value_type,value}`: TEXT, ID, U64 или ObjectRef; type и shape должны совпадать, decimal counters не float/bool. Поля не допускают исполняемых snippets/callbacks.

Anchor — ровно один tagged вариант:

- SOURCE: SourceBundleRef, FileId, exact ContentRef, raw byte start/end и range kind;
- ARTIFACT: PayloadRef и LocalNodeId; optional source map разрешается отдельным запросом;
- PROJECT: exact PipelinePlanRef и reason, когда source location действительно отсутствует.

Source ranges могут ссылаться на dependency source только из exact input closure; batch обязан сохранять собственный root subject и отличать related foreign source. Нельзя приписать ошибку текущему открытом файлу по одному path. Если actual bytes источника unavailable, возвращается ARTIFACT/PROJECT anchor с missing ref, а не угаданная строка.

## 2. Координаты

Единица core diagnostic — **байтовое смещение в точном исходном файле**, interval `[start,end)`, 0-based. `0≤start≤end≤content.bytes`. Для обычного UTF8_TEXT_RANGE границы лежат между Unicode scalars и не разрезают CRLF пару, если указан line-range view. Core byte span допускает CRLF bytes отдельно, когда lexer rule явно адресует delimiter; line/column presentation не меняет actual span. Для ошибки декодирования `RAW_BYTE_RANGE` может покрывать ill-formed UTF-8 без попытки исправления. Zero-width вставка допускается на границе bytes и помечается recovery=true; она не утверждает наличие token.

Canonical core не хранит line/column как вторую authority. Adapter строит line table из тех же bytes: LF завершает строку; CRLF — один перевод строки; одиночный CR сохраняется как scalar, если upstream lexical contract не требует иного. CRLF handling для display и lexer раздельно pinned. Для valid UTF-8 line/column adapter явно объявляет negotiated position encoding UTF8_BYTES, UTF16_CODE_UNITS либо UNICODE_SCALARS. Длина scalar вне BMP =4 UTF-8 bytes, 2 UTF-16 units, 1 scalar. Grapheme clusters, tab width и display cells не подменяют эти единицы. Нельзя представить ill-formed UTF-8 как корректную Unicode position; editor получает byte-oriented diagnostic или явный unsupported-location marker.

Алгоритм преобразования: verify ContentRef; проверить byte interval; найти line start двоичным поиском в immutable line table; decode bytes от line start до offset строго; подсчитать выбранные единицы; вернуть position вместе с exact source identity. Offset внутри multi-byte scalar при UTF8_TEXT_RANGE — RANGE_INVALID, не округление. При CRLF boundary, для которого целевой editor position не имеет точного представления, core span остаётся первичным и adapter возвращает non-exact display annotation. Обратное преобразование принимает только representable boundaries и выполняет roundtrip.

Editor buffer version — дополнительная ephemeral session identity. Отсутствие совпадения buffer version **или** raw content ref означает STALE_DIAGNOSTIC: old diagnostic может показываться в historical view с точной пометкой, но не как current annotation. Одинаковая длина и совпадающий path недостаточны. Source A→B→A: bytes могут снова совпасть, однако прежний fix с ожидаемой generation не становится действующим автоматически.

## 3. Детерминизм и recovery

Stage traversal фиксирован контрактом. Batch order: stage rank → file inventory rank → byte start → byte end → rule priority → code → stable local ordinal. Для ARTIFACT/PROJECT anchors используются отдельные fixed ranks после source locations. Related locations имеют own sorted key; диагностические причинные edges адресуют IDs внутри того же batch и образуют DAG. Duplicate diagnostic IDs, cycle, missing cause или unknown code без upstream ErrorContractRef — protocol error.

При truncation первоначально выбирается bounded sorted prefix под entry/byte caps. Затем из него детерминированно удаляются все records, чей cause_id отсутствует в выбранном subset; проход повторяется до неподвижной точки. Новые entries вместо удалённых не добавляются. Порядок оставшихся сохраняется; cause_ids не стираются и не переписываются. Эта процедура конечна (каждая итерация удаляет хотя бы один record) и оставляет причинно замкнутый DAG, возможно пустой. Полные discovered total/source-error lower bounds собираются **до** отсечения и не уменьшаются; envelope по-прежнему объясняет наличие omitted errors. Проверка полного и выбранного DAG выполняется iterative color-stack traversal с bounded edges, без зависимости от call-stack host. Неизвестный cause ещё до truncation или causal cycle — TOOL protocol failure, а не обычное сокращение.

Recovery parser никогда не теряет original bytes. Source errors и missing tokens остаются в LosslessCST; любые downstream editor summaries имеют `purpose=EDITOR_ONLY`, `complete=false`, valid region coverage и dependency scope. Ошибки в одной функции не разрешают compiler выдать другой entry как executable в EMIT без полной проверки объявленного compilation unit. User может создать новый явный unit/plan с меньшей областью, но не выдавать partial result старого unit за полный.

Если pipeline остановился на missing contract/input, диагностика перечисляет точные missing refs и downstream blocked stages. Не рисуется type-error там, где parser/grammar не был доступен. Tool failure не превращается в SOURCE category. Truncation сохраняет наличие ошибки и отдельную причину; неизвестное общее число — только lower bound, не точный count.

## 4. FixCandidate

Fix — proposal с exact DiagnosticBatchRef и diagnostic IDs внутри этого batch, exact base SourceBundleRef, SourceVersionBindingRef, expected working generation, ordered edits и rationale diagnostic IDs. Для каждого edit: FileId, old ContentRef, byte range, expected range hash, replacement bytes ref. Empty replacement допустима. Все ranges проверяются на UTF8_TEXT boundaries для text edits; raw-byte repair — отдельная explicit repair operation. Edits одного файла не перекрываются; несколько вставок в ту же границу требуют заданного порядка либо отвергаются как ambiguous. Replacement bytes строго декодируются под pinned source encoding.

Порядок content identities: immutable DiagnosticBatch (без future fix refs) → FixCandidate → derived lookup index по `(DiagnosticBatchRef, diagnostic_id)`. Candidate обязан ссылаться только на существующие IDs указанного batch и на его exact source/MeaningLock base; связывание с current generation выполняется отдельно при proposal/apply. Индекс исправлений не входит в hash batch или candidate и может быть перестроен из известных FixCandidate objects. Поэтому нет цикла `Batch→Fix→Batch`, а два разных batch с одинаковым D1 не смешиваются. Просмотр предложений требует текущего read access; наличие связанного fix не означает его применимость.

Применение:

1. Проверить current edit authority и точный base binding/generation.
2. Сверить actual file bytes и каждый expected slice; path не служит identity.
3. Из immutable old bytes построить новое содержимое, применяя disjoint edits по убыванию start; одна insertion boundary имеет однозначный порядок.
4. Создать новый SourceBundle и полный parse/check candidate; diagnostics старого bundle не переносятся по смещениям.
5. Принимать/устанавливать working change только существующей T10/T12 guarded operation с R16 key/CAS. До commit edits являются immutable candidate, accepted head не меняется.

Автоматическая правка из semantic warning без проверенного mapping запрещена. Generated/inlined/merged node может иметь несколько origins; tool предлагает выбор или отдельный source-level transform, не угадывает owner. Неприменимый fix даёт STALE_FIX/AMBIGUOUS_ORIGIN; это нормальный отказ, не основание принудительно обновить base.

## 5. Независимые ожидаемые случаи

- Insert ASCII comment перед ошибкой: новый ContentRef и смещение, old batch STALE.
- Кириллица + non-BMP scalar перед ошибкой: raw-byte, UTF16 и scalar координаты различаются предсказуемо.
- Неверный UTF-8: RAW_BYTE_RANGE, никакой replacement character в сохранённых source bytes.
- CRLF и zero-width missing token: точный interval без удаления line ending.
- Два parallel modules с ошибками: тот же deterministic sorted batch при reverse completion order.
- Recovery syntax в false branch: EDITOR_PARTIAL допустим; EMIT обязан отказать.
- Exhausted diagnostic buffer: INVALID+truncated, не OK+empty diagnostics.
- A→B→A перед fix commit: old expected generation отказывает.

Эти реальные source/editor integration classes входят в route R21 и пока NOT_RUN. Finite модель использует JSON node paths вместо полного UTF8 source-map protocol и не подтверждает эти случаи автоматически.
