# RELEASE-INTENT-0.1 — выпуск из точных входов и отдельное внешнее действие

Статус: проект R20; уточняет **T18-C05**, уже имевший stage2 в сохранённом R07. Повторное описание этого правила не даёт нового балла. Связанный основной предмет — [точный lock, T13-C02](../toolchain/dependency-lock.md). Production integrations ещё `NOT_RUN`.

## 1. Инвариант

`accept_source`, `verify_locked`, `build`, `check_candidate`, `seal_candidate` и просмотр evidence не создают разрешение на публикацию, изменение remote alias, deploy, migration или ActiveBinding. Ни successful test, ни signature, ни provenance, ни accepted source не служат таким разрешением.

Внешняя операция допускается отдельным **точным намерением** и действующей политикой полномочий. Политика может заранее делегировать автоматический выпуск при конкретных условиях: обязательного ручного вопроса на каждом шаге нет. Но она должна явно охватывать action kind, exact target, payload/candidate, principal, expected target state, limits и adapter. Отсутствующее разрешение — отказ, а не вывод из намерения «принять правку».

Историческая приёмка конкретной версии остаётся историческим фактом. Новый accepted source не переписывает старый release; выпуск старой принятой версии допустим только если текущая release policy явно разрешает именно её. Если policy требует current accepted head, его generation проверяется на admission/commit, а не только при подготовке.

## 2. Объекты и связи

Все ссылки typed `ObjectRef` и canonical metadata следуют DEPENDENCY-LOCK-0.1. Object hash находится вне собственного body. Неизвестные исполняемые semantics отклоняются по [R19 compatibility](compatibility.md).

| Объект | Обязательная связь | Чего объект сам не делает |
| --- | --- | --- |
| AcceptedSource | ProjectIdentity, source version/ref, acceptance record, exact MeaningLock/Environment, authorized acceptance result | Не запускает build/publish/deploy |
| BuildPlan | accepted source ref, LockRef, environment, target/recipe/toolchain/closed input inventory, output contract | Не является результатом исполнения |
| BuildResultBody | PlanRef, invocation identity, exact output refs, declared observations/effects, outcome, completeness classification | Не доказывает доверие к builder или воспроизводимость |
| BuildEvidence | ResultRef, trusted builder/verifier identities, logs/provenance/reproduction refs, scope and exclusions | Не даёт publish capability |
| ReleaseCandidateBody | AcceptedSourceRef, MeaningLockRef, EnvironmentRef, LockRef, ordered platform build results, exact artifact/index refs, evidence refs, release policy ref | Не содержит собственной подписи/будущего receipt и не изменяет registry |
| CandidateCheck | CandidateRef, checker/ref, exact policy, input evidence inventory, status and expiry/revocation semantics | Не покрывает другого candidate, target или policy |
| CandidateSeal | CandidateRef + exact successful required checks + evidence inventory ref | Не является разрешением на внешнее действие |
| PublishIntent | SealRef, exact publication actions, destination/namespace, expected remote state, adapter guarantee profile, stable semantic key | Не равен намерению deploy |
| DeploymentIntent | SealRef, exact deploy target/config/state-transition plan, expected generation/current binding, adapter/authority/fence requirements | Не возникает из publish receipt |
| Attempt / Receipt | stable intent digest, actual attempt/fence, dispatch evidence, exact result or UNKNOWN, external observations | Не переписывает прошлое и не делает неизвестный исход неисполненным |
| ActiveBinding / Observation | actual target generation, exact artifact+config+environment, authority epoch, fresh observation/ref | Наблюдение в момент t не обещает дальнейшую неизменность/health |

Hash DAG: source/descriptors/lock/environment → BuildPlan → BuildResultBody → BuildEvidence → ReleaseCandidateBody → CandidateCheck → CandidateSeal → Intent → Attempt/Receipt/Observation. Evidence об определённом body хранится после body; новая проверка seal выпускается отдельно. Provenance sidecar не встраивается в artifact, хеш которого он подписывает. Если контейнер должен содержать provenance, сначала фиксируется внутренний artifact, затем sidecar, затем внешний контейнер с отдельным digest; subject уровни не смешиваются.

