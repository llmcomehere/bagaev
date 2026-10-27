# RECOVERY-SET-0.1 — восстановление проекта из объявленных входов

**R18 · WORKING_DESIGN · проект общего контракта для T18-C03.** Исходный критерий: «Проект восстанавливается из объявленного комплекта входов». Этот документ охватывает проект V1, его среду, данные, обязательства и историю полномочий. Конечная исследовательская модель проверяет только отдельные правила; фактическое восстановление V1 ещё не выполнено.

Это самостоятельное дополнение к R16 и R17. Точные байты полного свода R15 недоступны; существующие правила нельзя считать заменёнными без сверки. Компактная основа языка сохранена без изменений. Зависимости T01/T03/T06–T14 могут оставаться открытыми для проекта контракта; их фактическая готовность обязательна для приёмки.

## 1. Результат, который заказывает пользователь

Операция принимает точную цель. Она не подменяет её более слабым успехом.

| Цель | Достаточный результат | Чего результат не разрешает |
| --- | --- | --- |
| INSPECT_SNAPSHOT | Проверенный исторический снимок на точном срезе H; доступ только для чтения | Продолжение прежних команд, выдачу полномочий, признание снимка текущим |
| REPRODUCE_PROGRAM | Восстановлены исходники, точная семантика, toolchain/packages, конфигурация и объявленные входные данные; выполнен заданный проверочный маршрут | Автоматический запуск с эффектами, продолжение старой истории полномочий |
| RESUME_AUTHORITY | Полное состояние до зафиксированного текущего frontier, сохранённые долги, новая эпоха и согласованная активация | Автоповтор UNKNOWN, принятие исходника, публикацию или развёртывание |

INSPECT_SNAPSHOT не требует сетевой проверки нынешнего authority, но требует доверенного происхождения исторического capture certificate. Если доступны только некоторые файлы, результат — PARTIAL_INSPECTION с точным перечнем пробелов. Он не получает статус полного снимка. Для REPRODUCE_PROGRAM наличие всех входов позволяет получить PROGRAM_INPUTS_READY; итог PROGRAM_REPRODUCED появляется только после реальных decode/check/build и сверки независимого ожидаемого результата. Проверка хешей не подменяет этот шаг.

RESUME_AUTHORITY допускает известные незавершённые задачи и известные UNKNOWN-эффекты: они остаются долгами и блокируют соответствующее действие. Отсутствующий реестр таких долгов — неизвестная полнота истории, поэтому весь затронутый scope остаётся QUARANTINED. Готовность authority и готовность каждой задачи к выполнению — отдельные состояния.

Импорт исходников под новым ProjectId — отдельная операция SOURCE_FORK. Она сохраняет lineage и ссылки на старые долги, создаёт working head и открытые обязательства проверки. Она не продолжает старые ключи и не объявляет старые внешние действия отменёнными. Автоматического перехода от неудачного RESUME_AUTHORITY к SOURCE_FORK нет.

## 2. Идентичности и границы доверия

| Поле | Смысл |
| --- | --- |
| ProjectId / LineageId | Постоянная идентичность проекта и точная ветвь истории; имя каталога их не заменяет |
| RecoveryProfileRef | Доверенный контракт форматов, обязательных ролей, извлечения ссылок и пределов |
| RecoverySetId | Хеш канонического ManifestBody; не подпись, не свидетельство полноты или свежести |
| CheckpointRef / C | Проверенный снимок единого состояния и номер последнего включённого события |
| TargetCut / H | Точный последний включённый номер и хеш события; H ≥ C |
| EnvironmentRef | Неизменяемая среда R17, связанная с исходником и семантическими профилями |
| ObligationCommitment | Полный корень обязательств, ключей, prepared reservations и неопределённых эффектов |
| RecoveryAttemptId | Идемпотентный maintenance intent R16, связанный с точным намерением восстановления |
| AuthorityId / ServiceEpoch | Текущий источник полномочий и монотонная эпоха; backup не выбирает новую эпоху |
| CandidateRef | Неизменяемое подготовленное состояние вместе со всеми связанными входами и корнями |
| RecoveryReceipt | Исторический результат конкретной попытки; сам по себе не выдаёт текущих прав |

Отдельны три области: архивные данные, локальный восстановленный проект и действующий control store authority. Восстановление первых двух не заменяет третий. Deployment contract обязан назвать источник текущего anchor вне области отката выбранного backup, его freshness, fencing и сохранность tombstones. Архивная копия самого authority может быть материалом для диагностики, но не текущим control store.

Доверие к профилю/codec/историческому capture certificate устанавливается вне архива. Манифест не может сам назначить себе доверенного издателя, разрешить неизвестный decoder или снять отзыв ключа. Для исторического исследования допустима явно указанная историческая trust policy; для подключения к действующей системе применяются текущие права и policy. Неизвестное происхождение даёт UNTRUSTED_INPUT.

