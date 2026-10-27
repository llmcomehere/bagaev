# PIPELINE-0.1 — контракт конвейера компилятора

**R21 · WORKING_DESIGN · 23 октября 2026.** Предмет — весь исходный T13-C01: вход, выход, ошибки и версии каждой стадии `parse / resolve / type / effect / lower / link / emit`. Это спецификация границ и алгоритмов композиции. Полная грамматика, wire IR, библиотека, FFI и доказательства оптимизаций сохраняют свои задачи T03–T06/T13-C03–C05. Отсутствующие точные контракты блокируют настоящий запуск, а не заменяются экспериментальным синтаксисом.

Реестр стадий: [stage-registry.json](../../registry/data/toolchain/pipeline-stage-registry.json). Форматы внешних записей: [schema](../metadata/pipeline.schema.json). Диагностика: [diagnostics.md](diagnostics.md). Кэш и обратная связь: [incremental-origin.md](incremental-origin.md). Сквозная проверка: [pipeline-route.md](pipeline-route.md).

## 1. Результат и границы доверия

Компиляция принимает immutable снимок исходников, exact lock, MeaningLock/Environment, ToolBuild, TargetProfile, реестр контрактов и явные compile limits. Она выдаёт проверенные промежуточные представления, диагностики и, при полном успехе, неизменяемый executable image. Она не выполняет программу, adapter, initializer, lifecycle hook, загрузку пакетов, приёмку исходника, публикацию или развёртывание.

Внутренние stage providers — исполняемые компоненты toolchain, прошедшие явную admission по текущей политике. Пакет программы не может зарегистрировать произвольный provider. Compile-time generation оформляется отдельным R20 BuildPlan с собственными входами/эффектами; созданные bytes фиксируются до подготовки следующего source snapshot. Здесь пользовательские macros, compiler plugins из packages и динамические schema hooks не исполняются: `UNSUPPORTED_FEATURE`. Это ограничение конвейера, а не скрытое выполнение host-кода.

Успех shape checker или совпадение hash означает только проверку формы/байтов. Семантическую корректность обеспечивает конкретный trusted stage implementation и обязательный независимый boundary checker там, где он объявлен. Их точные identities и область входят в StageContract. `PASS` от недоверенного caller не является stage evidence. Подпись сама по себе не доказывает истинность результата: допускается только exact producer/checker, область и lineage, разрешённые действующей политикой.

Первый target — эталонный интерпретатор канонического typed IR (D04, D65). Native/Wasm backend не становится поддержанным по одному имени target. Его contracts, ABI и observation-preservation evidence должны быть зарегистрированы отдельно. Язык промышленной реализации — Rust (D65).

## 2. Порядок identities без циклического hash

До compiler pipeline выполняется R20 подготовка:

`authored SourceBundle + PackageResolutionContract → Manifest/catalog → DependencyLock → PackageInterfaceClosure → final MeaningLock/Environment → SourceVersionBinding`.

Входы compiler фиксируются после этого. PipelinePlan не содержит результатов стадий, future artifact refs или собственного hash. MeaningLock содержит точные semantic contracts, но не output ссылающегося на него compiler. SourceBundle содержит только authored bytes/config/identity attachments; generated lock, binding, build result, receipt, executable и собственный inventory в него не входят.

R21 `ObjectRef={kind,format,codec,sha256,bytes}` продолжает R20 и проверяет outer exact bytes. Native semantic identity R19 вычисляется по соответствующему domain-separated codec отдельно. Нельзя заменить одно другим. Foreign payload сохраняется в исходном codec; recanonicalize JSON перед проверкой foreign hash запрещено.

Порядок после подготовки:

1. immutable PipelinePlan;
2. stage payload(s), затем OriginMap к этим payloads;
3. StageResult с точными inputs/outputs/map/read-set;
4. optional VerificationEvidence к уже существующему StageResult;
5. следующий stage;
6. ExecutableImage body, OriginMap/diagnostics sidecars;
7. PipelineResult; отдельный BuildResult и последующая acceptance/release evidence.

Payload не ссылается на свою SourceMap или StageResult. StageResult не включает evidence, хеширующее этот же StageResult. Отдельный evidence index может связать их впоследствии. Внутренний LocalNodeId — строковый ID в payload; полный адрес узла `(PayloadRef, LocalNodeId)` создаётся снаружи после hash. Это исключает `node.id` с hash собственного контейнера.