## 3. Построение и проверка кандидата

### 3.1 Входы и выход

`make_candidate(AcceptedSourceRef, LockRef, BuildResultRefs, EvidenceRefs, ReleasePolicyRef)` возвращает immutable CandidateRef либо bounded diagnostic. Обязательные exact upstream bytes должны существовать и быть поддержаны; заглушки `source_ok`, `equivalent=true`, `reproducible=true` не заменяют проверку.

Алгоритм:

1. Проверить typed refs, hashes, acceptance lineage и exact Source/MeaningLock/Environment пары. Рабочий неприёмочный snapshot нельзя подставить вместо AcceptedSource. При policy current-head зафиксировать expected acceptance generation.
2. Повторить locked verification по exact manifest/lock. Проверить Plan→Result→artifact связь каждого build; builder/checker identities и actual input/effect closure по trust policy.
3. Сверить target matrix. Для каждого target нужен отдельный BuildPlan/Result с точными host/target inputs и outputs. Multi-platform index перечисляет exact child digest, size, media type и platform; отсутствующие/дублированные/подменённые children запрещены. Digest index не подменяет проверку полноты детей.
4. Проверить required observations/tests/claims. UNKNOWN, stale, incomplete, unsupported domain, unmatched assumptions и missing required check блокируют seal. Политика может принимать unreproduced build, если это явно указанный более слабый профиль; он никогда не маркируется REPRODUCED.
5. Построить candidate body и hash. Запустить required checks именно по CandidateRef. Проверить scopes и policy identities, затем создать seal отдельным object. При изменении любого байта candidate нужен новый check/seal.
6. Локально сохранить immutable objects. Изменение project candidate pointer — отдельный CAS/receipt; remote targets и dispatch counter не меняются.

Валидация подписи отвечает на «какой ключ подписал какие bytes», trust policy — «допустим ли этот signer/builder для данной роли», checks — «какое утверждение и в какой области проверено», authorization — «может ли этот principal сейчас совершить это действие». Эти результаты хранятся отдельно. Экспорт SLSA/OCI не расширяет их область автоматически.

### 3.2 Build isolation

Рецепт release build выполняется в exact declared environment с доступом только к verified inputs и отдельному output space. Ambient network, package lifecycle hooks, filesystem outside input closure, публикационные credentials и remote deployment authority не выдаются по факту build. Нужный внешний build effect должен быть явно допущен своим operation/effect contract и записан в evidence; он может сделать профиль nonreproducible. Local output writes не равны праву менять внешний registry.

Сборка/проверка не могут выполнять post-build publish hook из package metadata. Such hook — unsupported input либо отдельное, видимое намерение пользователя/политики; его нельзя прятать под названием `check`/`install`. Реальный adapter должен обеспечивать ограничение, а не полагаться на соглашение о названиях команд.

## 4. Точная семантика намерения

`IntentBody` содержит:

- `project_identity_ref`, principal identity, action kind `PUBLISH_CONTENT | PROMOTE_ALIAS | DEPLOY_BINDING | COMPENSATE`, CandidateSealRef и policy ref;
- destination identity с tenant/account/registry/repository/environment; credentials хранятся отдельно; locator не определяет полномочия;
- exact payload inventory и target path/alias/config refs, media types, byte sizes, transformation profile если destination меняет representation;
- expected target `{generation, current_binding_ref|null}`; content-only target может иметь explicit immutable-object precondition, но не притворяется alias CAS;
- exact adapter identity/version и guarantee profile, declared authority domain, retention/query semantics, expected authority epoch/fence domain;
- budget/expiry policy, allowed attempts, compensation relationship при наличии; `intent_key` — полный R16 KeyRef `{project_id, namespace_id, generation, key}`, не один label, и canonical semantic digest. Key generation, target generation и authority epoch различны.