## 3. Что именно входит в RecoverySet

RecoveryProfile содержит обязательный список ролей, а также точные registry refs для всех декодеров. Для каждой роли ManifestBody содержит ровно одну запись. Отсутствующая запись — ROLE_MISSING, а не пустой набор.

| Роль | Канонический предмет и условие |
| --- | --- |
| identity | ProjectId, LineageId, история происхождения, исходный epoch и authority scope |
| source | Все достижимые версии исходников, working/accepted heads, pending changes; accepted head может быть явно null |
| semantics | Версии source grammar, typed IR, value codec, effect/verification profiles и reducers |
| environment | EnvironmentLock, release/toolchain/runtime/target, точные packages и transitively pinned зависимости |
| configuration | Настройки компиляции/запуска, feature flags, declared inputs, кодировки, locale/time assumptions |
| data | Канонические значения и пользовательские данные, требуемые выбранной целью; для физического backend — полный согласованный snapshot profile |
| relations | Канонические сущности/связи требований, спецификаций, кода и evidence; отдельно версия построения обратных индексов |
| work | WorkState, открытые obligations, pending changes, verification requests, причины блокировок и оставшиеся semantic budgets |
| admission | Namespace/generation inventory, active bindings, closed prefixes, tombstones, receipts и адресуемость удалённого payload |
| effects | Полный effect ledger: intent, target, request digest, remote key, MAY_HAVE_RUN/UNKNOWN и evidence |
| jobs | Задачи и continuations, checkpoint refs, входные версии, consumed budgets и разрешённый способ продолжения |
| evidence | Исторические результаты с subject/method/environment refs и статусами применимости |
| journal | CheckpointHeader, точный хвост C+1..H, event codecs и финальные roots |
| capture | Barrier/participant certificates, обязательства на C и H, reservation classifications и publication seal inputs |
| bindings | Объявленные внешние подключения: authority, секреты/ключи расшифровки, remote services, platform capabilities |

Четыре состояния роли:

- INCLUDED: один или несколько точных корней присутствуют и замыкание достижимых объектов проверено.
- EMPTY_BY_CONTRACT: запись содержит EmptyWitnessRef; decoder профиля подтверждает конкретное разрешённое условие пустоты. Например, evidence пуст при отсутствии исторических результатов; admission не становится пустым только потому, что ни одного файла не нашлось.
- EXTERNAL_REQUIRED: точное внешнее обязательство с adapter contract, identity, разрешённой операцией чтения/получения и текущим BindingWitness. Это не ссылка «возьми последнюю версию».
- UNAVAILABLE: роль известна, но материал отсутствует. Полная цель, которой она нужна, блокируется; diagnosis может продолжиться.

Матрица RequiredRoles(target, decoded state) задаётся профилем, а не заявителем. В базовом профиле INSPECT_SNAPSHOT требует все авторитетные исторические роли, кроме исполнения environment binaries и действующего bindings: для них достаточно точных описателей, если запрос не требует чтения зашифрованного содержимого. Для REPRODUCE_PROGRAM обязательны source/semantics/environment/configuration/data и их транзитивные refs; остальные роли остаются явно перечисленными и не дают права продолжать историю. Для RESUME_AUTHORITY необходимы все исторические роли и разрешённые текущие bindings. Пустые jobs/effects допустимы только по проверенному пустому корню на C и H.

Невключённая необязательная для выбранной цели роль не скрывается: результат содержит coverage vector по всем 15 ролям. Добавление нового типа обязательств требует новой версии RecoveryProfile с новыми обязательными extractors. Unknown extension, который может нести состояние/эффекты, блокирует полный успех, даже если формально проходит JSON Schema.

## 4. Канонизация, пределы и граф хешей

Metadata использует **RecoveryJSON-1**: UTF-8 без BOM, только объекты/массивы/строки/boolean/null; числовые величины записаны строками. Duplicate keys, lone surrogates, неизвестные обязательные поля и нестрогое UTF-8 запрещены. Значения счётчиков — десятичные строки без знака и ведущих нулей, диапазон 0..18446744073709551615. Строки не нормализуются: байты исходника не меняются по правилам Unicode.

Canonical encode: рекурсивно сортировать ключи объекта по Unicode scalar value; массивы сохранять по порядку, кроме явно объявленных множеств, которые заранее сортируются по уникальному id. Строки выводить UTF-8; кавычку и backslash экранировать; U+0000..U+001F всегда как lowercase \u00xx; остальные scalar values не экранировать. Пробелов и завершающего newline нет. Не полагаться на произвольные defaults JSON-библиотеки. Profile decoder проверяет canonical bytes, а не только повторно сериализованное значение.

