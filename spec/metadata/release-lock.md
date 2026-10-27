# R20 metadata binding и обязательные семантические проверки

Статус: проект binding для DEPENDENCY-LOCK-0.1 / RELEASE-INTENT-0.1. [Schema](release-lock.schema.json) определяет 17 закрытых record shapes. [Registry](../../registry/data/distribution/release-lock-metadata-registry.json) перечисляет их и отделяет shape от procedural obligations. Ни schema, ни sample refs не являются bagaev compiler/IR implementation.

## 1. Форматы и ссылки

В каждом новом R20 body обязательны `kind` и `profile=R20-META-0.1`. Outer ObjectRef имеет `{kind,format,codec,sha256,bytes}`. Для этих 17 bodies `format=R20-META-0.1`, `codec=BAG-META-JSON-1`; `kind` совпадает с body.kind. Schema probes используют синтетические references: соответствующие actual objects отсутствуют, это проверка структуры, не materialization. Production decoder сверяет все поля и bytes до семантики.

Upstream referenced kinds (SourceBundle, MeaningLock, Environment, ABIInterface, Toolchain и т. д.) используют свои exact format/codec contracts. Отсутствие их bytes/decoder — INPUT_NOT_READY; incompatible semantics — UNSUPPORTED_PROFILE. Outer SHA-256 по serialized bytes не заменяет domain-separated native identity R19. Знание похожего имени формата не разрешает реконструировать identity алгоритм по догадке.

`TreeInventory` — единственный R20 kind содержимого package source tree. Descriptor/LockNode.source_ref имеют kind TreeInventory. File bytes связаны через inventory; archive/git transport refs находятся в exact SourceProfile/declared inputs и отдельно сверяются с результирующим TreeInventory. Нет неописанного второго kind SourceTree.

Счётчики U64 и компоненты version U32 — decimal strings в точном диапазоне; booleans, leading zero, signed spelling, exponent и newline suffix отвергаются. JSON numeric values не используются в R20 bodies. Поле size означает байты, не число Unicode symbols.

## 2. Acyclic source/meaning binding

Manifest фиксирует authored SourceBundle и PackageResolutionContract, но не final MeaningLock. SourceBundle не включает generated Manifest/lock/binding/result и не содержит собственного hash. Manifest root requirement bytes выводятся trusted parser из source declarations; несогласие проекций — MANIFEST_MISMATCH. UI aliases развернуты в точные keys до формирования Manifest.

После resolve создаётся LockBody, затем PackageInterfaceClosure, связывающая LockRef и exact package source/descriptor/feature/interface graph. Только затем final MeaningLock и Environment; после этого SourceVersionBinding и acceptance. У AcceptedSource, BuildPlan и ReleaseCandidate должны совпасть SourceBundle и final MeaningLock/Environment bindings. Изменение selected package bytes требует нового closure/MeaningLock/source binding даже при совпадении public ABI. Working и accepted heads остаются отдельными как в R19.

Это правило устраняет цикл Manifest→MeaningLock→package lock→Manifest. MeaningLock не превращается в mutable pointer, а lock не включает будущую acceptance. Structural object graph validator обязан обнаруживать любые обратные content dependencies, а не пробовать подобрать digest fixed point.

## 3. Constraints, roots и instances

Manifest roots в V1 **безусловны**: `when_feature=null`. Программа без package imports имеет roots=[], lock roots/nodes/edges=[]; exact compiler/runtime/toolchain остаются обязательными build inputs. Пустой package graph не означает отсутствие входов сборки. Поле `Manifest.features` зарезервировано и должно быть пустым в этом профиле; оно не молча игнорируется. Необходимые dependency features задаются в `roots[*].features`; программные compiler flags входят в exact build recipe/execution policy.

В PackageDescriptor.dependencies `when_feature=null` означает unconditional edge; иначе имя относится к feature **этого исходящего package instance**. `features` внутри requirement относится к **целевому** instance. Импликации только внутри descriptor. Все имена проверяются против соответствующих declarations. Exclusion pair неупорядочена, хранится в отсортированном виде; self-exclusion запрещена, implications cycles разрешены. Unknown feature — conflict/invalid input согласно месту, не отключение edge.