### 2.1 SourceBundle

`SOURCE-BUNDLE-0.1` — закрытый transport envelope: project identity ref, sorted file inventory и nullable identity-attachment ref. Каждый file имеет уникальные `file_id`, portable `path`, role `SOURCE|AUTHORED_CONFIG|ATTACHMENT`, media type и exact `content_ref`. Для SOURCE media type фиксирован `text/x-bagaev; charset=utf-8`; snapshot может сохранить и ошибочные authored bytes для диагностики; их корректность как source проверяется в PARSE строгим UTF-8 decoder без исправления, Unicode normalization и изменения переводов строк. Остальные roles не передаются parser без собственного semantic contract. Inventory использует BAG-TREE-1 правила path/case/ancestor collision R20. Сумма фактических длин и все content hashes проверяются до parse. Пустой bundle допустим как snapshot, но EMIT требует объявленный entrypoint.

`file_id` — source-local стабильная identity из authored T02 identity mapping, не имя файла и не номер от глобального счётчика. При отсутствии/противоречии обязательного mapping production resolve возвращает `INPUT_NOT_READY`/`IDENTITY_CONFLICT`. Копирование или переименование не назначает EntityId автоматически. Bundle может быть сформирован в staging из editor buffer без изменения accepted head; compare-and-capture должен получить согласованный набор exact buffers. Несогласованная capture возвращает `STALE_SOURCE_CAPTURE`.

Source text digest и семантический payload digest различны. Одинаковый смысл не делает равными source bytes, комментарии, права, историю принятия или source locations.

### 2.2 PipelinePlan и BuildPlan

PipelinePlan включает SourceBundleRef, SourceVersionBindingRef, MeaningLockRef, EnvironmentRef, DependencyLockRef, PackageInterfaceClosureRef, TargetProfileRef, CompilerBuildRef, exact семь StageContractRef, формат diagnostic protocol, compile limits и `mode=CHECK|EDITOR|EMIT`. Entry selector — exact EntityRef либо `null`; для EMIT обязателен. Tool build/platform/time/random/locale inputs pinned Environment/Toolchain и R20 build inventory, а не прочитаны из ambient environment.

Bindings сравниваются по actual decoded objects: SourceVersionBinding указывает именно на source/MeaningLock/Environment плана; Manifest lock указывает на тот же source/resolution contract; PackageInterfaceClosure выведен из exact lock; MeaningLock указывает на эту closure; TargetProfile и contracts совпадают с закреплёнными semantic dependencies. Null/missing production dependency не заполняется текущим default.

BuildRecipe, на который ссылается R20 Manifest, — **независимое pre-resolution определение** compiler invocation template/transport/выбора target, без PipelinePlanRef, LockRef, final MeaningLock, generated output или derived source binding. После resolution отдельная запись `CompileInvocation={recipe_ref, pipeline_plan_ref, invocation_contract_ref}` связывает exact template с конкретными входами; она не является тем BuildRecipe, который уже закреплён в Manifest. R20 BuildPlan.recipe_ref остаётся ссылкой на этот же pre-resolution BuildRecipe; input_inventory включает CompileInvocation, PipelinePlan и всю их transitive closure. Проверяющий adapter требует ровно один invocation заявленной роли и equality recipe/source/MeaningLock/lock/environment/target между фактическими records. PipelinePlan и CompileInvocation **не** ссылаются на BuildPlan. Порядок: `independent Recipe → Manifest → Lock → MeaningLock → PipelinePlan → CompileInvocation/InputInventory → BuildPlan → BuildObservations/PipelineResult`. BuildObservations после выполнения ссылается на PipelineResult. Положить Plan внутрь Manifest.recipe означало бы цикл `Manifest→Recipe→Plan→Lock→Manifest`; это запрещено. R20 schema не переписывается.

`CHECK` проходит parse/resolve/type/effect и выдаёт CHECKED, без lowered executable. `EDITOR` разрешает recovery syntax и независимые diagnostics, выдаёт EDITOR_PARTIAL или CHECKED; никогда executable. `EMIT` проходит все семь стадий. AcceptanceRef не обязателен для compile working source; release gate позже требует exact accepted source по R20. Изменение current head во время чтения не меняет snapshot плана; публикация результата как результата «текущего head» потребует отдельный CAS.

## 3. StageContract и единый алгоритм

