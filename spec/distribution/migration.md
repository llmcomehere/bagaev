# MIGRATION-PLAN-0.1 — явный переход проекта между версиями

**R19 · WORKING_DESIGN.** Контракт продолжает [VERSION-BINDING-0.1](compatibility.md), R16 admission/idempotency, R17 immutable environments/pins и R18 recovery/current authority. Он описывает алгоритм V1 для всего проекта. COMPAT-FINITE-0.1 реализует только ограниченную модель преобразования и CAS; действительный filesystem, scheduler, authority service и compiler остаются предметом [интеграционного маршрута](compatibility-route.md).

## 1. Режимы перехода и результат

| Режим | Что может измениться | Обязательное условие |
| --- | --- | --- |
| HOST_TOOL_UPDATE | Host default installation | ProjectBinding и все его source-version bindings остаются прежними; алгоритм миграции проекта не запускается |
| STORAGE_REENCODE | Представление значений/метаданных и storage format map | MeaningLock и logical identities сохраняются; проверяются typed value relation и все защищённые состояния |
| ENVIRONMENT_REPIN | ToolBuild/EnvironmentRef при прежнем MeaningLock | Exact new build conformance, target/ABI/adapter constraints и новое основание применимости evidence; прежние receipts не переписываются |
| SEMANTIC_CHANGE | Working SourceRef и/или MeaningLock | Явно объявленные изменения, новый source candidate и verification/acceptance obligations; результат не маркируется PRESERVING |
| CONTINUATION_REENCODE | Job checkpoint/runtime representation | Отдельный continuation relation, тот же history/effect frontier и проверенный mapping budget/cancel; иначе job остаётся suspended |

План имеет ровно один primary mode и перечисляет дополнительные изменения как typed steps. Сочетание storage и environment migration не освобождает ни от одного соответствующего условия. HOST_TOOL_UPDATE — отдельная операция R17; в project migration plan она не допускается.

Результат успешного перехода — новый immutable ProjectBinding, durable MigrationReceipt и явный список оставшихся verification/acceptance/resumption obligations. «Миграция завершена» означает, что новое состояние корректно опубликовано. Это не означает, что новый source принят или каждый suspended job разрешено продолжить.

Профиль R19 V1 использует **остановку обычных writers на финальном переходе**. Dual-write между произвольными версиями и online rolling schema conversion не заявляются. Preview/staging могут работать параллельно с проектом, но опубликован может быть только кандидат, соответствующий окончательно закрытому source cut.

## 2. Неизменяемые объекты и порядок хеширования

Входы представляются exact refs. Labels, пути, актуальная версия dependency и непроверенный supplied equivalent=true не заменяют content identity или proof.

### 2.1. MigrationIntent

Intent задаёт ProjectIdentity, source ProjectBindingRef/generation, target binding requirements, mode, explicit transform path, preservation/change policy и разрешённый предел работы. Stable maintenance key и semantic digest используют R16. Current delegated policy может разрешать такой intent; отдельный human prompt не является технической предпосылкой каждого шага. Наличие сохранённого intent или старой подписи не выдаёт нынешние полномочия.

Source generation входит в смысл intent. После изменения source cut нужен новый intent/maintenance key либо заранее определённая отдельная операция replanning с новым semantic digest. Старый key нельзя незаметно перепривязать к новому проекту, transform path или candidate. Повтор прежнего key возвращает прежний receipt/status по R16.

### 2.2. MigrationPlanBody

~~~text
MigrationPlanBody = {
  intent_ref, source_project_binding_ref, source_generation,
  source_semantic_state_root, source_participant_vector_ref,
  source_meaning_bindings_ref, target_binding_requirements_ref,
  exact_registry_ref, current_policy_requirements_ref,
  mode, transform_steps, affected_closure_ref, unaffected_boundary_ref,
  preservation_contract_refs, change_declaration_ref,
  protected_inventory_ref, identity_mapping_rules_ref,
  required_checkers, required_target_pins,
  resource_limits_ref, final_cut_policy_ref, abort_policy_ref, activation_policy_ref
}
~~~

