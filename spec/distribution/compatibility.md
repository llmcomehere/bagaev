# VERSION-BINDING-0.1 — версии, совместимость и смысл программы

**R19 · WORKING_DESIGN.** Основные исходные критерии: T18-C01 — «Каждый формат и протокол имеет версию и правило несовместимости»; T18-C02 — «Обновление инструмента не меняет молча смысл существующей программы». Это проект общего контракта V1, а не заявление о готовой совместимости реальных выпусков.

R19 дополняет R16/R17/R18. Полные байты R15 недоступны; новые правила необходимо сверить с актуальным сводом перед включением. Компактная основа не расширяется. Модель COMPAT-FINITE-0.1 проверяет ограниченный предмет и не заменяет полный реестр форматов, реальный compiler или migration runtime.

## 1. Обязательное разделение

Одно число версии не отвечает сразу на все вопросы о совместимости. Различаются:

| Идентичность | Что закрепляет |
| --- | --- |
| ToolBuildRef | Exact compiler/runtime/CLI binary и его dependency closure |
| FormatContractRef | Вид артефакта, wire/schema/semantic revisions, required features и правила чтения/записи |
| MeaningLockRef | Полный набор правил, определяющих смысл данного проекта |
| EnvironmentRef | Immutable среда R17: инструменты, packages, target/ABI и platform profile |
| ProjectBindingRef | Конкретные source heads, MeaningLock, EnvironmentRef, state format map и generation |
| CompatibilityClaimRef | Направленное утверждение о конкретной операции и области значений |
| MigrationPlanRef | Явное намерение перейти между exact bindings по заданному алгоритму |
| VerificationMethodRef | Точный checker, observation domain, assumptions и правила evidence |
| SessionBindingRef | Зафиксированный результат согласования wire operation/semantic revisions между endpoints |

VersionLabel — только удобное имя. Даже одинаковые MAJOR.MINOR.PATCH не разрешают исполнение или запись. Два артефакта с тем же label и разными bytes дают VERSION_IDENTITY_CONFLICT. Изменение содержимого опубликованного exact ref запрещено; новая редакция получает новую identity. Alias latest может участвовать в поиске кандидатов до фиксации lock, но не при запуске, replay или миграции.

Обновление host default tools меняет только install generation R17. Existing ProjectBinding остаётся прежним. ToolBuild может поддерживать несколько старых MeaningLocks; он обязан выбирать явно закреплённый. Неизвестный старый профиль нельзя заменить наиболее близким новым.

## 2. Универсальная привязка формата

FormatContract — неизменяемый описатель со следующими обязательными полями:

~~~text
FormatContract = {
  family_id, kind_id, format_label,
  wire_contract_ref, schema_contract_ref, semantic_contract_ref,
  canonicalization_ref, reference_extractor_ref, invariant_checker_ref,
  required_feature_contracts, extension_policy_ref,
  operation_domains, limits_ref, error_contract_ref,
  lifecycle_policy_ref
}
~~~

Refs — content identities точных контрактов, а не свободно меняющиеся URLs. Semantic contract необходим и для «только метаданных»: он определяет, какие поля действительно инертны. Отсутствующее определение не заменяется null или обещанием реализовать позже для production. FormatContract body не содержит compatibility claim refs: claim ссылается на уже готовые contract bodies, а отдельный registry/support index — на contracts и claims. Это исключает цикл content hashes Contract→Claim→Contract.

ArtifactEnvelope содержит envelope revision, family/kind, FormatContractRef, PayloadRef, exact dependency roots и declared features. Payload хранит native bytes своего формата; R19 не переопределяет BD07, JSON или source text одним codec. ProducerBuildRef можно добавить для provenance, но он не подменяет trust policy. Object envelope отделён от signatures/evidence sidecars, чтобы не хешировать собственное доказательство.

Вложенный объект со своей семантикой несёт свой exact contract ref либо наследует его по формально указанному enclosing schema. Наследование по произвольному текущему global default запрещено. Reader обязан установить binding до разбора semantic payload; decoder неизвестной версии не вызывается через format sniffing.

### 2.1. Что входит в MeaningLock