Хеш описателя: SHA-256(domain || NUL || canonical_body). Domain — точная ASCII строка типа и версии. Binary blobs адресуются SHA-256(raw bytes); тип/байтовая длина/decoder ref находятся в ObjectRef. Совпадение хеша — предположение криптографической целостности; оно не доказывает происхождение и правильность программы. RecoverySetId хеширует только ManifestBody. CompletionSeal ссылается на RecoverySetId; подпись/provenance — отдельный envelope, не часть собственного subject. Цикла «manifest включает подпись своего же хеша» нет. Поле CompletionSeal.durability_receipt_ref ссылается на PreSealDurabilityReceipt: подтверждение долговечного наличия exact ManifestBody и chunks, связанное с RecoverySetId, backend/profile и inventory. Этот receipt создаётся до seal и не содержит SealRef или post-publication index receipt. Квитанция окончательной публикации с SealRef хранится отдельно после seal. Таким образом seal не хеширует квитанцию, которая хеширует его самого.

Базовый лимит профиля: manifest ≤8 MiB; descriptor ≤1 MiB; один chunk ≤64 MiB; до 1 048 576 объектов; до 1 048 576 records в одном journal segment; depth metadata ≤64; строка metadata ≤16 384 UTF-8 bytes; до 4096 participant/binding entries; incremental bases ≤64 и глубина bases ≤32. Общий declared plaintext size ≤1 TiB. Лимиты относятся к объявленному профилю, это не измеренные performance guarantees. Больший проект требует нового профиля, а не молчаливого усечения.

Счётчики и размеры проверяются до выделения памяти; превышение суммарного лимита — INPUT_LIMIT. Потоковая обработка не превращает неполную страницу в полный inventory: требуется final page/root/count. Cancellation оставляет CLOSED/QUARANTINED и доступный resume token. Все множества уникальны по ключу; дубли и разные bytes под одним ObjectRef отвергаются.

## 5. Проверка полноты и входных зависимостей

Профиль предоставляет для каждого object kind доверенные pure decode/validate/extract_refs. Пользовательский plugin не запускается ради разбора архива. Извлечённые ссылки имеют класс REQUIRED, REBUILDABLE_DERIVED, HISTORICAL_OPTIONAL или EXTERNAL_BINDING; класс устанавливает decoder, а не поле произвольного объекта.

~~~text
validate_closure(manifest, trusted_profile, requested_target):
    require exact supported profile and all 15 role entries
    require strict canonical metadata, unique object IDs and bounded counts
    roots = required_roots(profile, target, role witnesses)
    queue = sorted(roots); visited = empty
    while queue not empty:
        ref = pop_min(queue)
        if ref in visited: continue
        require exact bytes/hash/length/kind/decoder for ref
        value = trusted_decode(ref); validate(value)
        require object project/lineage/format bindings where specified
        for edge in extract_refs(value):
            require allowed edge class for this kind and target
            REQUIRED -> enqueue exact ref
            REBUILDABLE_DERIVED -> record deterministic rebuild obligation
            HISTORICAL_OPTIONAL -> record coverage or missing payload reason
            EXTERNAL_BINDING -> record typed binding requirement
        visited.add(ref)
    require independent role/cardinality/root commitments agree
    require every declared object either visited or declared inert attachment
    return closure certificate and exact unresolved requirements
~~~

Объектные графы могут содержать циклы через идентификаторы сущностей: visited делает обход конечным. Самореферентный content hash запрещён; циклы представляются стабильными entity IDs внутри канонического graph object, чьи edges проверяются после загрузки всех nodes. Граф incremental bases ацикличен. Base разрешается только по точному RecoverySetId и CompletionSeal; совпадающее имя проекта недостаточно. Для overlay одинаковый object id обязан иметь одинаковые bytes; удаление authority state отдельной tombstone/event, а не отсутствие chunk.

Список manifest — средство доставки, но независимый checkpoint/capture commitment определяет ожидаемые roots/counts. Без исходного полного state root и доверенного capture процесса невозможно отличить «до C долгов не было» от «их выкинули перед упаковкой». Тогда допустима только ограниченная инспекция с пометкой UNPROVEN_CAPTURE_COMPLETENESS. Это сознательная граница доверия, а не обещание восстановить неизвестные отсутствующие сведения.

Для внешних входов BindingWitness получен host adapter через текущую авторизацию и связан с exact identity/version/operation/scope. Caller field available=true недопустим. Источник может быть локальным offline bundle; сеть не обязательна, когда все необходимые bytes и доверенные свидетельства уже есть. Отсутствующий secret/decryption key диагностируется до заявления о полноте данных. Archive path не используется как произвольный write path; safe extraction наследует R17: нет traversal, symlinks/hardlinks/devices, case collisions, path aliases и исполнения hooks.

## 6. Checkpoint и непрерывный журнал