TransformStep связывает input/output FormatContractRefs, exact transform implementation, domain predicate, identity mapping, required preservation relation, checker и loss policy. Порядок шагов указан явно. Число шагов ограничено; неявный выбор «самого нового конвертера» запрещён. Plan не содержит certificate, который затем ссылается на этот же Plan.

Affected closure вычисляет trusted reference extractor каждого вида. Boundary фиксирует все зависимости, остающиеся вне преобразования, их exact refs и условия неизменности. Любой неизвестный artifact kind, неполный inventory, неразрешённая reference или неподдержанный обязательный decoder дают INPUT_NOT_READY/REGISTRY_COVERAGE_GAP. Пустой список нельзя выдавать за отсутствие непонятных зависимостей.

### 2.3. Candidate и certificate

Порядок создания:

1. Immutable PlanBody и его PlanRef.
2. Staged payload objects, resulting ProjectBinding body и его Ref; затем CandidateBody: PlanRef, before/after semantic roots, ProjectBindingRef, format map, identity map, protected inventory roots, loss/change report, derived-index descriptions.
3. PreservationCertificate: PlanRef, CandidateBodyRef, exact before/after roots, relation kind, observation/domain refs, assumptions, checker build/method, verdict и evidence refs.
4. PreparedEnvelope: CandidateBodyRef, certificate refs, final-cut certificate, durable target pins и capacity reservation.
5. AuthorityCommitRecord, затем local MigrationReceipt, которые ссылаются на PreparedEnvelope.

CandidateBody не содержит собственный certificate/receipt, а его state root исключает enclosing migration event/current journal head. Исторические graph edges могут ссылаться на более ранние receipts. PreparedEnvelope и commit envelope добавляют связь после вычисления body hashes; обратного ребра в тот же content-addressed body нет. Никакой из этих hashes сам по себе не подтверждает авторство или полномочия.

Checker verdict содержит PASS, FAIL или UNKNOWN. PASS допустим только после выполнения exact check method по его admission policy; caller не может самостоятельно выдать PASS посредством поля запроса. Для SEMANTIC_CHANGE certificate подтверждает сохранность защищённых состояний и корректность объявленного изменения, но не equality изменённого поведения.

## 3. Что обязательно сохранить

ProtectedInventory строится независимо от transform: из исходного checkpoint, journal reducers, canonical graph и всех зарегистрированных state owners. Это не список, который конвертер составляет по удобным ему полям. Проверка completeness использует R18 checkpoint commitments и participant frontier. Unknown semantic state не трактуется как пустое.

| Область | Проверяемое отношение до/после |
| --- | --- |
| Values/types | Exact nominal/type identity либо объявленная typed relation; presence/null/default/order/overflow проверяются отдельно |
| Source versions | Каждая версия хранит собственные SourceRef, MeaningLockRef, EnvironmentRef. Working migration не переназначает meaning старому accepted head |
| Canonical relations | Logical entity IDs сохраняются либо преобразуются инъективным explicit mapping; version endpoints и link meaning согласованы с новыми refs |
| Reverse indexes | Перестраиваются из canonical edges под exact extractor/query contract; stale cache не источник истины |
| Requirements/acceptance | Старые subject/method/domain/assumptions immutable; новый subject не получает acceptance по совпадению имени |
| Work/obligations | Полный multiset обязательств, их IDs, зависимости, UNKNOWN/blocked причины и незавершённые попытки сохраняются; новые обязательства добавляются явно |
| Effects/keys | Remote identity, canonical request digest, original operation revision, namespace/generation, tombstones/closed frontiers и MAY_HAVE_RUN/UNKNOWN не теряются |
| Jobs | Progress frontier, continuation provenance, outstanding reservations, spent budget и cancellation state сохраняются либо job становится явно suspended |
| History | Исторические receipts/evidence остаются доступными под их original format contract; миграция не объявляет старое исполнение новым |
| Authority/identity | IDs и authority epochs не переиспользуются; current permissions проверяются заново; serialized capabilities не оживают |
| Inert bytes | Допущенные extension bags/comments/attachments сохраняются согласно explicit preservation contract; unknown fields вне allowlist дают отказ |