Roots сравниваются по уникальному import_name. Dependency clauses имеют уникальные clause_id и import_name внутри descriptor; два одновременно активных clauses не могут претендовать на один import name. Features множества; domains, nodes, edges, inventories и clauses имеют канонический порядок, описанный lock contract. `uniqueItems` в schema не заменяет semantic uniqueness по ключам.

Root bindings задают связи root→node. Lock.edges содержит только descriptor node→node edges; `source_instance=null` зарезервирован и в production V1 отвергается, чтобы не дублировать roots. Requirement SHA — hash exact canonical clause, включая scope/domain/feature fields. Node IDs пересчитываются по формуле lock contract. Manifest/descriptor/reference bytes и полные closures проверяются отдельно от JSON Schema.

`RESOLVE` имеет old_lock_ref=null и пустые mutable/allow_new sets. `UPDATE` имеет exact old_lock_ref; mutable/allow_new keys включают domain. Операция не расширяет scope сама. Для update удаление unreachable old nodes перечисляется в diff; всякий surviving node вне U сохраняет descriptor/source/features/domain/namespace/interface. Если root constraints требуют иное — PIN_CONFLICT.

## 4. Успех и отсутствие полного результата

ResolveResult со статусом SOLVED обязан иметь lock/trace/inventory refs. При любом ином status lock_ref и inventory_ref равны null; bounded trace/diagnostics могут существовать. UNSAT_SNAPSHOT относится только к полной finite snapshot/DAG области. LIMIT/INPUT_NOT_READY/UNSUPPORTED не означают UNSAT.

LockVerification=LOCK_VALID имеет nonnull closure SHA и input inventory. INPUT_NOT_READY/UNSUPPORTED_PROFILE имеют оба поля null: нельзя придумывать digest невычисленного closure. LOCK_INVALID может включать вычисленный rejected candidate inventory/hash, если они реально существуют; они не являются valid closure и не подаются в build. Schema разрешает такой record, procedural verifier проверяет его evidence scope.

Successful BuildResult обязан иметь ровно outputs, разрешённые OutputContract; исходы failure/UNKNOWN могут содержать quarantined outputs, которые нельзя seal. `input_closure=INPUT_CLOSED` допустим только по actual enforcing BuildAdapter evidence. BuildEvidence не может объявить trusted builder по caller field без текущей trust policy. ReproductionEvidence проверяется по двум exact independent invocations и declared observation domain.

CandidateCheck PASS должен относится к exact CandidateRef и policy, иметь complete required inventory и действующую freshness/revocation policy. Seal проверяет полный required check set, не просто непустой массив. ReleaseCandidate.index_ref может быть null только для одного platform artifact; при нескольких platform entries exact index обязателен. Duplicate platform или отсутствующий index child — INVALID_CANDIDATE.

## 5. Intent identity и phase/status matrix

`intent_key` — полный R16 KeyRef `{project_id, namespace_id, generation, key}`. project_id должен соответствовать разрешённой ProjectIdentity; generation выдан именно namespace authority, не закрыт и не переиспользован. Key generation, target generation и authority epoch — три независимых значения; их совпадение как чисел не делает их одним счётчиком. Исторический key сохраняется через recovery/migration.

IntentRef — outer byte hash всего IntentBody. SemanticDigest — `SHA256(UTF8("BAG-RELEASE-INTENT-0.1") || 0x00 || BAG-META-JSON-1(IntentBody без intent_key))`; KeyRef связывается с этим digest. Credentials и transport timing не входят в body. Bound receipt/attempt хранит и KeyRef, и digest, и exact IntentRef. Lookup не выполняет новое admission; persisted reconciliation проходит свой текущий grant+epoch+CAS.

PUBLISH_CONTENT имеет immutable content target; PROMOTE_ALIAS требует declared generation/content CAS semantics и exact expected binding; DEPLOY_BINDING требует GENERATION_CAS, nonnull generation и DeploymentPlanRef. COMPENSATE имеет nonnull compensates_ref и exact new target preconditions; если компенсация меняет runtime binding, также обязателен DeploymentPlanRef и generation CAS. Для остальных actions compensates_ref=null. Secret credentials не попадают ни в payload inventory, ни в public provenance.