StageContract фиксирует stage ID, semantic rule ref, input/output format contracts, provider implementation ref, checker ref, exact feature coverage, read roles, output validator, limits/work counter rules, failure contract, origin-map rule, diagnostic rules и invalidation policy. Все списки закрытые; extension kind без version admission отвергается. Число `0.1` — label; identity задаёт exact contract content. Один label с разными bytes — `FORMAT_IDENTITY_CONFLICT`.

Для стадии `S`:

```text
run_stage(plan, S, required_inputs):
  validate exact plan/context/limits and support for this operation
  for role in declared order:
    verify required ref kind/format/codec/size/hash/native identity
    decode with the explicitly bound contract; check full invariants
  verify predecessor lineage and identical source/meaning/lock/target subject
  reject recovery/poison/incomplete inputs unless S is EDITOR analysis
  derive read-set, work schedule and cache key from trusted contracts
  use a valid exact cached result only under CACHE-PIPE-0.1
  otherwise execute the admitted provider on private immutable inputs
  map failures by the closed result matrix; never catch-all as source error
  validate all output bytes, shape, semantic boundary invariants and origin map
  independently check prescribed relations (e.g. no unresolved link slots)
  freeze payloads and result, write through bounded staging
  atomically publish completed StageResult / cache entry; then report it
```

Запуск читает только exact inputs через instrumented resolver. Любое необъявленное чтение даёт `UNDECLARED_INPUT`. Полнота enforcement требует реального build adapter; запись read-set без enforcement — только DECLARED_ONLY evidence R20. Анализ не меняет inputs; выходы используют новые immutable objects. Parallel execution допустимо только по независимым modules/SCC; наблюдаемые diagnostics, traversal и work приводятся к указанному порядку. Параллельный completion order не влияет на выбранную первую ошибку.

StageResult содержит plan ref, stage/contract, status, exact role→input refs, role→output refs, diagnostic batch, read-set ref, origin map ref и `origin_output_role` когда они существуют, complete flag и logical compile work. `complete` не supplied proof, а проверяемое следствие status/output/invariants. У `OK` outputs исчерпывают обязательные роли. У `INVALID`, `INPUT_NOT_READY`, `UNSUPPORTED`, `LIMIT`, `CANCELED`, `INTERNAL_ERROR`, `UNTRUSTED` executable output отсутствует. Editor partial body может существовать только в typed output role `recovery_cst`/`editor_analysis` с explicit non-executable purpose.

### 3.1. Единственный основной origin output

Каждая стадия объявляет ровно один `primary_origin_output_role`: parse=`syntax_ir`, resolve=`resolved_ir`, type=`typed_ir`, effect=`effect_ir`, lower=`lowered_ir`, link=`linked_ir`, emit=`executable`. У successful StageResult `origin_output_role` равен этому registry value, а decoded OriginMap.output_payload_ref **точно** равен outputs[этот role]. Карта auxiliary table вместо основной программы не удовлетворяет gate. Map enumerates все node IDs основного payload через его exact decoder, даже если node не имеет source range.

Auxiliary outputs (type/effect/symbol/call tables, inventories, derivation/check metadata) не содержат независимо исполняемых bodies; они адресуют primary local nodes или independent input refs. Ссылки auxiliary→primary допустимы после создания primary bytes, обратная primary→этот auxiliary запрещена. Когда target должен ссылаться на независимую type table, table создаётся первой без primary back-reference; StageResult связывает оба. Source CST/token inventory сохраняют exact spans/bytes по собственному PARSE contract; parse OriginMap связывает SyntaxIR nodes с CST/source. Если новый auxiliary kind содержит executable/generated code nodes, старый one-primary profile его не допускает: нужен новый зарегистрированный map-set contract, а не потеря coverage. EDITOR_PARTIAL map, если задан, адресует ровно указанный recovery/editor output; ошибочный stage без partial output имеет origin_output_role=null и origin_map_ref=null.

## 4. Семь стадий

### P1 PARSE — bytes → lossless syntax

**Вход:** SourceBundle SOURCE bytes, GrammarContract (lexer/parser tables, disambiguation, parser algorithm revision, recovery table, literal rules), Edition/Unicode contract и source identity attachments. **Выход:** `LosslessCST`, `SyntaxIR` (ещё с source names), source ranges/token inventory, parse diagnostics. Payload formats: `LosslessCST`, `SyntaxIR` из exact T03 FormatContracts; transport binding `STAGE-RESULT-0.1`.