В V1 preserving migration loss report должен быть пуст. SEMANTIC_CHANGE может менять объявленное поведение/исходник, но не уничтожать уже возникшие долговые, effect, identity или history records. Пользователь может отдельно отменить обязательство разрешённой business operation с собственным доказательством; migration не подменяет её удалением записи.

### 3.1. Бюджет и continuation

Число remaining=100 до и после недостаточно, если изменилось определение semantic step. Проверяются units, accounting rule, spent/remaining frontier, maximum already admitted reservation и cancellation visibility. Mapping между units требует зарегистрированного relation и проверяемого ограничения на оставшееся поведение. В отсутствие такого основания continuation переводится в SUSPENDED_INCOMPATIBLE_RUNTIME, с сохранением checkpoint и счётчиков.

Возобновление job — отдельный RESUME admission. Оно проверяет current authority, exact runtime/state contract, reservation/effect ledger, budget и cancellation заново. Создание новой job после старой не может списать уже израсходованный shared/project budget или скрыть неизвестный исход прежнего эффекта.

### 3.2. Проверка relation graph

Сначала преобразуются canonical entity/version records. Trusted extractor пересчитывает только воспроизводимые structural edges. Authored и observed canonical edges сохраняются через отдельное schema transformation с исходными provenance, subject/version refs и статусами UNKNOWN/gap; новый extractor не обязан уметь заново породить прошлое наблюдение или авторское заявление. Checker сопоставляет структурные edges через identity map, а исторические — по их собственному preservation contract, без перепривязки к новому subject. Проверяются отсутствие потерянных endpoint IDs, dangling refs, accidental many-to-one merges, согласованность accepted/working версий и scope новых obligations. Reverse index строится заново из полного target canonical graph и проверяется запросами в обе стороны. Равенство числа edges не доказывает сохранение их значения.

Новый evidence subject создаёт новые applicability edges; старый historical PASS остаётся фактом о старом subject. REUSE_EVIDENCE допускается лишь по отдельному transfer claim, покрывающему точное изменение и observation domain. Проверка schema сама такого claim не создаёт.

## 4. Plan, preview и чистое построение

~~~text
plan(intent, current_project, trusted_registry):
    admit original key/digest and current requested permissions
    require exact source ProjectBindingRef and semantic generation
    resolve source/target closure, formats, tools and all required readers
    inventory protected state independently of transform
    resolve an explicit bounded transform path and each domain predicate
    derive affected closure plus exact unaffected boundary
    require declared observation coverage for every changed semantic axis
    reserve staging budget; persist PlanBody and maintenance status
    return PlanRef and preview requirements

stage(plan):
    pin all source and target dependencies before dereferencing
    execute registered pure transforms in isolated staging under resource limits
    never dispatch effects or invoke project lifecycle hooks
    compute target refs, identity map, loss/change report and protected inventory
    rebuild derived indexes from target canonical graph
    persist bounded CandidateBody and payload closure durably
    return CandidateBodyRef

check(plan, candidate):
    rederive all refs/inventories using exact independent checkers
    validate domain, invariants, identity relation, obligations and observations
    verify target environment/materialization and all required operation capabilities
    produce certificate with exact subject and assumptions
    return PASS, FAIL or UNKNOWN; never publish project here
~~~

Preview показывает source/target refs, affected/unaffected closure, changed meaning axes, files/formats, identities, suspended jobs, remaining UNKNOWN, evidence invalidations, required acceptance, storage/pin cost и rollback constraints. Он вычисляется из actual staged candidate; это объяснение перехода, не proof. Если CandidateBody изменился, старый preview/certificate неприменимы.