MeaningLock связывает grammar/edition и name resolution, type and value rules, primitive/error table, evaluation order, effects/adapters, budget/cancellation rules, scheduler observation contract, source→IR lowering, target/ABI assumptions, package resolution and public interfaces, locale/normalization и declared external input contracts. Каждое поле задаёт exact ref либо типизированное NOT_APPLICABLE с проверяемым основанием.

У результата важен не только scalar return. Например, изменение количества semantic steps может изменить исход при прежнем budget; изменение точки видимости cancellation может изменить наличие эффекта до остановки. Поэтому такие правила входят в MeaningLock, если они наблюдаемы выбранным V1 profile. R07 уже различает value, wire и work trace; R19 сохраняет это разделение.

Каждая source version, включая working и accepted heads, несёт собственную SourceVersionBinding = (SourceRef, MeaningLockRef, EnvironmentRef). ProjectBinding содержит активную working binding и отдельную принятую binding; исторический accepted head не наследует новый working default. При смене grammar/semantics старый head остаётся читаемым только под своим контрактом. Новый source candidate получает собственное принятие по правилам проекта; миграция хранения не присваивает его автоматически.

MeaningLock не содержит нынешних прав пользователя или secret bytes. Он определяет требуемый capability/effect contract; действующее право выдаёт текущий host. Отзыв права может запретить выполнение закреплённой программы, но не переписывает её MeaningLock.

## 3. Полный реестр семейств V1

Ниже — обязательный registry coverage, а не перечень уже выпущенных production decoders. Машинный реестр: [format-registry.json](../../registry/data/distribution/compatibility-format-registry.json). Каждый сохраняемый или передаваемый artifact kind должен принадлежать ровно одному семейству и иметь отдельную запись FormatContract.

| ID | Семейство и обязательные подвиды | Особая граница несовместимости |
| --- | --- | --- |
| F01 | Source text, module/edition declaration, source attachments | Grammar/name resolution/encoding; новые keywords не меняют старый исходник без edition migration |
| F02 | Lossless CST, source map, formatter/edit patch | Сохранность всех bytes, comments, spans и entity bindings; parse success не даёт право разрушить unknown syntax |
| F03 | Typed IR, executable image, lowering/optimizer metadata | Opcode/type/effect/cost rules и target ABI; неизвестная форма не выполняется приблизительно |
| F04 | Type/schema registry, values, codec wire | Nominal identity/type arguments/order/presence; same layout не означает same type |
| F05 | Package manifest, exported API/ABI, dependency graph | Exact interface/effect contracts и dependency closure; совместимость одной функции не разрешает весь пакет |
| F06 | Release descriptor, environment/toolchain lock, target profile | Exact build/closure/platform; tool default не меняет проект |
| F07 | Project configuration, declared input manifest, execution options | Defaults, feature flags, locale/time/random contracts; missing field не получает новый default без правила |
| F08 | Canonical relation graph, extraction/query profiles, reverse index/cache | Смысл edges и version endpoints; derived cache rebuild отдельно от canonical migration |
| F09 | Requirements/specification records, authored proposals, acceptance requests | Смысл требования и область принятия; форматирование не переутверждает спецификацию |
| F10 | Evidence, claims, observations, verification/acceptance receipts | Subject/method/domain/assumptions; historical PASS не переносится по имени версии |
| F11 | WorkState, obligation inventory, pending changes | Полный состав долгов и причины блокировок; неизвестный статус не считается terminal |
| F12 | Job checkpoint, continuation, scheduler/budget/cancel state | Runtime ABI, continuation validity, spent budget и observable schedule |
| F13 | Agent/tool command wire, session negotiation, diagnostics/query cursors | Wire revision и operation semantics; retry сохраняет прежнее значение intent |
| F14 | Idempotency keys, command receipts, effect ledger, remote adapter records | Namespace/generation/digest rules и UNKNOWN; смена decoder не делает старый key новым |
| F15 | Journal events, checkpoints, authority/reservation/control records | Exact reducers и current epoch; неизвестный event не пропускается |
| F16 | Installation database, project identity registry, launch/pin/GC records | Монотонные IDs/generations, pin lifecycle и actual writer guards |
| F17 | RecoverySet, capture/participant certificates, seals, recovery receipts | Полнота15 roles R18, exact cut/ancestry и текущие полномочия |
| F18 | Format/feature registries, compatibility claims, migration plans/certificates | Замкнутая metacontract bootstrap и запрет самоназначения trust/compatibility |