CheckpointHeader содержит project/lineage, checkpoint sequence C, last_event_hash, StateRoot, SourceRoot, WorkRoot, AdmissionRoot, EffectRoot, JobRoot, RelationRoot, EvidenceRoot, ObligationCommitment, EnvironmentRef, profile/reducer refs и participant inventory. Эти поля образуют CheckpointBody, который не содержит CaptureCertificateRef. CaptureCertificate ссылается на CheckpointBodyRef; отдельный CheckpointEnvelope содержит body_ref и capture_certificate_ref. ManifestBody ссылается на envelope и certificate. Все корни связаны одним согласованным срезом; обратной ссылки из body на certificate нет.

StateRoot хеширует только каноническое semantic payload: значения, source/Work/admission/effect/job/relation/evidence roots и receipt bodies. Он исключает собственный StateRoot, текущий journal head, event hash, enclosing commit/capture envelopes и указатель на свой checkpoint. ReceiptBody содержит command/result/subject refs, но не хеш enclosing event; связь receipt ↔ journal вынесена в CommitEnvelope. Поэтому after_state_root вычисляется до хеша JournalRecord, а CheckpointBody отдельно связывает StateRoot с last_event_hash. CaptureCertificate не включает RecoverySetId; manifest → certificate → checkpoint body → semantic roots — ациклическая зависимость хешей.

ObligationCommitment — хеш типизированного списка с counts и roots для открытых Work obligations, pending commands, UNKNOWN/MAY_HAVE_RUN effects, suspended jobs, prepared authority slots, незавершённых launches R17 и retained pins. Closed prefixes/retired namespaces входят в AdmissionRoot. Необходимы и положительные записи о долгах, и свидетельство полноты inventory. Воспроизведение только хвоста не обнаруживает долг, потерянный до C.

JournalRecord содержит exact sequence, previous_event_hash, project, lineage, reducer_ref, command/transaction ref, reservation ref, payload ref, before_state_root и after_state_root. Локальный state change, WorkState, journal append и receipt фиксируются в одном project-store transaction согласно R16. Если authority расположен отдельно, его prepared reservation предшествует этому transaction, а record_commit может следовать после него; промежуток остаётся явно незавершённым.

~~~text
replay(C, checkpoint, records, H):
    state = decode_and_validate(checkpoint)
    require checkpoint roots and completeness certificate agree
    seq = C; prev = checkpoint.last_event_hash
    for record in records:
        require record.sequence == seq + 1 and record.previous_event_hash == prev
        require same project/lineage and exact reducer/profile
        require before_state_root == digest(state)
        state = pure_reduce(state, record.payload)  # no dispatch, no host capabilities
        require after_state_root == digest(state)
        seq += 1; prev = digest(record)
    require seq == H and prev == target.last_event_hash
    require all final roots == target commitments
    require cross_invariants(state)
    return inert candidate
~~~

C=H требует ровно пустой tail и совпадения checkpoint/target hashes. Gap, duplicate, reordered event, чужая lineage, неизвестный reducer или лишний record за H — отказ. Для segment ranges проверяются endpoints, count, chain и отсутствие перекрытия. «Взять наиболее свежий доступный record» запрещено. Разные ветви журнала не склеиваются сортировкой номеров.

Pure reducer применяет зафиксированные события, а не заново вызывает исходные команды. Event о намерении внешней отправки восстанавливает ledger; он не отправляет запрос. Event с historical verification PASS восстанавливает факт проверки точного subject, а не принимает нынешний working head. Непроверенный reducer старой версии не заменяется «похожим новым».

## 7. Создание восстанавливаемого комплекта

Выбран первый полный capture profile: **SERIALIZED-CUT-1**. Project store имеет один сериализованный stream, транзакционный checkpoint и immutable object store. Это конкретный профиль, не обещание произвольного snapshot всех файлов.

1. Через maintenance protocol R16 зарезервировать CaptureIntentId и semantic digest. Зафиксировать capture pins на checkpoint, журнал, obligations/receipts, environment/packages и достижимые immutable objects. Ошибка pin запрещает успешное завершение.
2. В project store получить coherent checkpoint C вместе с roots и полным inventory, используя доказанный snapshot API backend. Файлы живой базы нельзя просто копировать последовательно. CaptureCertificate связывает фактическую snapshot revision и durable checkpoint.
3. Запросить coordinated capture barrier. Закрыть новые admissions для scope. Довести локальные транзакции до известного завершения. Для каждого независимого participant (authority, IdentityRoot, install-store launch pins, effect adapter) получить точный revision/inventory, удерживаемый до связывания с cut.
4. Каждый потенциально отправленный внешний запрос обязан иметь durable reservation и MAY_HAVE_RUN marker до пересечения dispatch boundary. Запрос, который ушёл до barrier и может завершиться после него, включается как известный неопределённый долг. Barrier не обещает отменить remote effect.
5. Установить точный H как номер последнего committed события project stream. Отдельный participant/reservation vector перечисляет все slots, которые могли породить запись/dispatch к barrier; номера slots не прибавляются к H. COMMITTED ссылаются на полный journal event; ABORTED имеют доказательство невозможности commit/dispatch; effect UNKNOWN имеет полный retained intent/ledger. Неклассифицированная local commit reservation — CAPTURE_INCOMPLETE.
6. Выдать BarrierCertificate с participant vector и roots на H. После долговечной фиксации сертификата новые события получают номера за H. Immutable participant snapshots и pins позволяют копировать bytes позже, без удержания глобального простоя на весь upload.
7. Собрать manifest, независимо проверить closure, replay C..H и финальные commitments. Сначала сделать durable chunks и ManifestBody, затем CompletionSeal, затем атомарно опубликовать seal/index. Неполный upload не считается SEALED. Прекращение процесса не должно оставить «готовую» ссылку на недописанные bytes.
8. После подтверждённой публикации допустимо снять capture pins через отдельный terminal transition. Если ответ publication потерян, lookup того же CaptureIntentId; неизвестное состояние не освобождает pins по TTL. Retention готового RecoverySet и его incremental bases объявляется отдельно.