Pure transform не читает undeclared network/time/random/current default; требуемые входы фиксируются в Plan. Sandbox failure, exception, timeout, noncanonical output или превышение лимита завершают staging отказом. Existing project остаётся прежним. Независимый checker использует собственные правила проверки, а не булево поле, присланное transform.

## 5. Финальный cut и actual writer fences

Обычные source/state writers, effect dispatch, scheduler/budget updates и metadata publishers не должны менять исходное состояние во время публикации. Одного mutex в CLI или смены `activeVersion` недостаточно: каждый actual storage commit/dispatch проверяет current authority epoch и format/generation contract. Не отвечающий worker не считается остановленным.

Migration control records живут отдельно от semantic input cut. Их запись не маскируется под изменение source data. Любая обычная запись в source/relations/jobs/receipts/budget увеличивает semantic generation либо попадает в перечисленный participant frontier. Generation не уменьшается и не сбрасывается при возврате прежнего content hash: это защита от ABA.

Финальный алгоритм:

1. Проверить current write authority, trust/revocation, exact intent/plan/candidate/certificates, target pins и ресурсный запас. Нельзя сначала отнять старые права, а потом впервые выяснять, что target decoder отсутствует.
2. Зафиксировать FENCING в current authority domain R18. Перекрыть admission новых обычных writers/dispatch и довести все участники до подтверждённого writer barrier. Коммитящие storage adapters сами отвергают старый epoch. Неклассифицированная reservation держит переход незавершённым.
3. Снять final participant vector, committed frontier и complete obligation inventory. Уже зарегистрированный UNKNOWN external effect сохраняется как UNKNOWN; он не обязан исчезнуть для переноса ledger, но затронутая работа остаётся заблокированной. Migration не повторяет и не «дозавершает» такой эффект.
4. Сопоставить final semantic generation, cut, source binding, inventory и boundary со subject certificate. В R19 V1 любое различие даёт STALE_SOURCE_CUT: старый candidate не публикуется. Новый plan строится по final current state с новым key/digest. Неявное догоняющее преобразование неподтверждённых записей запрещено.
5. После точного совпадения получить FENCED_FINAL и final-cut certificate. Материализовать durable PreparedEnvelope и PREPARED control record, связывающие именно этот cut/candidate и target launch pins.
6. Проверить, что final prepared output, journal/receipt records и authoritative operation помещаются в заранее объявленные limits. Недостаточный capacity даёт отказ до authority commit.

Если writer barrier не завершён, состояние остаётся FENCING/QUARANTINED, а не ACTIVE. Возможность read-only inspection задаёт current policy. Timeout не доказывает завершение чужого действия. Когда изменение cut обнаружено после fencing, можно строить новый план в закрытом режиме либо безопасно отменить maintenance; любое восстановление доступа использует свежие права текущей authority, а не прежний epoch.

## 6. Публикация в двух durability domains

Current authority и project storage могут быть разными долговечными системами. Нельзя объявить их одной атомарной транзакцией по факту соседства вызовов. Используется односторонний протокол R18:

~~~text
activate(prepared, attempt_id):
    lookup attempt_id under original intent digest
    if authoritative terminal receipt exists: finish/read same attempt
    require PREPARED, exact final cut and durable dependency pins
    recheck current policy and actual fence status
    authority.CAS_commit(attempt_id, PreparedEnvelopeRef, fresh_epoch)
    # response loss is resolved by authority lookup, not a new attempt
    local_atomic_transaction:
        require same prepared record and expected source generation
        require current exact authority(attempt_id, PreparedEnvelopeRef, fresh_epoch)
        set active ProjectBinding = exact prepared target
        advance semantic generation monotonically
        append migration event + receipt + required work/applicability records
        mark local control ACTIVATED
    publish acknowledgement and retain old/new history per reachability policy
~~~