Digest включает все поля, способные изменить действие, включая target, operation, payload, expected generation и профиль гарантий; точная domain-separated формула и KeyRef binding заданы в [metadata binding](../metadata/release-lock.md). Ephemeral bearer credentials и transport timestamps в digest не входят; они проверяются текущим authority adapter. Один key с другим semantic digest — `KEY_CONFLICT`. Смена target/candidate/precondition/adapter profile означает другое намерение. Новый key нельзя использовать для обхода unresolved старого действия над тем же target.

Размеры/порядок actions зафиксированы. Для нескольких destinations создаются отдельные intents/receipts; агрегат выпуска имеет vector результатов. Успех в одном registry не делает все остальные опубликованными. Распределённая транзакция между registry, deployment authority и локальным project store не предполагается.

## 5. Admission, dispatch и неизвестный результат

Применяются [R16 idempotency lifecycle](../protocol/idempotency-lifecycle.md) и текущая authority вне rollback-domain. Ниже специализация, не новый менее строгий retry-протокол.

### 5.1 Локальная последовательность

1. **Read gate.** Для lookup/history проверить текущие права чтения scope. При existing key сначала вернуть exact matching historical receipt/attempt; новый capability, current candidate head или freshness check не переписывает исторический результат. При digest mismatch — KEY_CONFLICT.
2. **Prepare.** Для нового действия проверить exact seal, current policy, authority, trust/adaptor capabilities, target state precondition и бюджеты. Любой unavailable или ambiguous prerequisite — INPUT_NOT_READY/UNKNOWN, не dispatch. Сохранить draft без внешнего эффекта.
3. **Reserve.** В одной локальной transaction зарегистрировать intent/key/digest, ожидаемый target generation, budget reservation, attempt ID, outbox/job и receipt skeleton. Заблокировать конфликтующий single-flight scope. Проверить размеры целого post-state/transport envelope до commit.
4. **Arm.** Перед фактической передачей отметить durable `MAY_HAVE_RUN` и сохранить exact request digest/fence. Переход должен переживать crash. Если durability недоступна, действие не допускается. Этот маркер может быть консервативным: он не утверждает, что remote effect уже был.
5. **Actual dispatch.** Sink/adapter проверяет текущую authority/expected generation/fence **в точке реального commit**, либо authority выдаёт неотзываемый на короткий срок permit с точно доказанным contract. Простая проверка доступа за секунду до HTTP-запроса этого не гарантирует. Отзыв, смена generation и задержанный старый worker должны блокироваться реальным writer boundary.
6. **Record.** Exact подтверждённый result сохраняется под прежним attempt ID. Потеря ответа, timeout, disconnect, crash between remote commit and local receipt, неподдерживаемая интерпретация response → `UNKNOWN_MAY_HAVE_RUN`. Reservation/pins/receipt не удаляются по TTL.

До MAY_HAVE_RUN корректная отмена может дать `CANCELED_BEFORE_DISPATCH` только если dispatcher действительно fenced и нет пути, который уже мог отправить запрос. Если admitted RESERVED intent встретил stale semantic guard до arm, сохраняется terminal `LOCAL_REJECTED_BEFORE_DISPATCH` с LocalCommit/no-send proof по R16; такой отказ отличается от DENIED до admission. После MAY_HAVE_RUN отказ новой команды/отмена означает прекращение дальнейших локальных попыток; remote результат остаётся queryable/UNKNOWN. Нельзя записать «не опубликовано» из-за отсутствия локального success receipt.

### 5.2 Reconciliation

`lookup(intent_key, digest, attempt_id)` проверяет current read rights и делает read-only adapter-defined lookup. Historical receipt read не требует нового write/action grant. Отдельный `record_reconciliation` сохраняет наблюдение/terminal result только с текущим reconcile/record grant, authority epoch и CAS expected attempt state; current read rights сами по себе не дают права менять локальный journal. Если grant отозван, наблюдение можно вернуть читающему, но persisted state не меняется. Возможные результаты:

| Наблюдение | Записываемый результат | Допустимый следующий шаг |
| --- | --- | --- |
| Destination вернул durable receipt **этого** key/digest/attempt | CONFIRMED_SUCCESS или CONFIRMED_REJECTION | Сохранить exact receipt; новый dispatch не требуется |
| Доказано, что попытка не исполнялась и не сможет исполниться позднее | CONFIRMED_NOT_APPLIED, terminal для старого intent | Старый intent не исполняется заново; отдельный explicit semantic request может предложить новое действие с текущими admission/preconditions после разрешения прежнего долга |
| Видны exact artifact bytes, но нет атрибуции этому intent | CONTENT_OBSERVED, attempt остаётся UNKNOWN | Можно удовлетворить отдельно определённую state observation policy; нельзя приписать собственный exactly-once effect |
| Alias/deployment generation уже другая | SUPERSEDED_OBSERVED плюс факты; old outcome может остаться UNKNOWN | Не возвращать старое значение; новый intent требует новой базы |
| Target недоступен/ответ двусмыслен/retention истёк | UNKNOWN_MAY_HAVE_RUN | Сохранить pins и reservation; без слепого resend/new-key обхода |

`retry_same_remote_intent` при ещё unresolved результате допустим лишь в отдельном доказанном destination dedup contract: тот же remote semantic ID/digest, retention ещё действует, current authority проверена; это не re-execution terminal CONFIRMED_NOT_APPLIED. У RELEASE-INTENT-0.1 нет общего автоматического retry такой попытки: default — lookup/UNKNOWN. Новый key не может сам по себе очищать старый debt.

HTTP 2xx само по себе не является точным receipt: adapter должен разобрать destination contract, verify returned content digest/target state и связать результат с intent, если заявляет execution attribution. Exact content already present может быть успешным **state convergence**, но не доказательством того, кто его опубликовал, сколько раз выполнились notifications/hooks и была ли выполнена именно эта попытка.

## 6. Что обязан гарантировать destination adapter

Guarantee profile отдельно перечисляет: immutable content put semantics, exact byte readback, stable operation identity, dedup scope/retention, receipt query, generation/CAS, fencing, authorization-at-commit, payload transformations, side effects, cancellation и observability. Список capabilities подписан/проверен против конкретной реализации и deployment configuration, а не caller boolean `cas_supported=true`.

Для immutable content upload повтор exact bytes может быть безопасен только в объявленном domain эффектов. Например, content state может быть idempotent, а notifications/billing/hooks — нет. Для mutable alias/active binding обязательна destination-enforced compare-and-set с monotonic generation и/или actual writer fencing. GET-before-PUT и mutex одного CLI не защищают от другого writer, уже отправленного запроса или split brain.

Strong content ETag полезен для content precondition, но сам по себе не различает A→B→A. Если semantics требуют обнаружить промежуточные изменения, нужен monotonic generation/transaction token. Если destination предоставляет только content CAS, профиль должен прямо ограничить наблюдения: content-equivalence condition без утверждения history freshness. Полный DEPLOY_BINDING профиль при отсутствии generation/fence недоступен; PROMOTE_ALIAS допускается только с явно заявленной более узкой семантикой, покрытой policy, либо отвергается `UNSUPPORTED_DESTINATION`.

Нельзя обещать exactly-once из local intent table. Такое утверждение допустимо только относительно exact destination effect domain и доказанного dedup/commit/receipt contract. GC ключей/receipts не может опережать unresolved attempts, remote retention и R16 closed-prefix условия. Старые generation/fence не переиспользуются после backup restore.