Новые подвиды не скрываются внутри универсального blob. Сборка release inventory извлекает форматы из storage writers, protocol methods, CLI machine outputs, persisted caches, package artifacts и adapters. Для каждого writer и reader указывается exact kind/contract/operation. Незарегистрированный вид — REGISTRY_COVERAGE_GAP, блокирующий release gate. Pure ephemeral implementation values, которые не сохраняются/не пересылаются и не входят в наблюдаемое поведение, могут быть вне реестра по явному классификационному правилу.

Наличие family row не доказывает готовность соответствующего decoder. Для известных research contracts сохранены конкретные baseline refs; unavailable source/IR/protocol releases отмечены INPUT_NOT_READY. В published V1 обязательный registry не может содержать unresolved refs, PendingSpecification или непроверенную совместимость.

## 4. Направленная матрица по операциям

CompatibilityQuery = (reader ToolBuildRef, input FormatContractRef, operation, requested target/output contract, requested domain, required observation/relation scope, exact features, optional exact claim ref, current policy). Target задан exact ref либо типизированным NOT_APPLICABLE с основанием; для REWRITE/EXECUTE/RESUME/REUSE_EVIDENCE его нельзя угадать из текущего default reader. Направление — из конкретного input в конкретный reader/operation/target, а не симметричная пара номеров.

| Операция | Что разрешает положительный результат |
| --- | --- |
| COPY_OPAQUE | Побайтно сохранить/передать объект по внешнему container contract без трактовки payload |
| INSPECT_METADATA | Прочитать поддержанный envelope и явно ограниченные метаданные; unknown payload остаётся unknown |
| DECODE_VALUE | Получить значение по exact old schema/codec с выполненными invariants |
| REWRITE | Записать новое представление, сохранив всё требуемое по declared preservation contract |
| EXECUTE | Выполнить программу с закреплённым MeaningLock и допустимыми target/effect/budget contracts |
| RESUME | Продолжить точное job/state history с runtime checkpoint, obligations и authority guards |
| VERIFY_EVIDENCE | Проверить historical claim в его исходном domain/method/assumptions |
| REUSE_EVIDENCE | Использовать результат для другого exact subject только с отдельным transfer basis |

COPY_OPAQUE не сообщает, что содержимое осмысленно или пригодно для выполнения. DECODE_VALUE не разрешает REWRITE, если writer потеряет поля. EXECUTE не разрешает RESUME сохранённого stack. VERIFY_EVIDENCE не означает REUSE_EVIDENCE.

Результат query один из:

- ALLOW_EXACT: exact contract/operation supported, все required features и guards удовлетворены.
- ALLOW_SCOPED: есть проверенное CompatibilityClaim для точного domain и операции; returned constraints обязательны.
- INSPECTION_ONLY: доступен только перечисленный metadata projection.
- MIGRATION_REQUIRED: прежний artifact не изменяется; указан допустимый plan kind/transform candidate.
- INPUT_NOT_READY: нет необходимых exact bytes/profile/decoder/evidence.
- REFUSE: известная несовместимость, неизвестная критическая feature, потеря данных, превышение limits или policy denial.

Результат включает input/reader/target refs, operation, domain, observation/relation scope, evidence basis, capabilities, denied capabilities и exact missing/unsupported items. Нельзя вернуть общий compatible=true и заставить caller угадывать разрешённые действия. Registry запрещает duplicate support entries для одинакового input/reader/operation/target/domain/scope. При overlapping claims resolver использует явно запрошенный claim; если без него остаётся несколько допустимых оснований, возвращает AMBIGUOUS_COMPATIBILITY_BASIS, а не выбирает первое по порядку загрузки. Domain inclusion проверяет declared checker, не эвристика по имени.

### 4.1. Базовая матрица правил