Участники не обязаны иметь одинаковые счётчики. Certificate содержит точные соответствующие revisions и correlation refs: например, LaunchIntentId в project store ↔ ExecutionPin в install store. Статус PENDING допустим при полном сохранении обеих сторон. Без такого соответствия получается перечень несогласованных копий, а не RecoverySet.

Продолжающаяся работа после H делает архив историческим, но не повреждённым. Архив не обязан останавливать проект навсегда, поэтому RESUME_AUTHORITY всегда заново получает финальный текущий frontier. Для filesystem/DB backend контракты durability, backup API, fsync и crash consistency — отдельные обязательные adapter evidence. SERIALIZED-CUT-1 сам их не доказывает.

## 8. Предварительная проверка и восстановление без полномочий

Host закрывает write/dispatch gate **нового изолированного recovery endpoint до чтения backup**. INSPECT_SNAPSHOT и REPRODUCE_PROGRAM сами по себе не закрывают работу живого проекта; его admissions/fences меняются только явно выбранным capture/RESUME протоколом. Присутствующее в backup поле READY ничего не меняет. Gate не открывается при ошибке записи diagnostic/barrier, нехватке диска или недоступном authority.

Изолированная staging area не видна обычным process launchers. В ней проходят trust/format/closure проверки, replay и cross-invariants. Секреты не печатаются; diagnostic указывает binding id и требуемое действие без secret bytes. Ни download hook, ни migration, ни decoder из недоверенного архива не исполняются.

Для INSPECT_SNAPSHOT публикуется readonly view с exact set/cut/coverage. Для REPRODUCE_PROGRAM stage materialization связывает среду R17, конфигурацию, package closure и declared inputs; check/build/run выполняются только согласно отдельной явно допущенной verification procedure. Если маршрут требует запуск без эффектов, host enforce-ит этот профиль. Результат фиксирует expected и actual outputs, budgets, exact compiler/runtime and artifact refs. Несовпадение — REPRODUCTION_MISMATCH, а не автоматически новая «правильная» сборка.

Все полученные значения остаются инертными до отдельного текущего допуска. Недоступные host handles, sockets, worker tokens и capability grants не сериализуются как восстановленные действующие полномочия. Разрешения и trust floors сегодняшней установки не понижаются из-за старого снимка.

## 9. Продолжение прежнего authority: точный протокол

### 9.1 Контракт адаптера

RecoveryAuthority предоставляет linearizable append-or-lookup для maintenance attempts, текущий anchor, переход к FENCING, получение подтверждённого FenceCertificate, frozen frontier и условный commit. Deployment обязан обеспечить fencing в фактической точке storage commit и dispatch admission. Проверка только в клиенте до записи недостаточна.

FenceCertificate перечисляет все writers/participants и основание прекращения старых прав. Допустимы: атомарно изменённый storage guard, проверяемый в той же транзакции, либо истёкшие grants с доказанным временем и запретом новых выдач. Неответивший worker не считается остановленным. Запрос, уже пересёкший remote dispatch boundary, остаётся UNKNOWN в ledger; local fencing его не отменяет.

Authority phase FENCING запрещает новые admissions, но ещё не утверждает, что завершились ранее разрешённые local commits. Только после fence proofs и классификации всех prepared slots устанавливается FENCED_FINAL. Если participant потерян и нельзя установить commit outcome, scope остаётся QUARANTINED; нельзя выбрать удобный меньший H.

### 9.2 Последовательность

