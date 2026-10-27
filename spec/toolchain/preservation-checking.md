# PRESERVE-CHECK-0.1 · проверка и применение

Проект R22. Семантические основы: [preservation.md](preservation.md), разрешённые замены: [optimization-rules.md](optimization-rules.md). Форматная схема в [metadata](../metadata/preservation.md) является дополнительным входным барьером, не выполняет этот semantic protocol.

## 1. Объекты и ациклические ссылки

Порядок построения:

    exact source/context/registry
      → OptimizationRequest
      → independently materialized CandidateProgram
      → PreservationCertificate(source + candidate + rules + observations)
      → VerificationReceipt(certificate + exact checker result)
      → R21 StageResult outputs / BuildObservations output inventory

CandidateProgram содержит executable target form payload, original semantic region mappings и source subject. Он не включает будущий certificate/receipt hash. Certificate указывает на candidate и exact OutputMapSet через origin_map_set_ref, receipt — на certificate. Индекс candidate→receipts вычисляется отдельно. Ни SourceBundle, ни Manifest recipe не получают ссылку на будущий оптимизированный результат.

Candidate target forms ссылаются только на raw checkpoint/reconstruction payloads. Эти payloads содержат source subject/origin/region и parameterized recipes, но не candidate_ir_ref, enclosing CheckpointPlan, OutputMapSet, certificate или receipt. CheckpointPlan — построенная ПОСЛЕ candidate metadata, связывающая raw payload с exact candidate_ir_ref. DeoptDescriptor также является последующей metadata; executable хранит raw state recipe, не future descriptor. Иначе candidate→CheckpointPlan→candidate создал бы content cycle. Origin maps и map set создаются после обоих IR; сами IR не содержат обратных ссылок на будущие map objects.

BuildPlan.input_inventory закрепляется до выполнения собственной сборки. Он включает доступное к этому моменту замыкание source/contracts/catalog/checker/config; существующий до сборки OptimizationRequest включается прямо, а stage-local Request после reference lowering выводится из этих inputs и фиксируется как derived output. Candidate/certificate/receipt, впервые созданные в этой сборке, также являются outputs и входят в BuildObservations/output inventory; задним числом добавлять их в собственные inputs запрещено. Другая последующая сборка может потреблять уже существующий verified candidate как exact declared input, но использует новый BuildPlan с самостоятельной предварительно закреплённой input inventory.

ObjectRef закрепляет exact outer bytes/size/media/schema; semantic identity исходных контрактов сохраняется отдельно. Same byte hash не доказывает соответствия source→candidate.

Восемь metadata kinds:

| Kind | Обязательный смысл |
| --- | --- |
| ObservationContract | Полный набор измерений и точные equality/resource/environment contracts |
| OptimizationRequest | SourceSubject, origin_ir, input_ir, optional checked parent, context/target/registries/mode/limits; целиком закреплён до работы |
| RewriteStep | Rule/version, exact before/after region, occurrence/path, local evidence |
| CheckpointPlan | Source/candidate region, order/count, exact plan payload и reconstruction |
| PreservationCertificate | Request, candidate, chain, exact observations, scopes и coverage |
| VerificationReceipt | Проверенная certificate identity, checker identity, outcome/limits/coverage |
| DeoptDescriptor | Exact target checkpoint → exact source state recipe с прежними run counters |
| OutputMapSet | Exact origin maps обоих code-bearing outputs нового P5 |

ObservationContract, Request и Certificate не содержат готового semantic PASS. Receipt имеет outcome VALID только после всей проверки. Его accepted=false: semantic checking не означает нормативную приёмку/activation.

## 2. Входная проверка

Decode по exact BAG-META-JSON-1/pinned schema: reject duplicate keys, unknown fields/tags/revisions, surrogate codepoints, nonexact integers, invalid relative object references. Ограничить bytes до разбора. Raw finite model использует свой API и не служит production codec.