| Вход и возможности reader | Чтение | Запись/исполнение/продолжение |
| --- | --- | --- |
| Exact contract, exact features, проверенная реализация | По заявленной операции | Только по отдельным поддержанным операциям и текущим guards |
| Тот же label, иной contract digest | VERSION_IDENTITY_CONFLICT | Отказ |
| Известен wire/schema, отличается semantic contract | Допустим exact old decode, если он поддержан | MIGRATION_REQUIRED либо отдельный scoped compatibility claim |
| Новая required feature неизвестна reader | Envelope inspection при разрешении | Refuse; feature не игнорируется |
| Неизвестное инертное annotation в разрешённом extension bag | Разрешён declared projection | Только побайтное сохранение bag; потеря блокирует migration |
| Старый artifact, новый tool поддерживает old MeaningLock | Exact old read | Old semantics явно выбирается; новый default не применяется |
| Новый artifact, старый reader не поддерживает kind/revision | Opaque copy/metadata, если envelope известен | Refuse; обратное направление не выводится из forward claim |
| Поддержанный формат, но payload вне domain/limits reader | Точный ограниченный отказ | Ни truncation, ни новый default |
| Certificate покрывает value, но не budget/effects | Только value claim | Не разрешает full executable preservation |
| Нужный decoder отсутствует/отозван policy | INPUT_NOT_READY/policy refusal | Не подставлять другой decoder по label |

Прямое ALLOW_SCOPED(A→B) не даёт B→A. Наличие A→B и B→C не даёт автоматического A→C: требуется проверка composition — области входов/выходов, observation domains, точных transforms и накопленных losses. Для V1 миграция выбирает явно перечисленный path; не ищет «любую достижимую последнюю версию» и не исполняет произвольные конвертеры.

## 5. Unknown fields, defaults и сохранность информации

Required semantic features выводятся trusted decoder/extractor из artifact и MeaningLock; незнакомая extension не может объявить себя некритической собственным critical=false. Класс extension определяется заранее доверенным ExtensionPolicy.

V1 предоставляет только два класса:

1. SEMANTIC_REQUIRED: reader должен понимать exact feature contract для операции. Неизвестность блокирует interpret/rewrite/execute/resume.
2. INERT_PRESERVE: ограниченный namespace annotations, чей trusted contract доказывает отсутствие влияния на semantic interpretation. Bytes сохраняются точно и входят в content identity. Их потеря — ошибка rewrite, даже если result value совпадает.

Обычные unknown fields вне разрешённого extension bag отвергаются. Inert payload не исполняется как hook, schema или format registry. Исходный текст с неизвестной grammar можно копировать целиком, но нельзя выдавать новый formatter output за lossless. Сохранение комментариев может быть отдельным observation requirement пользователя; инертность для runtime не означает разрешение их удалить.

Default имеет version binding. В миграции явно различаются отсутствующее поле, null, пустое значение и значение default. Transform обязан задать mapping и предусловия. «Новое поле optional» недостаточно, если новый reader использует иной default при execution или admission.

R19 V1 не определяет lossy export. Кандидат с утратой защищаемой информации отвергается; permission не превращает потерю в preserving migration. Будущий export с потерями требует отдельного зарегистрированного operation contract, точного перечня потерь и нового artifact purpose; он не может служить project activation или authority continuation. Нельзя отбросить unknown obligation/status/key/effect record даже по общему разрешению «убрать лишние поля».

## 6. Алгоритм проверки совместимости

~~~text
resolve(query, trusted_registry, host_context):
    validate bounded envelope and requested operation
    check current permission for requested view/action
    resolve exact format/feature/reader contract refs under current trust policy
    if family/kind not registered: REFUSE(REGISTRY_COVERAGE_GAP)
    if same label resolves to different bytes: REFUSE(VERSION_IDENTITY_CONFLICT)
    derive required features/dependencies from exact trusted contracts
    if requested operation only copies opaque bytes:
        check container/size/destination contract
        return ALLOW_EXACT(capability=COPY_OPAQUE, interpretation=UNKNOWN)
    if unsupported semantic feature:
        return metadata-only result if explicitly requested; otherwise REFUSE
    require exact decoder bytes and decoder implementation conformance
    decode privately under declared limits; check canonical form and invariants
    select exact input/reader/operation/target/domain/scope support entry
    or one explicit CompatibilityClaim; refuse unresolved ambiguity
    verify domain predicate, observation coverage, certificate binding and assumptions
    verify operation-specific dependencies and current host guards
    return bounded per-operation capability and exact evidence refs
~~~

Отказ не меняет project lock и не выполняет migration. Для inspection caller должен запросить её явно либо принять отдельный частичный результат; requested EXECUTE не получает successful INSPECTION_ONLY под тем же success type. Хеширование/скачивание/проверка signatures не запускает произвольный decoder из входного payload.