Алгоритм: проверить byte bounds/UTF-8; lexer идёт слева направо, отдаёт непересекающееся полное покрытие bytes, включая whitespace/comments; production grammar определяет token precedence и ambiguity. Deterministic parser применяет pinned grammar/table и consumption rules. Каждый source form обязан иметь известное syntax tag/rule. CST leaves покрывают bytes без пропуска/перестановки, concat leaves равен original file. Syntax projection извлекает semantic tokens/identity associations, сохраняя source-order children. Строки/числа не нормализуются через host defaults. Успешный parse исчерпал весь input, не содержит error/unknown/missing tokens и имеет одно разрешённое дерево. Эти свойства проверяет отдельный boundary traversal.

**Recovery:** допустим только EDITOR. Pinned recovery table задаёт insert/delete/synchronize actions и стабильный priority; каждая action потребляет input либо recovery budget. Missing token — zero-width anchor, original bad bytes сохраняются. Неизвестная grammar/recovery table не угадывается: INPUT_NOT_READY. Recovery CST не получает SyntaxIR с purpose executable; отдельный later full parse обязателен. Ошибки UTF8_ERROR, TOKEN_ERROR, SYNTAX_ERROR, AMBIGUOUS_PARSE, UNKNOWN_FORM, PARSE_LIMIT. Не найденный grammar contract отличается от ошибочного source. Наличие parser tables в описании — зависимость T03, а не уже существующий V1 parser.

### P2 RESOLVE — names → identities

**Вход:** complete SyntaxIR, source identity mapping, exact lock/import map/interface closure, NameResolutionContract и module/export table. **Выход:** `ResolvedIR`, complete ScopeIndex, resolved import/export mapping, lookup dependency set. Ни одного unresolved executable name.

Алгоритм: inventory declarations по stable lexical order; проверить duplicate IDs/names по namespace rules; imports разрешить только через R20 LockBinding без текущего registry. Build lexical scopes: parameters и outer captures доступны явно; ordinary let binder появляется после initializer; recursive group устанавливает все свои function IDs/signatures до обхода bodies. Module/block forward references допускаются только в declared scope table. Для каждого occurrence обходить ближайший scope к outer и затем только явно импортированные namespaces; при множественности в одном allowed namespace — AMBIGUOUS_NAME, без выбора по порядку загрузки. Qualified reference фиксирует exact namespace/entity, private export — VISIBILITY_ERROR. Wildcard/overload policy без pinned rule — UNSUPPORTED_FEATURE, не предположение о «ближайшем» совпадении.

Результат lookup содержит **все просмотренные ScopeInventory refs**, включая scopes без найденного имени; отсутствие имени — зависимость от полного inventory. Проверить SCC declaration graph для forward edges; разрешённый cycle должен целиком принадлежать одному explicit recursive group по TYPES-0.1. Package cycles уже отвергнуты R20; recursion функций не исключается. Resolved form хранит BinderId/EntityRef, не только spelling. Boundary checker повторно проверяет reachability, identity uniqueness, lexical dominance и equality import map. Errors: UNBOUND_NAME, AMBIGUOUS_NAME, DUPLICATE_BINDING, IDENTITY_CONFLICT, VISIBILITY_ERROR, RECURSIVE_GROUP_REQUIRED, IMPORT_NOT_LOCKED, INTERFACE_MISMATCH, RESOLVE_LIMIT.

### P3 TYPE — resolved forms → typed forms

**Вход:** ResolvedIR, exact Type/Primitive/Error registries, nominal package identities, T04 type algorithm и all declared signatures/effect bounds. **Выход:** `TypedIR`, TypeTable, generic instantiation records, declared latent effect bounds и direct-call graph. All branches/functions проверены, inference holes/skolems/metas не выходят в complete result.

Алгоритм соответствует pinned TYPES-0.1: validate nominal/type parameter arity и well-formedness; explicit rank-1 schemes; no implicit let-generalization; recursively check/synthesize expressions; constraints унифицируются детерминированно с occurs check, scoped rigid sets и exact latent effect sets; expected result распространяется до проверки call arguments; let initializer finalized до binding. Recursive group использует один rigid vector и explicit signatures, рекурсивные type args не меняются. Nominal constructors сравниваются по exact TypeEntityRef, Bool не приводится к Int64. После каждого required finalization нормализовать substitutions/aliases и проверить отсутствие unresolved metas, unavailable rigid IDs, unsatisfied predicates и hidden forall. Exported signature замкнута. All branch types проверяются даже при literal condition.