~~~text
restore_authority(intent):
    close_host_gates()
    validate_historical_set_and_replay_into_staging()
    require current authorization and exact immutable attempt binding
    durably record local attempt and preliminary candidate

    reservation = authority.enter_recovery(attempt, expected_current_anchor)
    # CAS fails if anchor changed; same attempt is looked up, not reallocated
    establish_actual_fences(reservation)
    final = authority.freeze_final_frontier(reservation, participant_proofs)
    # complete all local slots or retain fully known external UNKNOWN debt

    require candidate lineage is an ancestor of final and candidate.H <= final.H
    require candidate event hash at H matches final's authenticated chain
    suffix = obtain_exact_catchup(candidate.H + 1 .. final.H)
    candidate = replay_and_revalidate_to(final)
    require full obligation/inventory equality and current bindings
    durably persist candidate, objects, pins, PREPARED record
    proof = {attempt, final_anchor, final_frontier, candidate_ref, all_roots}

    authority_receipt = authority.commit_recovery(proof)  # conditional durable CAS
    # binds fresh epoch and exact candidate; response loss => lookup same attempt
    durably activate_local(candidate_ref, authority_receipt)  # separate local transaction
    require authority still authorizes this epoch/candidate and host bindings
    open_eligible_gates()
    return exact RecoveryReceipt and per-job/effect restrictions
~~~

Поле expected_current_anchor предотвращает гонку старой проверки с новыми событиями. При изменившемся anchor до reservation — CURRENT_FRONTIER_CHANGED и новая предварительная проверка в рамках определённого retry intent; semantic request нельзя незаметно заменить. После FENCED_FINAL ordinary writers закрыты. Controller reconciliation может добавлять классификационные control records: они включаются в frozen proof. Любое изменение предмета proof инвалидирует PREPARED и требует нового candidate subrevision, сохраняя тот же исходный attempt и отдельную историю.

ServiceEpoch выделяется текущим authority монотонно; старая эпоха навсегда теряет write/dispatch права. Переполнение sequence/epoch — AUTHORITY_LIMIT, а не wraparound. Tombstones, closed prefixes, maintenance issued/closed frontier и противооткатные trust floors не восстанавливаются меньшими значениями из архива.

CandidateRef включает конечный set+catchup digest, final frontier, source/environment/obligation roots, RecoveryProfileRef, полный decoder/reducer registry digest, closure certificate, derivation outputs и bindings contract refs. Неизменяемые зависимости принадлежат одному pinned profile; последующая проверка не может заменить их смысл и сохранить прежний candidate digest. Secret material в digest не включается; включаются witness identity/scope/validity constraints. Активация не может переключить source snapshot или EnvironmentRef между prepare и commit.

### 9.3 Два durability domains и потерянный ответ

| Место остановки | Состояние после перезапуска | Разрешённое действие |
| --- | --- | --- |
| До authority reservation | Host CLOSED, staging может существовать | Повторить validation; старое authority ещё требует текущей проверки |
| В FENCING | Новые admissions закрыты; не все старые commits классифицированы | Продолжить fencing/classification того же attempt |
| После FENCED_FINAL, до PREPARED | Scope без writer, frontier закреплён | Достроить exact candidate; не возвращать старую эпоху |
| После PREPARED, до authority commit | Candidate durable, writer закрыт | Проверить тот же reservation/proof и CAS; не менять bytes на месте |
| Authority commit выполнен, ответ потерян | Outcome локально неизвестен | Lookup того же RecoveryAttemptId; не выделять новую эпоху вслепую |
| Authority commit выполнен, local activate не выполнен | Новая эпоха связана с candidate; обычного writer ещё нет | Довести локальную активацию того же candidate; сохранить CLOSED до проверки |
| Local activate выполнен, ответ потерян | Receipt и active pointer согласованы | Вернуть прежний receipt после current read authorization |
| Старый receipt после другой recovery | Исторический результат существует | Вернуть его как исторический; не переоткрывать старую эпоху |

Локальная активация — transaction: active candidate pointer, epoch, attempt, local recovery receipt и activation status. Нужные bytes и pins durable до transaction. Receipt authority и local receipt имеют разные виды и явно связаны; отсутствие local receipt не означает отсутствие authority commit.

Если durable candidate утрачен после authority commit, восстановить можно только его exact content из удерживаемых refs. Иначе scope остаётся CLOSED; новый recovery attempt допустим только через текущий authority с монотонным fencing и сохранением прежней истории. Отмена не откатывает ServiceEpoch и не оживляет старых workers.

Каждый новый business commit и dispatch всё равно проверяет текущую epoch/candidate grant в настоящей точке записи. Поэтому старый процесс с local active pointer не становится writer после следующего восстановления. Открытый локальный gate — необходимое, но недостаточное условие.

## 10. Обязательные связи внутри языка

### 10.1 Требования, исходники и двунаправленная связь

Relations — канонический граф с постоянными entity IDs, точными version refs и типизированными edges. Forward edge хранится один раз как источник истины. Reverse index — производная структура. После восстановления:

1. Декодировать все nodes/edges и проверить разрешённые типы, существование endpoints и version bindings.
2. Построить reverse index по объявленному алгоритму: сортировка по target entity/version, edge kind, source entity/version, edge id; уникальность edge id обязательна.
3. Сверить index digest/count с объявленным DerivedIndexContract, если он сохранён. Если кэш отсутствовал, вычислить новый и записать отдельный rebuild receipt.
4. Проверить симметрию наблюдения: каждый канонический edge появляется в соответствующем reverse query, и reverse query не создаёт новых canonical edges.
5. Dangling edge или неизвестный relation kind блокирует полный graph recovery; связь не удаляется автоматически.