AuthorityCommitRecord связывает attempt, PreparedEnvelopeRef и fresh epoch. После него host не имеет права автоматически вернуться к old authority, даже если local activation не успела. Recovery по тому же attempt завершает тот же target, только пока этот attempt/epoch сохраняет текущие полномочия. Если новая recovery уже superseded его, старый receipt не открывает прежний epoch. Несовпадение local prepared data с authority decision даёт QUARANTINED, без запуска программ.

Проверка current exact authority выполняется на actual commit boundary по протоколу fencing adapter R18. Предварительный remote `get` перед локальной транзакцией недостаточен: между ними полномочие может измениться. Authority не признаёт новый barrier закрытым до того, как actual storage adapter отвергает предыдущие epochs; local activation обязана участвовать в этом же guard. Если адаптер не способен обеспечить эту связь, публикация запрещена как INPUT_NOT_READY. Сценарий «authority commit A → новая recovery B → запоздалая local activation A» должен дать отказ A без записи старого binding.

Локальная транзакция включает ProjectBinding, work/obligation updates, migration receipt и event; невозможно опубликовать новый format map с прежним budget ledger. Если storage adapter не предоставляет такую атомарность, release profile должен реализовать эквивалентный WAL/commit protocol с отдельным доказательством, иначе INPUT_NOT_READY.

Target EnvironmentRef материализуется и долговечно закрепляется до PREPARED. ProjectBinding хранит ссылку на immutable environment, а не копирует mutable host default. Cross-store pin lifecycle и release неизвестного launch intent следуют R17; crash не разрешает GC зависимостей незавершённого перехода.

Права нового writer не включаются раньше подтверждённого local activation. Старый tool, продолжающий работать после cutover, получает STALE_WRITER_EPOCH/UNSUPPORTED_WRITE_CONTRACT на реальной точке записи. Совместимость чтения old format не разрешает запись через old schema.

## 7. Фазы, сбои и отмена

| Durable phase | Разрешённый следующий шаг | Сбой/отмена |
| --- | --- | --- |
| PLANNED | STAGED либо ABORTED | Удаление staging только после terminal attempt и release pins |
| STAGED | CHECKED либо ABORTED | Старый active binding не меняется; output остаётся untrusted candidate |
| CHECKED | FENCING либо ABORTED | Новая обычная запись делает subject stale; certificate не обновляется сам |
| FENCING | PREPARED после FENCED_FINAL либо QUARANTINED/ABORTED | Timeout не снимает actual fences и не возвращает старые токены |
| PREPARED | AUTHORITY_COMMITTED либо ABORTED при доказанном отсутствии commit | Unknown commit outcome требует lookup того же attempt |
| AUTHORITY_COMMITTED | ACTIVATED либо QUARANTINED | Cancel не откатывает authority decision; завершить выбранный target |
| ACTIVATED | Терминальный receipt | Повтор возвращает receipt; дальнейшее изменение — новый intent |
| ABORTED | Терминальный refusal/abort receipt | Key не переиспользуется; GC только по closed lifecycle |
| QUARANTINED | Repair/recovery по exact attempt | Нет ordinary writes/dispatch; сохраняются evidence и долг |

PREPARED→ABORTED допустим, только если authority atomically закрепила non-commit/abort outcome для того же attempt. «Не нашёл ответ в локальном cache» не является таким доказательством. Гонка cancel и commit разрешается в единственном authority attempt record; один исход не может соседствовать с другим под тем же ключом.

Если после AUTHORITY_COMMITTED истёк client timeout, ответ — OUTCOME_UNKNOWN с lookup handle, а не `migration failed, retry fresh`. Будущий lookup проверяет нынешнее право читать receipt. Внутреннее завершение принятого authority решения и новое user action различаются; отзыв пользовательских write rights не позволяет реанимировать старый target, но может оставить проект недоступным до authorized repair.

### 7.1. Почему нельзя просто откатить snapshot

До activation staging можно отбросить по terminal abort, сохранив monotonic authority history и расходы maintenance. После activation R19 V1 всегда требует **новую reverse migration из текущего состояния**. Даже возврат того же scalar/source hash не означает, что не было новых effects, receipts, obligations или budget spending.