Граница со следующей стадией: typing проверяет function types **по объявленным** latent bounds; effects refinement не меняет типы/overload решения назад. Это предотвращает цикл `type→effect→type`. Отдельный fixed point P4 проверяет actual⊆declared и может выдать более точное summary только как evidence, без implicit subtype. UNKNOWN predicates/unsupported recursive nominal rules не принимаются как success. Errors: TYPE_MISMATCH, TYPE_ARITY, OCCURS_CHECK, SKOLEM_ESCAPE, AMBIGUOUS_INSTANTIATION, UNSATISFIED_PREDICATE, POLYMORPHIC_RECURSION, UNRESOLVED_TYPE, TYPE_LIMIT. Полный T04 registry всё ещё необходим для каждого V1 form; отсутствие — INPUT_NOT_READY.

### P4 EFFECT — verified types → effect closure

**Вход:** TypedIR, declared effect bounds, exact finite effect domain/join/subset rules, adapter signatures/error sets и static call graph. **Выход:** `EffectCheckedIR`, EffectSummaryTable, CapabilityRequirementTable и closed obligations table. Summary не является capability token или доказательством текущего права.

Алгоритм: для каждого function вычислить direct effects тела без выполнения; создание lambda не вносит effects её body, но captures/creation expressions учитываются. Direct named call добавляет summary target; indirect call — declared latent bound callee, без optimistic guess. Для If/Match консервативно объединить все статически допустимые branches; short circuit меняет runtime order, не разрешает скрыть непроверенную ветку. Builtin/adapter effect и failure set берётся только из exact registry; неизвестный adapter не pure.

Построить call SCC и condensation DAG. Для каждого SCC в порядке зависимостей начать с direct sets; упорядоченная worklist добавляет union callee sets до неподвижной точки. Domain конечен: не более `|functions| × |effect_atoms|` strict set additions; work charges включают каждое examined edge/atom, поэтому циклический повтор без growth не бесплатен. Если actual set выходит за declared bound — EFFECT_BOUND_EXCEEDED. Неявно расширять bound нельзя. Аналогично выводятся обязательные capability classes/error variants через их finite registries. Dynamic resources и current authority остаются runtime checks; невозможность статического доказательства и missing adapter contract не превращаются в разрешение. Статические контрактные утверждения с отдельным verifier могут остаться NOT_VERIFIED, если policy не требует их для этого mode; required gate unknown блокирует emit: REQUIRED_OBLIGATION_UNVERIFIED.

Boundary checker повторяет monotone equations и проверяет least solution/declared bounds, не только любой большой fixed point. Errors: EFFECT_BOUND_EXCEEDED, UNKNOWN_EFFECT, ADAPTER_SIGNATURE_MISMATCH, REQUIRED_OBLIGATION_UNVERIFIED, EFFECT_LIMIT. Исчерпание work — LIMIT, а не доказательство отсутствия эффектов.

### P5 LOWER — checked forms → target core

**Вход:** EffectCheckedIR, exact lowering rules, target/core form registry, evaluation/error/cost/cancel contracts и origin rule. **Выход:** `LoweredIR`, explicit instantiation/capture/import slots, `LoweringDerivation` и OriginMap. Первый target не применяет optimizer.

Для каждого node в исходном evaluation order выбрать **ровно одну** rule по tag/type/profile. Нулевая или неоднозначная применимость даёт LOWERING_RULE_MISSING/AMBIGUOUS_LOWERING. Generated local IDs выводятся из `(input LocalNodeId, rule ID, output slot path)` в namespace этого output; collisions проверяются, hash/ID не заменяет EntityId. Строгие args/record fields/map entries обрабатываются слева направо до canonical storage sort; guard не перемещается через effect. Short-circuit lowering использует conditional, не strict call; result propagation создаёт explicit branch в окружающем result context. Closure captures связываются по resolved IDs, hygienic temp не захватывает user binding.

Rule содержит output skeleton, exact input→output mapping, evaluation order, type/effect invariant и **logical runtime charge/cancel boundary attribution**. Reference lowering может определять исходную semantics, если это явно pinned в MeaningLock. Когда source semantics уже задана независимо, требуется доказательство preservation указанного observation domain. Если cost rule/derivation checker отсутствует — INPUT_NOT_READY; равенства final value недостаточно. Оптимизация/TCO/inlining/constant folding не включается «по умолчанию». Она требует отдельного admitted transform, проверенного относительно T06; T13-C03 остаётся самостоятельным критерием.