Таким образом потеря обратного индекса не означает потерю двунаправленной связи, если полный канонический граф сохранён. Потеря канонического edge не компенсируется угадыванием из текста или старым UI cache.

### 10.2 Исходник, evidence и принятие

Working head, accepted head и pending candidate не объединяются. Историческое PASS относится к exact subject/profile/environment/method и остаётся историческим. Текущая applicability вычисляется заново по действующим правилам зависимостей. Новая версия compiler или другой source digest может сделать evidence неприменимым, но не переписать прошлое. Восстановление не выдаёт SPEC_READY, VERIFIED, RELEASED и не публикует проект.

Текущий ObservationCursor содержит ProjectId, ServiceEpoch, sequence и query-profile ref. После смены ServiceEpoch прежний cursor получает RESET_REQUIRED; клиент заново читает разрешённый полный snapshot и строит свой cache. Historical snapshot cursor относится к immutable RecoverySetId и не превращается в live cursor. Старые worker sessions, leases и process handles инвалидируются независимо от сохранённых historical receipts.

### 10.3 WorkState, ключи и эффекты

Cross-invariants требуют: каждый незавершённый command имеет Work obligation; каждый MAY_HAVE_RUN/UNKNOWN имеет retained intent и точный scope/target/request/remote-key binding; ни один key ниже closed prefix не допускается заново; удалённый payload различается с missing retained object; prepared authority slot связан с классификацией и нужным storage/effect record. Забытый receipt может быть восстановим по declared archive ref, но недоступный archive не означает нового key.

Внешний UNKNOWN остаётся отдельным reconciliation work item. Продолжение допускает read-only query состояния remote operation, когда adapter contract это позволяет. Новый write требует отдельного явного intent и всех текущих guards; timeout, восстановление, новое имя модели и истечение retention не разрешают автоматическую повторную отправку.

## 11. Jobs, данные и внешние подключения

Для каждой jobs-записи фиксируются JobId, input/version refs, kind, status, consumed/remaining semantic budgets, состояние PRNG для чистого детерминированного вычисления по профилю и continuation mode:

| Mode | Допустимое восстановление |
| --- | --- |
| RESTARTABLE_PURE | Новый owner может начать заново только по явному scheduler rule и сохранённому budget accounting; effects запрещены |
| CHECKPOINT_CONTINUATION | Нужны exact runtime/checkpoint codec и валидные continuation roots; stack bytes неизвестной версии не принимаются |
| EXTERNAL_PENDING | Восстанавливается ожидание/reconciliation; запуск исходного эффекта запрещён |
| TERMINAL | Исторический result/receipt; execution не возобновляется |

Недоступный runtime checkpoint не превращает задачу в новую: она получает SUSPENDED_RESTART_REQUIRED и остаётся обязательством. Возможность восстановить authority не даёт права назвать каждую задачу resumed. Потраченный budget не обнуляется из-за перезапуска, включая повтор чистой работы. Если точное безопасное budget accounting утрачено, задача блокируется.

Генераторы identity, capability grants, nonce/key uniqueness и иных служебных полномочий не относятся к восстанавливаемому чистому PRNG: они используют текущий authority domain/эпоху и не откатываются вместе с программой. Если значение участвует в обоих назначениях, профиль должен разделить эти состояния до поддержки recovery.

Время, случайность, locale, environment variables и прочие входы, влияющие на смысл, перечисляются в configuration/data contracts. Для воспроизведения нужны их сохранённые значения либо точный recorded-input stream. Для новой работы допустим новый input, но это отдельное выполнение. Нельзя обещать byte-identical output, если исходный профиль содержит недетерминизм без записи входов.

Secrets и encryption keys обычно хранятся вне архива. RecoverySet объявляет exact binding identity и разрешённый resolver; материализация выполняется через текущие полномочия host. Authority grants, identity allocator, platform/network permissions и endpoints не восстанавливаются доверенными только по строкам из backup. Если оригинальный remote resource исчез, это BINDING_UNAVAILABLE, а не разрешение отправить прежнее действие другому ресурсу.

## 12. Совместимость и миграция

Сначала читается старый exact формат по поддерживаемому decoder. Отдельный MigrationPlan перечисляет old/new profile refs, преобразование каждого авторитетного role, mapping entity/key identities, сохранение obligations/closed prefixes и expected semantic relations. До его независимой проверки результат остаётся candidate. Миграция не выполняется как побочный эффект открытия архива.

При byte-preserving restore версии не меняются. При semantic migration новый digest ожидаем; проверяется заявленная relation эквивалентности, а не совпадение файлов. Неподдерживаемый формат даёт FORMAT_UNSUPPORTED с exact required decoder ref. Обновлённый compiler не может читать старый IR иначе без отдельного решения.