OCI является транспортным примером, а не обязательным backend. Digest-addressed manifests/blobs дают точные identities; mutable tags и optional conditional writes требуют отдельного adapter contract. Репозиторий может подтверждать загрузку artifact, не предоставляя deploy, health или actual runtime activation.

## 7. Deploy и ActiveBinding

DeploymentIntent содержит CandidateSealRef, immutable artifact/config refs, exact target/runtime environment, expected old ActiveBinding/generation, migration/ref если необходима, observability/health policy, authority/fence requirements и rollback strategy. `publish success` не инициирует deploy и не означает, что запущен этот digest.

Ступени:

1. **Prepare locally:** проверить artifact closure и compatibility для целевого runtime; создать plan. Если staging требует remote writes или исполнения кода в target, это уже отдельный admitted external action со своим receipt.
2. **Acquire/fence:** проверить current authority вне восстанавливаемого project store; остановить/заблокировать actual writers по R18/R19. `FENCING` не равно `FENCED_FINAL`.
3. **Commit target:** sink atomic CAS по expected generation и exact new artifact/config/environment bindings; проверить актуальную authority в commit domain. Старый delayed attempt не может затереть более новую generation.
4. **Record durable target result:** сохранить receipt/actual generation. Затем отдельная local transaction активирует соответствующий project binding; при crash между remote и local commit выполнить lookup прежнего attempt, а не новый deploy.
5. **Observe:** получить fresh target-signed/adapter-verified observation exact generation/digests и declared health checks. Desired state, published availability, committed target state, locally recorded binding и наблюдаемое здоровье — разные поля.

Health failure после commit не стирает факт deployment. При rolling/multi-target deploy каждый member имеет отдельную generation/result. Частичный успех остаётся PARTIAL; global success допустим лишь после всех policy requirements. Автоматический rollback, если заранее разрешён, является новым COMPENSATE intent со ссылкой на исходный и **текущей** expected generation. Старый binary может быть недопустим после schema migration; нужен отдельный R19 reverse/migration plan и проверка совместимости данных. Обещания «rollback всегда безопасен» нет.

## 8. Возврат наблюдений в граф bagaev

Release evidence edges связывают accepted source → exact lock → plan/result → candidate/check/seal → intent → receipt/observation. Structural edges выводятся из объектов; observed edges фиксируют, что реально произошло, с scope/time/authority. Они не заменяют authored requirements и не подменяют missing proof.

Обратный переход полезен для диагностики: отказ release-check показывает affected source/lock clauses; неожиданное поведение deployment связывается с actual binding и соответствующим source version. Наблюдение не редактирует принятую программу автоматически. Agent создаёт предложенную правку, candidate source/lock, новые проверки и отдельную acceptance transaction. Следующий выпуск снова требует admission.

Новое source/lock изменение делает зависимые claims stale по footprint; опубликованные исторические bytes/receipts остаются фактами. Перемещение mutable tag не меняет meaning старого RunRecord: он ссылается на digest/Environment/MeaningLock и actual generation, не на tag. UNKNOWN external work остаётся pinned при recovery/migration; перенос проекта не превращает его в fresh action.

## 9. Полные результаты, ограничения и отказы

`ReleaseOperationResult` содержит exact request/intent ref, local commit ref если был, attempt ID, phase, status, candidate/target refs, remote receipt/observation refs или `null`, member_results_ref для PARTIAL, bounded diagnostics и evidence scope. `null` не эквивалентно empty success. `status` выбирается из `PREPARED`, `RESERVED`, `MAY_HAVE_RUN`, `CONFIRMED_SUCCESS`, `CONFIRMED_REJECTION`, `CONFIRMED_NOT_APPLIED`, `LOCAL_REJECTED_BEFORE_DISPATCH`, `CONTENT_OBSERVED`, `UNKNOWN_MAY_HAVE_RUN`, `CANCELED_BEFORE_DISPATCH`, `STALE_BASE`, `SUPERSEDED_OBSERVED`, `PARTIAL`, `INPUT_NOT_READY`, `DENIED`, `UNSUPPORTED_DESTINATION`, `LIMIT`. Полная [phase/status matrix и transitions](../metadata/release-lock.md) определяет допустимые combinations и обязательные receipt/observation fields; произвольный JSON status не считается valid receipt. Отказ новой команды после UNKNOWN не меняет старый debt.