Boundary checker воспроизводит deterministic rule instantiation по исходному checked IR, сравнивает output canonical payload, проверяет все links/types/charges/maps. Этот structural checker не заменяет доказательство правильности самих lowering rules. Errors: LOWERING_RULE_MISSING, AMBIGUOUS_LOWERING, HYGIENE_VIOLATION, OBSERVATION_CONTRACT_MISMATCH, COST_RULE_MISSING, LOWERING_INVALID, LOWER_LIMIT.

### P6 LINK — exact module instances → closed program

**Вход:** LoweredIR каждого selected module, locked exact dependency module bodies/interfaces, target/portable ABI contract и entry selector. **Выход:** `LinkedIR`, SymbolTable, complete import/export/adapter requirements и closed dependency inventory.

Алгоритм: deterministic topological package order по R20; внутри module deterministic EntityRef/instantiation key. Build export key `(package instance identity, module EntityRef, symbol EntityRef, type args)`; duplicates при разных bodies отвергаются. Каждый import slot содержит exact expected package instance/symbol/type/effect/ABI/version, находит **ровно один** matching export; проверить equality либо explicitly admitted directed compatibility claim для этой операции. Тот же spelling/layout не объединяет nominal IDs. Generic specialization keyed exact definition + normalized type args + target/semantic contract; repeated key требует same body/ref, polymorphic recursion уже запрещена. Instantiation work/graph bounded; first target может хранить explicit generic IR вместо monomorphization, если это target ABI.

Host import — declarative AdapterRequirement, а не загруженная native function и не issued capability. Неизвестная FFI memory/effect/error contract — INPUT_NOT_READY/UNSUPPORTED, не пропуск. First reference target не запускает linker constructors/init code. Любой обязательный module initializer должен быть lowered в explicit runtime entry sequence с объявленными effects/order; unsupported initialization mechanism отвергается. Boundary checker independently пересчитывает exact imports/exports/slots, closure, entry arity/result/effect contract. Unused functions всё ещё прошли статическую проверку; dead-strip без preservation contract выключен. Errors: MISSING_SYMBOL, DUPLICATE_SYMBOL, ABI_MISMATCH, NOMINAL_IDENTITY_MISMATCH, GENERIC_INSTANCE_CONFLICT, ENTRYPOINT_MISMATCH, LINK_CLOSURE_GAP, LINK_LIMIT.

### P7 EMIT — closed program → executable bytes

**Вход:** LinkedIR, pinned executable encoder, target/runtime ABI, full source/meaning/lock/environment bindings, output naming/inventory rules. **Выход:** exact ExecutableImage, sorted output inventory, debug/origin sidecars, EmitValidation. Поле `executable` обозначает purpose, не permission to run.

Алгоритм: проверенный immutable linked payload сериализуется prescribed encoder в staging; memory addresses, wall time, random seed, host path/locale не добавляются. Header содержит exact target/ABI/MeaningLock/Lock/Environment and entry; sections имеют explicit lengths/kinds/contracts, checked arithmetic, no overlap/gaps except prescribed padding. Unknown mandatory section rejected. Отдельный loader заново читает фактические emitted bytes под тем же contract, проверяет section bounds/hash/native identities, reconstructs normalized linked representation и сравнивает с input; serialized shape без semantic equality недостаточна. Debug symbols остаются exact source-bound sidecars, не перемешиваются с opcode order.

Для первого interpreter target image хранит canonically encoded linked typed IR; native machine emitter требует своего executable contract и checker. Изменение codec не объявляется совместимым по label. После проверки actual output lengths/hashes получить immutable refs, только затем complete Emit result. Filesystem crash до atomic result publication не создаёт успешный output; orphan staging quarantined. Errors: ENCODE_ERROR, EXECUTABLE_DECODE_ERROR, ROUNDTRIP_MISMATCH, SECTION_BOUNDS, TARGET_UNSUPPORTED, EMIT_LIMIT, OUTPUT_CAPACITY. BuildResult дополнительно различает declared inputs и реально enforced INPUT_CLOSED; emit PASS не объявляет битовую воспроизводимость независимой сборки.