Если целевая платформа отличается, profile обязан разрешать переносимый typed state или объявить невозможность continuation. Образ VM/контейнера сам по себе не доказывает восстановимость секретов, authority и внешних обязательств. В V1 не обещается произвольная миграция работающего процесса между CPU/OS.

## 13. Результат и диагностика

RecoveryResult содержит request target, achieved capability, set/candidate/cut refs, profile/environment refs, coverage vector всех ролей, exact roots/counts, unresolved debts, bindings status, attempt/authority/local receipt refs, независимые verification refs и limits. Полные ledger payload можно вынести в адресуемый object; выдача счётчика без доступного полного перечня не достаточна для снятия barrier.

| Код | Причина | Допустимое продолжение |
| --- | --- | --- |
| ROLE_MISSING / CLOSURE_GAP | Нет необходимой роли или достижимого объекта | Получить exact input; ограниченная диагностика |
| UNPROVEN_CAPTURE_COMPLETENESS | Нет основания полноты snapshot inventory | Только ограниченная инспекция; не authority resume |
| JOURNAL_GAP / JOURNAL_FORK | Неверный диапазон/цепочка/lineage | Найти точную историю, не подбирать ближайшую |
| STATE_ROOT_MISMATCH / OBLIGATION_MISMATCH | Replay/roots/долги расходятся | Оставить CLOSED, сохранить evidence |
| CURRENT_FRONTIER_CHANGED | Предварительная validation устарела | Новый current-anchor check и catchup до frozen frontier |
| FENCE_INCOMPLETE / RESERVATION_UNKNOWN | Старые записи ещё возможны или local outcome неизвестен | Завершить fencing/classification; не разрешать записи |
| AUTHORITY_UNAVAILABLE / STALE_AUTHORITY | Нет доказуемо текущего control source | Историческая инспекция; resume закрыт |
| BINDING_UNAVAILABLE / FORMAT_UNSUPPORTED | Нет внешнего входа/точного decoder | Предоставить exact binding или отдельный MigrationPlan |
| ATTEMPT_CONFLICT / CANDIDATE_CHANGED | Повтор имеет другой смысл/bytes | Не перезаписывать binding; отдельное осознанное намерение |
| REPRODUCTION_MISMATCH | Реальная проверка/сборка не совпала с expected | Диагностика, без PROGRAM_REPRODUCED |
| INPUT_LIMIT / AUTHORITY_LIMIT / STORAGE_PRESSURE | Превышен профиль/счётчик/нет места | Backpressure; никакого eviction pending/unknown |

Diagnostic сообщает field/object/range, ожидаемую identity и допустимое следующее действие. Он не содержит secret material. Permission denial предшествует чтению исторической квитанции; current write guards применяются после lookup исторического результата и не меняют его смысл. Восстановление receipt не предоставляет новых прав.

## 14. Независимая проверка и реализация

Полный маршрут и будущие RI-01..RI-24 находятся в [recovery-route.md](recovery-route.md). Их статус NOT_RUN до появления настоящих adapters, runtime, полного проекта и отдельного expected fixture. [RecoverySet schema](recovery-set.schema.json) проверяет форму envelope; она не исполняет closure, replay, криптографию, current authority или смысл V1.

Конечная модель имеет собственный малый профиль, инертные trusted context и атомарные JSON-переходы. Её сценарии и semantic mutants проверяют только изложенный finite API. Actual filesystem/crash durability, source grammar, runtime, signatures, реальный network dispatch и все 15 production roles требуют будущих интеграционных evidence.

Порядок реализации:

1. Зафиксировать decoder/role registry, canonical encoder, object store и role/closure verifier с потоковыми лимитами.
2. Реализовать consistent checkpoint, journal replay и invariant checker; отдельно подтвердить backend snapshot/commit durability.
3. Реализовать capture pins, participant barrier, obligation commitments и completion publication.
4. Материализовать исторический readonly view, exact program environment и независимый reproduce route.
5. Реализовать authority maintenance attempts, действительные fences, frozen frontier, catchup и двуххранилищную активацию.
6. Подключить relation index rebuild, WorkState/jobs/effect reconciliation и текущие bindings.
7. Выполнить весь RI-маршрут на реальном проекте, crash injection в обеих durability domains и независимое сравнение.
8. Только затем пересматривать stage 3; нормативная приёмка требует dependencies и evidence по SPEC-PROGRESS-1.

Следующее самостоятельное решение T18 — матрица совместимости и миграций по всем форматам (C01/C02). R18 задаёт обязательные recovery границы для этой матрицы, но не присваивает чужим критериям баллы.

Примечание к составу: экспериментальные пакеты R16–R23 не включены; упоминания их проверок описывают границы метода, а не результаты запуска этого пакета.