Limits V1: intent body≤1 MiB; ≤64 exact actions per intent (только при adapter atomicity/partial-result contract), ≤64 platform artifacts, candidate body≤8 MiB, metadata evidence inventory≤16 MiB, inline diagnostic≤64 KiB. Large artifacts только content refs. Local pending-attempt limit и remote retention задаются exact policy; исчерпание не снимается удалением UNKNOWN. uint64 generations/sequence/work counters не wrap: exhaustion требует отказа/нового authority domain по отдельному migration, не возврата к zero. Response transport bounds задаются отдельно и проверяются до mutation/dispatch; результат remote effect при недостатке локального result storage остаётся UNKNOWN с заранее reserved durable capacity.

| Причина | Требуемое поведение |
| --- | --- |
| ACCEPTED_SOURCE_MISMATCH / STALE_CHECK / LOCK_INVALID | Не строить seal/intent с подменённым evidence; новый candidate/check |
| AUTHORITY_DENIED / AUTHORITY_UNAVAILABLE | Не dispatch; недоступность не равна разрешению |
| ADAPTER_UNVERIFIED / UNSUPPORTED_DESTINATION | Не эмулировать CAS/exactly-once клиентскими обещаниями |
| KEY_CONFLICT | Не использовать тот же key для другой semantics |
| STALE_TARGET / FENCED / SUPERSEDED | Не overwrite нового target; сохранить факты старой попытки |
| CAPACITY / BUDGET | До arm атомарный отказ; после возможного remote effect сохранять reserved UNKNOWN record |
| TIMEOUT / LOST_ACK / AMBIGUOUS_REPLY | UNKNOWN, same-attempt lookup, без blind resend |
| HEALTH_FAILED / PARTIAL | Не выдавать overall success; compensation только отдельным допущенным intent |

## 10. Проверка и предел заявлений R20

[Integration route](release-lock-route.md) требует настоящие acceptance/build/package/registry/deployment adapters, независимые observed effects, crash injection между durable arm/remote commit/local receipt, concurrent writers/ABA/late requests, policy revocation в commit boundary, multi-platform inventory, activation/recovery/migration и unknown-result retention. Все реальные маршруты пока NOT_RUN. Finite model обладает explicit trusted in-memory CAS и serial transitions; он не доказывает работу произвольного OCI registry, распределённой authority, filesystem durability или полного compiler.

Исходный T18-C05 уже получил stage2 в R07. R20 проверяет связность его контракта с новым lock и последними R16–R19; число локальных tests не повышает его до stage3. T13-C02 отдельно рассматривается как кандидат stage2 относительно R07. Суммарный R15 audit отсутствует, cumulative изменение не применяется.

## 11. Первичные основания

- [OCI Distribution specification](https://github.com/opencontainers/distribution-spec/blob/main/spec.md): content digest/manifest upload и optional conditional operations. Из этого не следует универсальный CAS tags; adapter capabilities подтверждаются отдельно.
- [RFC 9110, If-Match](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.1): conditional request semantics требуют интерпретации response; equivalent already-succeeded modification может получать success response. R20 дополнительно различает exact-attempt attribution и наблюдение желаемого состояния.
- [SLSA v1.2 Build Provenance](https://slsa.dev/spec/v1.2/build-provenance): provenance связывает output, build parameters/dependencies и trusted builder. В R20 это evidence с конкретной областью; разрешение на публикацию задаётся отдельно.

Прочитано 2026-10-22 UTC. RFC/OCI/SLSA не определяют bagaev IntentBody, authority или stage accounting; соответствующие требования здесь — проектные решения.