Матрица ниже совпадает с [machine matrix](../../registry/data/distribution/release-result-matrix.json). Обозначения: R — обязателен nonnull; N — только null; O — nullable. Колонки A=attempt_id, C=local_commit_ref, Rcp=remote_receipt_ref, Obs=observation_ref, M=member_results_ref.

| Status | Разрешённая phase | A | C | Rcp | Obs | M |
| --- | --- | --- | --- | --- | --- | --- |
| PREPARED | PREPARE | N | N | N | N | N |
| RESERVED | RESERVE | R | R | N | N | N |
| MAY_HAVE_RUN | ARM, DISPATCH | R | R | N | N | N |
| CONFIRMED_SUCCESS / CONFIRMED_REJECTION | DISPATCH, RECONCILE, TERMINAL | R | R | R | O | N |
| CONFIRMED_NOT_APPLIED | RECONCILE, TERMINAL | R | R | R | O | N |
| LOCAL_REJECTED_BEFORE_DISPATCH | TERMINAL | R | R | N | N | N |
| CONTENT_OBSERVED | OBSERVE, RECONCILE | O | O | N | R | N |
| UNKNOWN_MAY_HAVE_RUN | DISPATCH, RECONCILE | R | R | N | O | N |
| CANCELED_BEFORE_DISPATCH | TERMINAL | R | R | N | N | N |
| STALE_BASE | PREPARE, RESERVE, ARM, DISPATCH, RECONCILE | O | N | N | O | N |
| SUPERSEDED_OBSERVED | RECONCILE, OBSERVE | R | O | N | R | N |
| PARTIAL | DISPATCH, RECONCILE, OBSERVE | R | O | N | O | R |
| INPUT_NOT_READY / DENIED / UNSUPPORTED_DESTINATION / LIMIT | PREPARE, RESERVE, ARM, DISPATCH, RECONCILE, OBSERVE | O | N | N | O | N |

Матрица описывает OperationResult, а не разрешает произвольный переход Attempt. Attempt создаётся RESERVED; arm переводит в MAY_HAVE_RUN; после возможного dispatch он переходит только в UNKNOWN либо доказанный terminal result. Если уже admitted RESERVED intent встретил stale semantic guard до arm, R16 требует сохранить terminal rejection: LOCAL_REJECTED_BEFORE_DISPATCH с LocalCommit, exact reason и доказанным no-send/fenced dispatcher. Это отличается от DENIED/STALE_BASE до admission, где новой записи нет. После MAY_HAVE_RUN один stale guard недостаточен для такого terminal result: debt сохраняется, пока не доказан actual outcome. UNKNOWN становится terminal только по exact receipt/proof; неатрибутированное CONTENT_OBSERVED/SUPERSEDED не снимает debt. Cancellation после arm не даёт CANCELED_BEFORE_DISPATCH без доказанного final fence/not-sent proof. Terminal intent нельзя вновь arm/dispatch. PREPARED — draft без выделенного attempt; отмена такого draft просто удаляет локальный proposal, не создаёт execution receipt.

CONFIRMED_NOT_APPLIED remote receipt содержит доказательство невозможности позднего исполнения, а не только пустой lookup. CANCELED_BEFORE_DISPATCH LocalCommit содержит доказанный dispatcher fence/no-send fact. PARTIAL MemberResultInventory перечисляет **все** planned actions, exact action refs и каждый результат; неперечисленный member остаётся UNKNOWN, aggregate success запрещён. Для read-only observation C=null; запись наблюдения требует reconcile grant и nonnull C. Отказ LIMIT/DENIED после ранее MAY_HAVE_RUN оставляет старый attempt/debt неизменным; это отказ новой команды, не утверждение «эффекта не было».

## 6. Проверка shapes и предел

Root-authored fixtures используют синтетические refs без доступных preimages и не являются integration input. Validator проверяет закрытые поля, types, ranges, conditional shapes и phase/status matrix. Он не импортирует provider/independent oracle. Отдельные procedure/real integration проверки обязаны проверить bytes, graph closure, actual authority, origin, destination guarantees и полный язык. Production records не принимаются на основании одного PASS этого набора.

`tools/build_metadata_fixtures.py` — provenance builder. Повторный запуск разрешён только в disposable unsealed copy; final package защищён MANIFEST.sha256. `tools/validate_metadata.py` не перезаписывает existing reports и после sealing пишет отчёт только вне package.