Materialize все обязательные references из immutable verified store с byte/hash/size/schema checks. Отсутствие точных bytes или upstream contract → INPUT_NOT_READY. Проверить весь authored snapshot и subject closure: SourceBundle, SourceVersionBinding, MeaningLock, Environment, dependency closure, FormatContracts, TargetContract, Form/Primitive/ChargeRegistry, ObservationContract, RuleCatalog, checker admission и LimitsContract.

Foreign adapters не исполняются для «выяснения» типа/effect. Verify static IR всех ветвей/тел, exact code closure и source origins. Несоответствие authored source — INVALID_SOURCE; повреждённый immutable object — UNTRUSTED_INPUT. Compiler-created invalid candidate — INTERNAL_ERROR в текущей compilation attempt; supplied invalid candidate — INVALID_CERTIFICATE.

## 3. Проверка полного candidate

    validate_candidate(request, candidate, certificate):
      validate all input objects and exact acyclic bindings
      establish source WF and complete supported form coverage
      confirm observation dimensions equal required EXACT_BOUNDARIES
      validate parent chain if input_ir differs from origin_ir
      current = exact verified input_ir
      for supplied_step in certificate.steps:
        validate step index, path and before-region against current
        inspect exact named rule from admitted local catalog
        derive allowed replacement inside checker from source/current facts
        compare all candidate bytes/values/checkpoints/reconstruction
        check unchanged-context and source mapping constraints
        replace region and update exact current identity
      require exact current == final candidate, including auxiliary closures
      verify candidate target WF, origin coverage and closure of all code refs
      load certificate.origin_map_set_ref and check both actual payload maps
      check resource/cancellation/effect/environment relation everywhere
      emit VerificationReceipt with exact validated subjects

Source-to-current mapping не даёт step права менять иной subtree. У пустой chain candidate должен совпадать с exact input representation. Непустая цепочка должна содержать действительные changes; косметическое дублирование metadata не превращает REQUIRE_OPT в успех.

У пустой chain candidate_ir=input_ir; reference representation является частным случаем первой попытки. При input_ir≠origin_ir обязательна цепочка ранее проверенных сертификатов до origin_ir, без cycles и с общим SourceSubject/context/observation. Parent refs проверяются итеративно в том же shared checker budget и maximum chain length 4 096. Отсутствующий/невалидный parent не разрешает продолжить.

Входные REPLAY_REGION/SCALAR_SLOT/KNOWN_ARM допускаются только по exact target form registry и verified parent. Их original semantic regions и все checkpoint recipes перепроверяются. Последующий проход либо KEEP этого узла, либо заново выводит допустимое replacement из его original semantic subtree; generated physical form не притворяется ordinary source const/if. Parent folding flatten использует одну original schedule, без повторного списания child history. Initial compiler выполняет один проход; composition protocol нужен для явных последующих проверенных attempts, не включает автоматический бесконечный fixed-point optimizer.

Local evidence — исходные facts/recipes, а не boolean. Checker повторно вычисляет их из exact source. User-supplied equality projection, список «неважных» эффектов, summary с narrower use и signed PASS не заменяют проверку.

Все executable/reference-bearing вспомогательные outputs включены в closure; скрытое тело функции в metadata недопустимо. Origin map проверяется для actual primary candidate payload R21, не для удобной побочной таблицы.

## 4. Проверка checkpoint/reconstruction