## 5. Ошибки, остановка и диагностическая определённость

Closed pipeline statuses: `CHECKED`, `EMITTED`, `EDITOR_PARTIAL`, `INVALID`, `INPUT_NOT_READY`, `UNSUPPORTED`, `LIMIT`, `CANCELED`, `INTERNAL_ERROR`, `UNTRUSTED`. `STALE_PUBLICATION` — результат отдельного compare-and-publish, а не переименование compiler success. При INVALID полный diagnostic summary фиксирует `has_source_error=true` и `source_error_lower_bound≥1`; конкретная ERROR entry может не уместиться в truncatable list; при INPUT_NOT_READY exact missing refs/contract IDs; при UNSUPPORTED known unsupported features/operation; при LIMIT конкретный counter+cap; при INTERNAL_ERROR pinned implementation issue/reproducer ref без ложного обвинения source. Hash corruption/mismatched kind/codecs даёт INPUT_HASH_MISMATCH/INPUT_KIND_MISMATCH в diagnostic code и pipeline UNTRUSTED, не SYNTAX_ERROR.

Hash-correct authored source с UTF8_ERROR/TOKEN_ERROR/SYNTAX_ERROR/AMBIGUOUS_PARSE/UNKNOWN_FORM под известной grammar даёт INVALID/SOURCE. Snapshot capture сохраняет bytes и не объявляет их syntactically valid. Malformed metadata/envelope/hash относится к UNTRUSTED/INPUT; отсутствующий grammar contract — INPUT_NOT_READY, известная неподдержанная grammar/feature — UNSUPPORTED. UNKNOWN_FORM здесь означает недопустимую конструкцию внутри уже выбранной известной grammar, а syntactically valid, но unsupported declared feature имеет UNSUPPORTED_FEATURE.

Нормативная классификация задаётся парой **phase+blame**, а не одним коротким code: [failure-matrix.json](../../registry/data/toolchain/pipeline-failure-matrix.json). CHECKER_REJECTED нового provider output, LOWERING_INVALID, нарушенная generated closure, ROUNDTRIP_MISMATCH или неверный generated source map — INTERNAL_ERROR/TOOL. Тот же дефект в supplied untrusted artifact — UNTRUSTED/INPUT. Корректно декодированный source, нарушающий известное type/effect rule, — INVALID/SOURCE. Отсутствующий exact checker/contract/input — INPUT_NOT_READY/INPUT. Неизвестный required obligation outcome — INPUT_NOT_READY; доказанный конфликт source contract — INVALID. Implementation exception/незаявленное чтение/unknown provider enum — INTERNAL_ERROR. Нельзя обвинить пользователя в compiler bug только потому, что проверка не прошла.

Common codes действуют на каждой стадии: INPUT_HASH_MISMATCH, INPUT_KIND_MISMATCH, INPUT_FORMAT_UNSUPPORTED, FORMAT_IDENTITY_CONFLICT, SUBJECT_MISMATCH, PREDECESSOR_INCOMPLETE, UNKNOWN_SEMANTIC_FIELD, UNDECLARED_INPUT, CHECKER_UNAVAILABLE, CHECKER_REJECTED, PROVIDER_FAULT, CAPACITY_EXCEEDED, CANCEL_REQUESTED. Stage-specific codes перечислены выше и в registry; upstream nested diagnostic сохраняет exact error contract+code+payload, не схлопывается в строку. Unknown error enum от provider = PROVIDER_PROTOCOL_ERROR/INTERNAL_ERROR.

Порядок gate: outer request decode/size → supported contract/context → exact dependencies → predecessor/subject checks → stage traversal → output validation → publication. В пределах stage first deterministic error задают pinned traversal и source-order tie breaks. Для multi-error EDITOR results сортируются по `[stage rank, file inventory rank, byte start, byte end, rule priority, code, stable local ordinal]`; schedule не меняет batch. Diagnostics cap не превращает наличие ошибок в success: batch содержит `truncated=true`, exact lower-bound count и reason. Полный исчерпывающий список без bytes не обещается.