Reverse plan проверяет поддержку обратного направления, domain нового состояния, новые writes/receipts/UNKNOWN, сохранность spent budget и current epoch. Отсутствие inverse transform даёт ROLLBACK_REQUIRES_NEW_PLAN или REVERSE_DOMAIN_UNSUPPORTED; оно не разрешает удалить свежие записи. Старый snapshot остаётся историческим input/inspection artifact.

Finite model может иметь более узкую операцию rollback без промежуточных project writes, защищённую точным generation guard. Это экспериментальное подмножество, не дополнительный production shortcut: production activation всё равно проходит новый intent/prepare/authority protocol.

## 8. Ошибки, ограничения и наблюдаемость

Минимальный error contract различает INPUT_NOT_READY, VERSION_IDENTITY_CONFLICT, REGISTRY_COVERAGE_GAP, UNSUPPORTED_REQUIRED_FEATURE, UNSUPPORTED_OPERATION, DOMAIN_MISMATCH, OBSERVATION_COVERAGE_GAP, IDENTITY_MAP_INVALID, PROTECTED_STATE_LOSS, SEMANTIC_CHANGE_REQUIRED, CHECK_UNKNOWN, STALE_SOURCE_CUT, STALE_WRITER_EPOCH, FENCE_INCOMPLETE, TARGET_PIN_UNAVAILABLE, CAPACITY_EXCEEDED, OUTCOME_UNKNOWN, ATTEMPT_DIGEST_CONFLICT, REVERSE_DOMAIN_UNSUPPORTED и QUARANTINED.

Diagnostic связывает phase, exact original request revision, plan/candidate refs, affected family/kind, missing condition и безопасный lookup/replan action. Неизвестный code сохраняется как unknown diagnostic original revision. Статус checker UNKNOWN не превращается в FAIL исходной программы, а timeout migration не превращается в доказанный abort.

Пределы VERSION-BINDING-0.1 применяются до recursion/allocation. Дополнительно Plan содержит max staged bytes/objects, CPU/step quota, temporary pin quota и deadline policy. Counters не wrap; исчерпание uint64 требует controlled refusal. Resource accounting maintenance не списывается из job budget без объявленного контракта и не сбрасывает уже израсходованное.

Граница storage object, state snapshot, response envelope и transport frame имеет собственный budget: успешный state, обёрнутый в слишком большой response, не считается доставленным результатом. Capacity output проверяется до publication; если committed receipt не помещается в inline response, используется заранее предусмотренный bounded receipt reference protocol, не неявное усечение. Конкретный transport profile обязан объявить этот путь до выполнения.

Metrics разделяют planned/staged/check PASS/authority committed/local activated/remaining suspended/UNKNOWN. Одно число «успешно мигрировано» не заменяет их. Пользователь видит old/new exact bindings, изменённые meaning axes, сохранённые долги и требуемые следующие действия; implementation-only hashes могут быть раскрыты в diagnostic detail, не засоряя обычный путь.

## 9. Приёмочные основания и границы R19

Критерий T18-C01 проверяется полнотой registry, exact directed operation rules, version bindings для каждого family/kind, unknown/default/lifecycle policy и негативными cases. T18-C02 проверяется независимостью host update от ProjectBinding, сохранением old MeaningLock, явным intent/preview, preservation или declared semantic change, защитой historical acceptance и fault-safe activation.

Finite tests подтверждают только перечисленные трассы bounded model. Они не доказывают полноту реального registry, arbitrary program equivalence, crash durability storage adapters, реальный compiler/runtime, wire downgrade protection или продолжение всех V1 jobs. Такие проверки заданы в [compatibility-route.md](compatibility-route.md) и до выполнения отмечены NOT_RUN. Для stage2 нужен полный проверяемый контракт; stage3 и stage4 требуют дополнительного независимого выполнения и принятия исходных критериев целиком.