Resolver использует точный immutable registry snapshot, которому доверяет host. Обновление registry не меняет прежние claims; создаётся новый registry ref. При отзыве доверия historical artifact остаётся историческим фактом, но действующее использование может быть запрещено текущей policy.

## 7. Что считается сохранением смысла

PreservationContract задаёт два exact semantic domains, mapping входов/идентичностей, projection наблюдений, relation между состояниями, effects/authority constraints, ресурсные предпосылки и независимый checker. Наблюдения включают declared values/errors, termination/implementation-stop distinctions, effect order and targets, cancellation/budget boundaries и public relation queries там, где профиль делает их видимыми.

В contract явно выбирается equality, observational equivalence или направленное refinement; они не взаимозаменяемы. Начальная и конечная границы доказательства названы exact representation/semantic refs: доказательство compiler pass между двумя AST не покрывает автоматически parser, linking, host adapters, semantic budget, cancellation или relation/evidence graph. Не включённое в observation domain свойство остаётся непроверенным; это ограничение нельзя скрыть за общим словом «эквивалентно».

Для pure value re-encoding может быть достаточно:

~~~text
decode_old(old_bytes, old_type_registry) = v
transform(v) = v_new
value_relation(v, v_new)
decode_new(new_bytes, new_type_registry) = v_new
all protected obligations/identities/metadata preserved
~~~

Для arbitrary executable rewrite одного равенства тестовых outputs недостаточно. V1 не обещает универсально решать эквивалентность программ. Разрешаются ограниченные зарегистрированные transformations с явно проверяемыми условиями и evidence точной области. Если основание не покрывает нужный claim, результат UNKNOWN/REQUIRES_SEMANTIC_CHANGE, а не «скорее всего сохраняет смысл».

Intentional semantic change — допустимый отдельный путь: новый MeaningLock/source candidate, явное описание изменения, новые verification/acceptance obligations. Его нельзя пометить PRESERVING, даже если владелец разрешил изменение. Разрешение изменить поведение и доказательство, что оно не изменилось, — разные факты.

### 7.1. Исправление ошибки реализации

Tool bug fix может сохранять специфицированный MeaningLock и менять ошибочное фактическое поведение прежнего build. Поэтому:

- Новый build получает новую identity и собственное conformance evidence.
- Existing pinned build не заменяется через host default update.
- Явный environment repin фиксирует changed implementation, affected claims и required revalidation.
- Исторические результаты старого build не переписываются; известный дефект может сделать их основание неприменимым к текущей acceptance.
- Если меняется сам заявленный semantic contract, нужна новая semantic revision и отдельное решение о миграции/изменении.
- Срочный отзыв опасного build может запретить его запуск по current policy, сохраняя возможность разрешённой инспекции. Он не даёт права тихо выполнить другой build.

Это различает обещание не менять смысл молча и нереалистичное обещание, что исправления ошибок никогда не меняют наблюдаемое поведение.

## 8. Protocol sessions и повтор команд разных версий

Session handshake передаёт protocol contract refs, operation semantic revisions, required features, target project/MeaningLock, allowed domains и current authorization context. Сервер выбирает конкретный общий контракт согласно явной policy и возвращает SessionBinding с полным transcript digest. Client проверяет, что выбранный контракт удовлетворяет его required capabilities; silent downgrade запрещён.

Handshake authentication/integrity обеспечивается transport/authority adapter, а не самим совпадением transcript hash. Нет общего supported contract — VERSION_NEGOTIATION_FAILED. Сессия не меняет ProjectBinding. Пропавшая во время reconnect capability даёт отказ, а не урезанный смысл прежней команды.

CommandIntent связывает original operation semantic revision, canonical request digest по тому revision, project/environment/domain и стабильный key. При повторе:

1. Проверить текущие права чтения исторического результата.
2. Разрешить original version binding и lookup key/digest.
3. Вернуть exact historical receipt либо версионированный wrapper с явным original payload ref; конвертация wrapper не меняет historical result.
4. Для нового действия отдельно проверить текущие write rights/epoch/operation support.

Нельзя декодировать старый request новым codec, получить иной digest и признать key незанятым. Если old decoder больше недоступен, безопасный отказ сохраняет key/history. Tombstones и minimal original-version bindings должны жить не меньше R16 admission guarantees. Поле «версии больше не поддерживаем» не разрешает повторно использовать старое пространство ключей.