Compile work budget отдельный от runtime semantic budget. Charge правила фиксированы StageContract: examined tokens/nodes/edges/type constraints/effect atoms/generated forms/encoded bytes. `StageResult.work_units` — intrinsic deterministic provider work для данного exact предмета, сохраняемое и при cache hit. Фактически выполненную текущим вызовом работу хранит отдельный `CompileAttempt`: disjoint counters preflight/cache/provider/check/publication, их checked U64 sum и exact CompileInvocation/Plan refs. Ранее засвидетельствованный intrinsic work не записывается как заново выполненный. RECOMPUTE_CHECK начисляет и recompute, и validation work; ADMITTED_PRODUCER_CHECK начисляет actual lookup/evidence/loading work. Все текущие counters входят в общий budget этого attempt, независимо от наличия historical success. Каждый charge preflight checked U64, overflow даёт LIMIT до commit. Physical OOM/time/process crash — IMPLEMENTATION_STOP/INTERNAL_ERROR, не логический отрицательный вывод о программе. Cancellation checked перед каждым declared compile work boundary, перед cache lookup, после cache verification и до result publication; hit не пропускает эти gates; уже опубликованный immutable stage остаётся historical, но новый PipelineResult получает CANCELED и не выдаёт ExecutableImage. Cancellation после committed EMITTED результата не отзывает bytes; отдельное current publication/launch admission решает последующие действия.

Default limits: ≤4096 source files, source total64MiB, file16MiB, ≤1,000,000 syntax/IR nodes, depth≤1024 с iterative traversal, ≤65536 declarations, ≤32768 imports, ≤256 effect atoms, ≤1,000,000 generated instantiations, ≤100,000,000 compile work units, emitted inventory≤256 files и total256MiB, diagnostics≤4096 entries/4MiB; refs/metadata body≤16MiB, request transport≤32MiB. Small deployments may lower bounds; поднятие меняет exact LimitsContract. Read sets/origin maps имеют отдельные limits, ≤4,000,000 edges и64MiB each; output map overflow не отбрасывает map silently. Resource guarantees реализации требуют отдельной проверки memory/IO; эти bounds ограничивают контракт, не доказывают использование памяти Python/host.

## 6. Композиция, loading и атомарность

Ни одна стадия не может объявить более позднюю успешно пройденной. PipelineResult проверяет точную непрерывную последовательность требуемых стадий, stage contract identities, одинаковый plan subject, каждую actual output→next input ref и complete flag. CHECKED требует P1–P4; EMITTED — P1–P7 плюс loader check; EDITOR_PARTIAL не повышается автоматически при отсутствии diagnostics. Для результата, остановленного до P1, completed_stages пуст; для отказа в Pk хранится successful prefix и отдельно failed_stage_result_ref. Duplicate/переставленные/пропущенные стадии и чужой plan отвергаются.

Atomic publication хранит complete PipelineResult с compare-and-set ожидаемого working source binding **и generation**, если caller хочет установить current compiler view. Same source after A→B→A не проходит старый generation guard. Недостаточная capacity/authority/stale base оставляет previous pointer и receipt unchanged; immutable completed output остаётся доступным по ref. R16 operation key/semantic digest governs mutating publication; repeated lookup имеет current read gate. Pure compile вычисление не выдаёт key или право publish/deploy.

Runtime loader заново проверяет actual ExecutableImage, target/runtime support, artifact/source/MeaningLock/Environment/Lock bindings, exact entry contract и required effect classes. Он не выполняет unknown opcode и не подставляет новую stdlib. Compiler PASS не выдаёт текущую capability: launch и каждый host dispatch проверяют current authority по runtime contract. Executable из untrusted cache нельзя запустить по одному валидному content hash. Accepted status, release policy, trust revocation и execution admission сохраняют самостоятельные проверки R16–R20.

## 7. Независимый ожидаемый результат и границы готовности

Для каждой стадии существуют три уровня проверки: shape/refs (R21 metadata probes), semantic boundary/finite model (ограниченный независимый опыт), полная real source→IR→reference execution route (обязательная, в этой итерации NOT_RUN). R21 не складывает их числа как «тесты всего языка». Модель может использовать иной закрытый research codec и меньшую grammar; их результаты не заполняют отсутствующие T03 inputs.

Stage contract готов к реализации, когда разработчик может перечислить required roles, exact versions/checkers, порядок действий, failure mapping, output invariants и способ сравнения с независимым ожидаемым результатом. Production release дополнительно требует реальные upstream contracts/decoders, полный V1 corpus, реальные compiler/runtime/storage adapters и принятие. Окончательная стадия T13-C01 определяется независимым whole-scope review; зависимости не считаются выполненными по наличию этого документа.