1. Bound region принадлежит current original semantic tree и входит в candidate map ровно в указанном месте.
2. Source rule sequence выводится из admitted matcher/evaluator. Каждый checkpoint содержит successor state recipe; последний local checkpoint возвращает value в исходный BASE_K.
3. Plan count совпадает с payload, positions contiguous, нет пропущенной/дублированной строки. Для control flow sequence относится к статически известному closed region; dynamic branches используют branch contract, не один observed path.
4. NodeIds/occurrence templates и error source sites относятся к source; repeated calls получают разные occurrences.
5. Exact costs выводятся из ChargeRegistry; supplied totals сравниваются с checked sum, но одних totals недостаточно.
6. Reconstruction DAG имеет только разрешённые узлы, exact types и live slots; все anchors имеют допустимый lifetime. Проверяется итеративным topo traversal.
7. Первая граница отображает source entry, каждая следующая — именно successor предыдущего transition. Нельзя предъявить хороший список charges и чужое конечное значение.
8. Final candidate runtime обязан исполнять проверенные target forms через допущенный runtime implementation. Correct certificate не разрешает произвольному executable притвориться этим runtime.

Runtime dispatch содержит единственную authority для logical counters/event publication. Native backend может физически группировать чтение recipes только если сохраняет поштучное наблюдение всех возможных stop boundaries. В initial target сгруппированного пропуска границ нет.

OutputMapSet.primary_role=lowered_ir; его lowered_ir payload равен candidate_ir, reference_lowered_ir payload равен invariant origin_ir. Каждая actual map.output_ref равна своему payload, source anchors принадлежат exact SourceSubject; coverage проверяется по реально декодированным двум IR. Schema-valid synthetically hashed map set не удовлетворяет этому semantic check.

## 5. Точная область результата проверки

VALID_RULE_REPLAY означает: для exact source/candidate/request соблюдён admitted rule contract. Его soundness условен относительно trusted contracts/checker/runtime. Все их identities входят в receipt.

FINITE_OBSERVATIONS означает только список реально исполненных (program,input,budget,cancel,environment) subjects с exact outcomes. Этот evidence kind запрещён как единственное основание production admission общего transformation claim.

COUNTEREXAMPLE содержит конкретный reproducible subject и первое различающееся поле/границу. UNKNOWN сообщает coverage frontier/неподдержанную форму/timeout; это не отсутствие ошибок и не universal equivalence.

Утверждение forall inputs требует либо проверенного общего rule proof в указанной логике, либо действительно исчерпывающего конечного домена, причём полнота перечисления доказывается отдельно. SMT timeout, ограниченный unroll и отсутствие найденного counterexample не превращаются в VALID_RULE_REPLAY.

## 6. Deopt алгоритм

    deopt(runtime_instance, descriptor):
      require currently published nonterminal logical boundary
      verify exact admitted candidate and descriptor/observation bindings
      read current immutable slots/frames and reconstruction recipe
      construct source state without executing source semantics or host calls
      verify type/control/env/K/code/capture consistency
      copy original runtime_instance, source snapshot, step position,
           every remaining budget, cancel state, journal cursor,
           operation identities and settlement knowledge
      install reference continuation atomically at the same boundary
      next advance starts with ordinary terminal/cancel/budget checks

Deopt marker может быть отдельной diagnostic implementation event; он не добавляет semantic step и не меняет program trace. После terminal descriptor не оживляет instance. В descriptor нет new_budget, new_operation_key, reset_journal или replacement input. Изменение фактических входов требует нового запуска с новой identity.

Если dispatcher уже отправил action, source reconstruction указывает на wait/reply/settlement state, а не на pre-dispatch. Атомарность переключения локальна конкретному RuntimeAdapter contract; migration между workers и recovery после process crash требуют отдельного протокола и не считаются выполненными R22.

## 7. Композиция и кэш

Проверяемая композиция C1/C2 требует exact C1.candidate_ir == C2.input_ir, одинаковых source_subject и origin_ir, одинаковых exact observation/resource/environment policy и совместимых state maps. Domain constraints должны быть выражены поддержанным решаемым языком этого профиля: exact equality refs, finite enum membership и integer intervals. Baseline rules имеют отсутствие input assumptions сверх well-typed V1 и target capacity; произвольная логическая formula не принимается.