Errors/diagnostics и cursor formats тоже зарегистрированы. Неизвестный error code сохраняется как unknown original diagnostic; его нельзя преобразовать в успех или ordinary domain value. Live cursor привязан к ServiceEpoch/query contract; migration меняет query semantics — cursor invalidation и новое разрешённое чтение.

## 9. Lifecycle, retirement и поставка

Каждая contract revision имеет lifecycle state DRAFT, SUPPORTED, DEPRECATED, READ_ONLY, RETIRED. Эти состояния обозначают policy использования, а не изменение bytes. Registry записывает effective policy revision и точные операции, остающиеся допустимыми.

Deprecation не переписывает project locks. Removal execution support должен иметь заранее объявленный refusal path и доступный способ экспорта/инспекции по policy. Для RETIRED необходимо проверить отсутствие live pins, pending jobs, UNKNOWN/effect/key obligations и retained evidence/recovery dependencies либо сохранить старые codecs в declared archival service. Отсутствие старого decoder не доказывает отсутствие старых объектов.

GC использует graph reachability по exact refs и R16/R17 pins, не возраст label. Исторические receipts можно хранить без полного старого executable при наличии минимального достаточного original codec и bindings; executor retention и receipt readability — разные обязательства. Архивный decoder недоступен — ARCHIVE_UNAVAILABLE, а не новый пустой объект.

Release gate объединяет:
1. Закрытый registry coverage всех readers/writers и protocol methods.
2. Exact support matrix для заявленных операций/platforms.
3. Независимые positive/negative compatibility cases, включая оба направления.
4. Подписанный/доверенный release provenance отдельно от content hashes.
5. Обновлённые compatibility/lifecycle policies без молчаливого изменения existing locks.
6. Реальный migration/recovery route для поддержанных переходов.

Номер версии, published schema или работающий finite demo не выполняют эти gates сами.

## 10. Форматы новых R19 метаданных и границы проверки

R19 descriptor bodies используют RecoveryJSON-1 из R18: strict UTF-8, без duplicate keys/floats, canonical key sorting, decimal-string counters, exact domains и bounded metadata. Body хешируется с domain separation; certificates ссылаются на body, который не ссылается на собственный certificate. Registry root собирается из contract bodies и explicit claim IDs; каждый claim body ссылается на конкретные contract refs, но не на registry root, содержащий его самого.

Для восьми metadata kinds в прилагаемой schema формула identity точна: `SHA256(UTF8("bagaev.r19." + kind + ".0.1") || 0x00 || RecoveryJSON1(body))`, lower-case hex. `kind` — case-sensitive discriminator FormatContract, ArtifactEnvelope, MeaningLock, CompatibilityClaim, MigrationPlan, CandidateBody, PreservationCertificate или PreparedEnvelope; весь body, включая schema/kind, входит в canonical payload. Body не содержит собственной identity. Прочие referenced kinds используют свои отдельные exact hash/codec contracts; при отсутствии таких контрактов production resolver возвращает INPUT_NOT_READY, не применяет формулу по догадке. Finite model имеет отдельный toy digest contract и не является реализацией этих production metadata codecs.

Profile bootstrap: минимальный RegistryEnvelope decoder и root trust задаются установкой R17. Registry не разрешает произвольный новый root decoder. Новый metacontract требует отдельного install/trust update и backward reader route.

Основные limits проекта: descriptor ≤1 MiB; registry snapshot ≤8 MiB; не более4096 kinds, 4096 claims и256 explicit migration steps; reference depth≤64; не более1 048 576 reachable objects на конкретный plan; decimal counters uint64 без wrap. Более широкий profile — отдельная revision. Cancellation не публикует частично преобразованный проект. Output admissibility проверяется до публикации, а не только на входе.

[Schema метаданных](compatibility.schema.json) проверяет только форму. Exact content references, semantic closure, uint64 range, checker validity, current permissions и universal preservation из JSON Schema не следуют.

Полный переход проекта определён в [migration.md](migration.md). Будущая проверка всех заявленных форматов и операций — [compatibility-route.md](compatibility-route.md). Все production integration cases до фактического выполнения имеют NOT_RUN. Исторические research format IDs в registry не объявляют эти форматы принятым V1 release.