Пересечение equal-ref constraints с конфликтом пусто, enum через intersection, intervals через max(lower)/min(upper); unknown constraint tag → UNSUPPORTED. Empty domain не даёт пользовательский общий PASS. Composition не удаляет scope ограничения и не выдаёт более широкое утверждение.

Initial ScopeConstraint имеет закрытые typed names. EXACT_REF.target_contract связывается с request.target_contract_ref; EXACT_REF.semantic_profile — с source_semantics_ref exact ObservationContract. ENUM.entrypoint обозначает объявленные entrypoints actual source/target closure. INTERVAL.input_items, value_bytes, stack_frames — только unsigned capacity dimensions одноимённого exact TargetCapacityContract с его unit/counting algorithm. Это не signed значения пользовательских Int64 и не runtime step budget. Имена, tag, unit и входное поле разрешаются через эти materialized contracts; неизвестное имя/несовпадающий тип или значение ref отвергаются.

Constraint domain certificate должен покрывать весь advertised admitted capacity/entrypoint domain request; произвольное сужение до успешно испытанных inputs запрещено. Baseline rules не используют дополнительных assumptions о значениях inputs. При composition пересечение capacity domains явно отображается в resulting claim и не объявляется сохранением более широкого request. Пустой/default constraints list означает тот же полный bound request domain, а не отсутствие ограничений. Ограничения physical capacity не позволяют исключить требуемую form family или бюджет0 из обещанной семантики.

Cache key включает request + candidate + certificate + exact checker/rule/semantic/target/limits admissions. Положительный старый результат применим только после current trust/admission checks, ограничения работы/отмены текущей compilation attempt и проверки exact bytes. Результат другого source snapshot не переносится по одинаковому normalized payload.

Проверяющая работа учитывается отдельно от runtime semantic costs. Cached historical work не обнуляет фактически выполненную нынешнюю загрузку, hash, local replay или validation. Cache не меняет accepted head и не порождает capability.

## 8. Ошибки и ограничения

| Code | Смысл |
| --- | --- |
| INPUT_NOT_READY | Нет точных обязательных bytes/registry/evaluator/ABI/checker |
| UNSUPPORTED | Неизвестная version, rule, target, domain или form |
| INVALID_SOURCE | Некорректный source при известном exact contract |
| UNTRUSTED_INPUT | Нарушена целостность или идентичность входного объекта |
| INVALID_CERTIFICATE | Предложенная замена/chain/checkpoint/reconstruction не следует из правила |
| OBSERVATION_MISMATCH | Исполнен конкретный сравнительный subject и найдено расхождение |
| CHECK_LIMIT | Исчерпан declared logical budget checker; universal result отсутствует |
| TOOL_LIMIT | Physical implementation guard инструмента |
| CANCELLED | Текущая compilation/checking attempt отменена |
| NO_APPLICABLE_RULE | REQUIRE_OPT не нашёл действительного разрешённого преобразования |
| INTERNAL_ERROR | Новый output/invariant own compiler нарушает контракт |

Runtime BudgetExceeded/Cancelled/Returned не смешиваются с этими результатами checking attempt. Внешний candidate может быть rejected без запуска программы. Ни один failure не выдаёт executable partially verified certificate.

Checker использует exact bounded counters и iterative traversals из rule limits. Before/after bytes и debug detail могут быть усечены для UI, но статус/ошибка/coverage не меняются. Незакрытые обязательства перечисляются даже при пустом отображаемом списке.

## 9. Граница независимости

Production kernel и его Formal/semantic assumptions требуют собственного аудита. Независимый oracle конечного опыта не импортирует provider; ожидания фиксируются до inspection. Mutations выполняются фактически и считаются обнаруженными только при ожидаемом semantic difference, не случайном исключении.

Root metadata probes проверяют закрытые записи и локальные связи, используя synthetic refs. Они не показывают correctness general optimizer. Whole-scope reviewer оценивает наличие достаточного проекта всей исходной задачи; такая оценка отделена от execution proof и нормативной приёмки.
