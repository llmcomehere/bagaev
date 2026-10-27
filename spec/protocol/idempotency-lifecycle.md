# IDEM-LIFECYCLE-0.2 — ключи, повтор, владение и восстановление

**R16 · WORKING_DESIGN · проект общего контракта.** Предмет: жизненный цикл идемпотентной команды от допуска до удаления ответа, смена исполнителя и восстановление журнала. Основной исходный критерий — **T12-C05**: «Истечение хранения ключа имеет определённый исход, а не скрыто теряет гарантию». Связанные условия T12-C01–C04 сохраняются. Этот документ не присваивает SPEC_READY, VERIFIED или RELEASED.

Документ подготовлен как самостоятельное дополнение: точные файлы R08–R15 недоступны в текущей среде. Доступные исходные критерии и методика сохранены в `sources/baseline`. Предыдущий проект `spec/protocol/idempotency-and-resume.md` R13 известен по отчёту разговора, но его байты здесь не восстановлены. До включения в полный свод обязательна сверка редакций, идентификаторов и старых evidence. Настоящий файл не заменяет недостающую R15.

## 1. Область обещания

Для одной допущенной локальной команды сервер обеспечивает не более одной фиксации её структурного результата в авторитетном хранилище. Повтор возвращает существующую квитанцию, состояние работы либо определённый отказ. Потеря ответа, удаление payload, смена модели, смена владельца и восстановление не являются основаниями повторить команду как новую.

Обещание зависит от целостности журнала, проверенного текущего authority и атомарного storage adapter. При недостатке этих оснований сервер прекращает новые записи соответствующей области и сообщает `RECOVERY_REQUIRED`. Это определённый исход, а не обещание продолжать работу при любой потере данных.

Внешнее действие имеет отдельный `EffectIntent`. Локальная квитанция о допуске или отправке не означает исполнения на другой стороне. Конечный профиль этой итерации вообще не разрешает повторную отправку. Более широкий адаптер может разрешать её только по условиям §12; истечение локального ключа таких условий не создаёт.

Профиль относится к сервису инструментов одного проекта и его работникам. Он не добавляет распределённое исполнение языка, shared mutable threads или межузловое exactly-once в V1. Известные общие архитектурные условия взяты из [сохранённого проекта инструментов](../architecture/04-agent-tooling.md).

## 2. Идентичности, которые нельзя смешивать

| Запись | Значение и обязательные привязки |
| --- | --- |
| `ProjectId` | Постоянная идентичность проекта; имя каталога её не заменяет. |
| `NamespaceId` | Выданная сервером область намерений для конкретной работы/логического клиента. Смена пользователя с делегированием, процесса или модели не создаёт новую область автоматически. |
| `KeyRef` | `(project_id, namespace_id, generation, key)`. Составной адрес одного намерения; сам по себе не является разрешением. |
| `CommandDigest` | Хеш канонического семантического запроса с точными guards и версиями. Совпадение вычисляется сервером. |
| `CommandId` | Серверная неизменяемая идентичность принятого намерения; один `KeyRef` соответствует не более чем одному `CommandId`. |
| `RequestId` | Идентификатор конкретной доставки/трассировки; не участвует в семантическом digest. |
| `WorkerId` | Текущий исполнитель; не входит в ключ бизнес-команды. |
| `ServiceEpoch` | Монотонная эпоха текущего authority; меняется при восстановлении/перезапуске, который инвалидирует владение. Не обнуляет журнал ключей. |
| `Fence` | Монотонный номер выдачи владения конкретной работой внутри эпохи; проверяется принимающей запись стороной. |
| `WorkRef` | Идентичность работы, её ревизия и digest тела. `WorkCursor` отдельно добавляет позицию/commitment журнала. |
| `EffectIntentId` | Постоянная идентичность внешнего намерения, выделенная до возможной отправки и сохраняемая при смене ключей/исполнителей. |

`NamespaceId` никогда не переиспользуется после удаления или аварийного закрытия. Новый namespace — отдельное административное создание с явной связью с `WorkState`; он не освобождает старую работу от нерешённого эффекта. Полномочия задаются текущими grants на namespace/операцию/ресурсы. Секретность случайного ключа не заменяет проверку доступа.

Клиент сохраняет `KeyRef` и исходные канонические параметры **до первой отправки**. При потерянном ответе он повторяет эту пару. Если клиент потерял сам ключ, он использует поиск по допустимым рабочим ссылкам и `resume`; произвольный новый ключ не считается продолжением прежнего действия. Сервер не угадывает тождество намерений по одинаковым аргументам: две одинаковые операции иногда действительно нужны дважды.

## 3. Семантическая канонизация и wire-пределы

Общий envelope имеет `schema`, `request_id`, `key_ref`, `operation`, `operation_revision`, `work_ref`, `target_ref`, `policy_ref`, `arguments_ref`. Последние четыре поля — точные ссылки, включая digest; они не означают «последнюю версию». Большие параметры хранятся как неизменяемый артефакт. Его доступность и digest проверяются до допуска, а срок хранения включает время незавершённой работы и объявленную возможность аудита.

Digest вычисляется над envelope без `request_id`, транспортных таймаутов, языка отображения, credentials и WorkerId. В него входят все влияющие на результат параметры, expected revisions, схема/редакция операции, точные целевые объекты, project и namespace. Credential и текущая authority не берутся из пользовательского JSON. Хеширование не легализует несовместимую редакцию операции: сервер должен поддерживать закреплённую редакцию либо вернуть `UNSUPPORTED_OPERATION_REVISION` до нового исполнения.

Для этого контракта используется `CJ-INT-1`: UTF-8 без BOM; объекты с уникальными именами; имена сортируются по Unicode scalar value; между токенами нет пробелов; строковые значения не нормализуются по NFC/NFKC; кавычка и обратная косая черта экранируются, управляющие символы используют JSON short escapes `\b`, `\f`, `\n`, `\r`, `\t`, остальные U+0000–U+001F — `\u00xx` в нижнем регистре. Непарные surrogates запрещены. Нет floats, NaN, Infinity и неограниченных целых. Строки могут содержать Unicode; сортировка и digest не зависят от locale.

Счётчики протокола передаются десятичными строками `0|[1-9][0-9]*` в диапазоне 0…2^63−1, а положительные поколения/эпохи — 1…2^63−1. Сложение проверяет верхнюю границу **до** записи; wrap запрещён. Булево значение не является счётчиком. IDs — ASCII длиной 1…128, opaque key — 16…128 символов из `[A-Za-z0-9_-]`; SHA256 — 64 нижних hex-символа. Эти правила не устанавливают общий codec значений языка.

`page_size` — отдельный ограниченный размер страницы: JSON integer 1…256, не bool. Он не является долговечным счётчиком или частью semantic command digest. Transport schema предлагает CommandEnvelope, ResumeRequest, MaintenanceCommand, RecoveryRequest и Reply. Схема не перечисляет аргументы всех операций T12: `arguments_ref` связывает их с точной редакцией operation schema. Дополнительные точные refusals из текста, включая WORK_CONFLICT и effect-evidence errors, входят в enum Reply.code.

Входной envelope не более 2 MiB UTF-8, глубина не более 32, не более 65 536 JSON-узлов. Повтор имени поля, неизвестное поле закрытой схемы, malformed UTF-8, trailing content или превышение предела отвергаются до открытия бизнес-транзакции. Общая wire-схема дана в [lifecycle-wire.schema.json](lifecycle-wire.schema.json); реальная авторизация и истинность refs не проверяются JSON Schema.

Ответ имеет неизменяемую сохранённую квитанцию и отдельный текущий `view`. При изменении job status меняется view, а историческая квитанция не переписывается. `request_id` и redaction относятся к текущей доставке. Два повтора должны возвращать ту же семантическую квитанцию, но не обязаны иметь побайтно одинаковую транспортную оболочку. Большой результат возвращается точной ссылкой; отсутствие доступа/архивного payload отражается явно, без нового исполнения.

## 4. Состояние namespace и поколений

```text
NamespaceState = {
  project_id, namespace_id, bound_work_id,
  authority_ref, service_epoch, namespace_revision,
  issued_through, closed_through,
  active_generation?, generations,
  retention_policy_ref, recovery_barrier_ref?, journal_head
}

Generation = {
  generation, status: ACTIVE | DRAINING | RETIRED,
  opened_at, accept_until, admission_sealed,
  policy_ref, admitted_count, unresolved_count,
  retained_records_root, retirement_ref?
}
```

Инварианты: `0 ≤ closed_through ≤ issued_through`; не больше одного ACTIVE; никогда не выдавать ранее выданный generation; все номера до `closed_through` закрыты навсегда. После GC отдельные Generation records закрытого префикса можно удалить, но граница и permanent namespace retirement остаются. Поколение больше `issued_through` возвращает `KEY_NOT_ISSUED`; дырка внутри незакрытой области означает `INTEGRITY_ERROR`, а не новое поколение.

`ACTIVE → DRAINING` разрешается при rotation, deadline, административном запрете нового допуска или заполнении. Обратного перехода нет. `DRAINING → RETIRED` возможен при условиях §9. Значение deadline не является таймером удаления записей. Изменение retention policy не возвращает старое поколение в ACTIVE и не сокращает уже обещанный срок выдачи результата.

## 5. Время и параметры хранения

V1 reference policy задаёт окно нового допуска 86 400 000 ms, минимальное хранение полной терминальной квитанции 604 800 000 ms после её фиксации, длительность lease 30 000 ms с максимумом 300 000 ms, не более 64 незакрытых поколений, 4 096 незавершённых записей и 1 048 576 сохранённых записей на namespace. Это предлагаемые профильные значения, а не измерения производительности. Конкретный deployment может объявлять более строгие ресурсные ограничения до допуска. Обязательства уже принятых команд при уменьшении лимита сохраняются.

Authority предоставляет `TimeWitness(clock_epoch, lower, upper, anchor_ref)`, где реальное время находится в интервале `[lower, upper]`. При точных логических часах lower=upper. Допуск новой команды возможен только при `upper < accept_until`. Lease позволяет запись только при `upper < lease_until`; новый владелец после срока назначается при `lower ≥ old_lease_until`. На равной границе старое право уже недействительно. Пересечение интервалом границы даёт `TIME_UNCERTAIN`, а не предположение о будущем/прошлом.

После надёжно замеченного истечения `admission_sealed=true` записывается монотонно. Откат часов не снимает seal. При неизвестной clock epoch, невозможности связать время с durable authority или откате ниже сохранённого безопасного floor новые допуски/выдача владения останавливаются. Чтение известного receipt не требует часов выполнения. Ротация по явной административной команде может закрыть допуск раньше срока.

Не обещается бесконечный приём при конечном хранилище. Старое UNKNOWN может задержать закрытие всего префикса поколений. При достижении лимита сервер возвращает `ADMISSION_PAUSED`/`STORAGE_PRESSURE`; pending и unknown не вытесняются. Копирование в архив допускается только при сохранении проверяемой адресуемости, индекса и обязательств восстановления. Недоступность архива означает `ARCHIVE_UNAVAILABLE`/`RECOVERY_REQUIRED`, а не отсутствие записи.

## 6. Запись намерения, квитанции и WorkState

`OperationRecord` содержит KeyRef, CommandId, CommandDigest, pinned request/artifacts, время допуска, policy/authority refs, состояние работы, lease/fence, ссылки на admission/completion receipts, effect intents, journal position и гарантированный срок хранения. Поля идентичности неизменяемы. Состояния работы меняются только зарегистрированными переходами с журналом.

У асинхронной операции есть два факта. Сохранённая квитанция `SCHEDULED` подтверждает постановку JobId; она не утверждает успех JobId. Поздний `JobCompletionReceipt` подтверждает конкретный исход исполнения. Операции, завершающиеся за одну локальную транзакцию, могут сразу иметь terminal completion. Отдельный idempotency key команды `resume.refresh` или `reconcile` не заменяет KeyRef исходной бизнес-команды.

`WorkState` сохраняет все открытые obligations, base/candidate/contract/policy refs, pinned job inputs, pending CommandIds, EffectIntentIds, recovery gaps и позиции журнала. Восстановление нового работника использует эти записи. Текст разговора и новый ContextPack не могут удалить обязательство, повысить raw verdict или разрешить эффект.

Запрос закрепляет исходный `expected WorkRef`, который проверяется при admission. Собственная постановка pending record изменяет WorkState и создаёт **internal execution_work_guard** на получившийся post-admission WorkRef. Только guard обновляется при допустимых собственных lifecycle-переходах команды; исходный запрос и его digest остаются неизменными. Claim/renew, если они меняют WorkState, выполняют CAS по текущему internal guard и сохраняют следующий guard в той же транзакции. Чужое изменение WorkState не переименовывается в собственное и даёт WORK_CONFLICT; для простого V1 профиля даже безвредная чужая правка может консервативно потребовать новой оценки. Guard нельзя просто заменить на «последнюю ревизию». Сценарии self-admission→claim→commit и concurrent foreign edit обязательны при интеграции.

Для ацикличных хешей тело WorkState ссылается на CommandId, а не на digest mutable OperationRecord; internal guard содержит только WorkRef без hash той же новой journal entry. Journal entry затем связывает записанные body hashes и предыдущий journal hash. Выданный наружу WorkCursor собирается после commit из WorkRef и journal head. Ссылки не вычисляются как хеш объекта, содержащего собственный будущий hash.

Внешний эффект рассматривается по двум осям:

| Исполнение | Значение |
| --- | --- |
| `NOT_STARTED` | Допущенный intent; возможность отправки ещё не была выдана. |
| `MAY_HAVE_RUN` | Durable marker о возможной отправке уже есть; точный исход пока неизвестен. |
| `CONFIRMED_APPLIED` | Применение подтверждено допустимым внешним evidence. |
| `CONFIRMED_NOT_APPLIED` | Есть доказанное завершённое отсутствие исполнения, включая невозможность поздней доставки. |

Локальная cancellation/ошибка/истечение lease не переводят MAY_HAVE_RUN в CONFIRMED_NOT_APPLIED. Termination вычисления и settlement внешних эффектов независимы. Команда может завершиться, оставив effect UNKNOWN; такой record остаётся unresolved для retention/retirement. Уже подтверждённый эффект не откатывается откатом принятой спецификации или кода.

## 7. Допуск и повтор: строгий порядок

```text
submit(envelope, trusted_context):
  bound_parse_and_validate(envelope)
  authorize_current_namespace_visibility_and_receipt_read(trusted_context)
  digest := canonical_semantic_digest(envelope)
  atomic_serialized_namespace_transaction:
    recheck_current_read_authority_and_access()
    if record(key_ref) exists:
      if record.digest != digest: return IDEMPOTENCY_CONFLICT
      return stored_receipt_and_current_permitted_view(record)
    if namespace_retired OR generation <= closed_through:
      return KEY_EXPIRED
    if recovery_barrier exists: return RECOVERY_REQUIRED
    require_generation_issued_and_structurally_present()
    require authoritative_negative_lookup_from_complete_live_admission_index()
    if generation != active OR admission_sealed OR deadline_not_provably_open:
      return KEY_ADMISSION_CLOSED or TIME_UNCERTAIN
    authorize_current_operation_write()
    verify_exact_request_artifacts_and_supported_operation()
    check_current_work_target_policy_guards_and_capacity()
    bind_key_and_intent_in_authoritative_journal()
    commit_admission_record_receipt_and_required_work_update()
  return committed_receipt_and_view
```

Schema/access errors не раскрывают существование закрытого key и не создают бизнес-команду. Current receipt access проверяется и на повторах; ранее имевшийся доступ не сохраняется автоматически. При утрате права записи, но сохранении права чтения exact retry может вернуть исторический receipt; он не выполняет новую запись. Эффект отзыва права определяется точкой атомарного допуска/фиксации, не произвольным обещанием отозвать уже случившееся.

Проверка read authority до lookup устанавливает право видеть текущий record и достоверность читаемого хранилища. Она не требует сохранения старого worker lease/ServiceEpoch и не является execution guard. Старый worker может иметь право читать исторический receipt, даже если его право записи уже отозвано новой эпохой.

Отрицательный lookup — ответ авторитетного полного admission index, связанного с текущими journal/authority commitments. Это не отсутствие строки в непроверенном backup, файла в object store или значения в cache. Missing root, неполный индекс, pending reservation без классификации либо несовпадение inventory дают RECOVERY_REQUIRED/INTEGRITY_ERROR до нового допуска. Даже атомарная база не превращает произвольно утраченный целиком record в доказанно новый key; integrity/restore layer обязан удерживать эту границу.

Существующая запись ищется **до** live work/head/policy/expiry guards. Поэтому потерянный ответ после смены head не превращается в новый запуск или `STALE_WORK`. Другие параметры под сохранённым key дают `IDEMPOTENCY_CONFLICT`, даже если исходный результат был отказом. Новый semantic assessment или новая ожидаемая ревизия требуют нового намерения/key и обычных правил допуска.

После полного удаления записи сравнивать старый digest невозможно. Поэтому `KEY_EXPIRED` относится к семейству **key_conflict**, как и IDEMPOTENCY_CONFLICT, но означает запрет адреса, а не установленное неравенство параметров. Это явное согласование с T12-C02: любой запрос под закрытым отсутствующим key получает конфликт допуска; сервер не выдумывает результат сравнения удалённых bytes. Предлагаемое HTTP отображение обоих кодов — 409. `KEY_NOT_ISSUED`/`KEY_ADMISSION_CLOSED` тоже не разрешают клиенту автоматически менять key ради старого действия.

Запрос в пределах принятой команды, который до начала бизнес-изменения обнаружил stale guards, получает сохранённый terminal rejection. Отказы до допуска, например отсутствие права, лимит входа или закрытое поколение, не резервируют произвольные ключи атакующего. Эти два класса отказов явно различаются полями `admitted` и `receipt`.

## 8. Владение и атомарная локальная фиксация

Выдача lease атомарно меняет owner, увеличивает fence и записывает deadline, operation identity, WorkRef и ServiceEpoch. Действующий владелец продлевает lease только CAS по своему текущему fence/epoch и до expiry. Отозванный владелец не может продлить его позже; нужен новый grant. Force takeover требует отдельного текущего права и увеличивает fence до передачи работы.

```text
commit_local(command_id, result, owner_token, current_context):
  transaction:
    require service_epoch == authority.current_epoch
    require command pending AND no external MAY_HAVE_RUN mixed into local commit
    require owner/fence/lease exactly current and unexpired
    recheck current write grant and pinned semantic inputs
    require internal_execution_work_guard, pinned_target_revision, policy_revision
    if semantic live guard failed:
      store terminal rejection + journal + work outcome
    else:
      apply prepared local mutation
      store terminal receipt + journal + work outcome
    commit all required writes together
```

Fenced/expired owner rejection не превращает работу нового владельца в terminal failure. Он не меняет бизнес-state или receipt. Lease обеспечивает возможность передачи работы; безопасность даёт атомарная проверка fence **в точке записи**, а не предварительный запрос «ещё ли я владелец». Неавторитетный cache не принимает final writes.

Смена ServiceEpoch инвалидирует все прежние worker grants. Восстановленная старая копия не может снова выдать тот же полный token. Переполнение fence/epoch возвращает `COUNTER_EXHAUSTED` и требует административного закрытия/миграции с сохранением истории; ноль не становится следующим номером.

Публикация business mutation, изменение обязательного WorkState, terminal receipt и journal commit — одна граница. Если storage adapter не может обеспечить её в одном storage transaction, он должен предоставить проверенный recovery protocol, удерживающий частичное состояние невидимым. «Сначала изменить данные, потом когда-нибудь сохранить receipt» не соответствует контракту. Outbox для проекций допустим, но авторитетные obligations уже входят в эту транзакцию.

## 9. Rotation, retirement и garbage collection

Rotation закрывает допуск старого ACTIVE, выдаёт следующий generation и новую retention policy с receipt административного действия. У незавершённых записей старого поколения сохраняется право закончить уже допущенную работу по текущим grants/fences. Истёкшее окно допуска не является автоматической отменой.

```text
retire_next(namespace, expected_revision):
  transaction:
    require current retirement authority, exact namespace revision
    g := closed_through + 1
    require generation[g].status == DRAINING
    require no unresolved operation, unresolved effect or recovery gap in g
    require integrity of admitted inventory and dependent WorkState
    set generation[g].status = RETIRED
    set closed_through = g
    append RetirementReceipt and advance namespace revision
    commit

collect(g, expected_retirement_ref):
  transaction:
    require g <= closed_through AND exact committed RetirementReceipt
    require each collected record terminal and full promised retention elapsed
    require audit/legal/project pins and archive obligations satisfied
    delete eligible response payloads/records; keep durable retirement frontier
    record GC audit event; commit
```

Обычное retirement не перепрыгивает старое unresolved поколение. При заполнении последующих поколений действует backpressure §5. Sparse tombstone compression можно спроектировать позже отдельно; она не подразумевается словом «префикс».

Запись `closed_through` предшествует физическому удалению и должна пережить любой поддерживаемый crash/restore. Crash до commit retirement оставляет прежнее состояние и запрещает GC. Crash после retirement, но до GC оставляет читаемые квитанции. Crash после части файлового GC допустим, если authoritative deletion ledger однозначно отличает архивный ref от удалённого payload и прежний key всё равно запрещён. Отсутствующий файл ещё живой записи — INTEGRITY_ERROR/ARCHIVE_UNAVAILABLE, не KEY_EXPIRED.

Retirement не является фактом выполнения: receipt ещё может говорить «отклонено», «отменено до запуска» или «подтверждено неприменение». Его смысл — больше нет незавершённых обязательств данного поколения, все дальнейшие новые допуски туда запрещены. Статус закрытого префикса нельзя использовать как подтверждение успеха конкретной старой команды.

До GC каждый live consumer receipt, включая WorkState, получает сохранённый terminal summary и явное состояние доступности `RETAINED | ARCHIVED | EXPIRED`, либо durable pin, запрещающий удаление нужного payload. Обновление availability/deletion ledger атомарно относительно публикации удаления. Summary закрепляет CommandId, digest исходного receipt и известный terminal outcome, но не подменяет полные evidence там, где они обязательны. Неразрешённый reference никогда не превращается в «работы не было». Если связь с конкретной командой также утрачена, `KEY_EXPIRED` сообщает только запрет адреса и неизвестную доступность результата; он не придумывает terminal summary.

## 10. Административные операции и отзыв authority

Namespace allocation, rotation, retirement, policy updates, force takeover и recovery activation имеют собственные `MaintenanceIntentId`, exact expected authority/revisions и записываемые receipts. Их повтор не создаёт ещё одно поколение. Maintenance ledger не хранится в поколении, которое эта же команда собирается удалить; это отдельная authority domain с явной retention/recovery политикой. Она подчиняется тому же запрету переиспользования закрытых идентичностей.

В V1 `MaintenanceIntentId = (AuthorityId, authority_epoch, sequence)`. Отдельный control register хранит монотонные `issued_sequence`, `closed_sequence` и текущую эпоху. Клиент читает exact control head и предлагает следующую sequence вместе с digest операции и expected head. Storage primitive `append_or_lookup` атомарно либо резервирует именно этот slot, либо возвращает его прежний binding/конфликт. Потеря ответа не заставляет резервировать другую sequence. При конкуренции другой digest под занятой sequence даёт конфликт; новый осознанный intent заново читает head. Это явный slot allocation protocol, а не скрытая неидемпотентная команда выдачи idempotency key.

Slot остаётся pinned, пока операция не завершена либо не доказан окончательный ABORTED. Его terminal receipt хранится минимум тот же объявленный срок, что business receipts. Только **непрерывный terminal prefix** можно закрыть; `closed_sequence` записывается до удаления payload. Повтор закрытой отсутствующей sequence получает KEY_EXPIRED семейства key_conflict. Текущий epoch и issued/closed frontier никогда не удаляются по TTL и не сбрасываются при restore. Для 4 096 pending/1 048 576 retained maintenance slots действует backpressure без eviction. Переполнение sequence закрывает новый допуск; переход epoch с сохранением retired-epoch tombstone требует текущего authority и recovery proof.

Корнем реализации являются два линейризуемых storage primitives: `append_or_lookup(expected_head, slot, digest)` и `close_terminal_prefix(expected_head, through, inventory_root)`. Вторая запись содержит собственный immutable control receipt в новом control head и не требует создающего бесконечную рекурсию maintenance key. Exact повтор проверяется по monotonic head/prefix и сохранённому receipt либо возвращает closed-prefix conflict после его разрешённой компакции. Сами primitives и durability control register — предмет проверки storage adapter, а не пользовательские команды с флагом trusted.

Bootstrap authority разрешён только для доказанно нового ProjectId/AuthorityId: exclusive durable создание genesis и контрольного регистра. При отсутствии ранее известного authority state сервер не создаёт вместо него пустой genesis с прежними IDs. Он остаётся в RECOVERY_REQUIRED. Любая читаемая копия/новая установка с прежним project identity проходит restore protocol. Так lifecycle maintenance не заканчивается незаявленной областью, в которой TTL снова разрешает дублирование.

До commit повторно проверяется текущая авторизация. Выданный ранее RetirePlan не является разрешением выполнить retirement после отзыва права. Два competing retire/rotate сериализуются CAS по namespace revision; проигравший не получает успех для незаписанного перехода. Административный receipt сам по себе не подтверждает полноту журналов или завершение эффектов — нужны основания, закреплённые в его preconditions.

Удаление проекта/namespace сохраняет минимальный permanent tombstone в authority domain. Если система полностью удаляет и этот tombstone, она обязана сделать прежний ProjectId/NamespaceId недействительным навсегда, включая endpoint routing. Повторное создание проекта с тем же человекочитаемым именем получает новые IDs. Возврат потерянного имени не возвращает старые ключи в область допустимых команд.

## 11. Read-only resume и refresh

```text
resume(work_id, checkpoint_ref, trusted_context):
  authorize current read access
  select a consistent authoritative journal head
  verify checkpoint digest/schema/project/work binding and journal prefix
  replay records to selected head; DO NOT invoke original commands
  verify references, pending inventory and recovery barriers
  recompute applicability/boundaries for exact current targets
  preserve raw historical results, all open obligations and unknown effects
  return bounded view with exact full-state ref, head, continuation and blockers
```

Выбранная старая контрольная точка дочитывается до указанного согласованного head. Точка, не являющаяся предком текущего журнала, даёт `CHECKPOINT_DIVERGED`; дырка — `JOURNAL_GAP`; несовместимая схема — `UNSUPPORTED_CHECKPOINT`. Нельзя восстановить WorkState из короткого summary модели. Пустой список, полученный из недоступного раздела, не означает пустой журнал.

`resume` имеет read-only semantics: он не захватывает lease, не отправляет эффект, не принимает проект и не меняет сохранённые статусы. `resume.refresh` — отдельная идемпотентная запись производного состояния с актуальным правом refresh, ожидаемыми WorkRef/journal head и CAS. На конфликте не затирает новые obligations. Повтор чтения допускается в ограниченном бюджете; дальнейшее продолжение сохраняет тот же явно выбранный исторический view либо заново объявленный current head.

Обязательная оболочка ответа содержит recovery state, все классы blocker, число/корень unresolved refs, current head, retained checkpoint ref и continuation. Полная коллекция может быть пагинирована по одному immutable head; summary «нет нерешённых» разрешён только по полному admitted inventory. Бюджет ответа не закрывает обязательства. Продолжение требует текущего доступа; cursor не является capability.

Если accepted base изменился, branch work может оставаться читаемой и редактируемой по своему контракту, но acceptance получает `NEEDS_REBASE`. Прежняя оценка evidence остаётся историческим фактом; её current applicability считается отдельно. Resume не переносит candidate на новую базу автоматически.

## 12. Внешние эффекты и reconciliation

До любой возможности отправить запрос адаптер атомарно сохраняет EffectIntentId, exact target/arguments/adapter revision, стабильный remote key, связь с CommandId/WorkState и `MAY_HAVE_RUN`. Даже crash между этим commit и фактическим network send оставляет UNKNOWN: он может оказаться консервативным ложным подозрением, но не выдаёт второе разрешение на отправку.

Работник может зависнуть уже после выдачи права отправки. Локальное увеличение fence не отзывает байты в сети и не гарантирует, что удалённая сторона проверяет этот fence. Поэтому failover для MAY_HAVE_RUN запускает **сверку**, а не отправку. Поздний подтверждённый результат можно принять отдельной reconciliation-командой с текущими правами и точной привязкой; старый работник не получает право локальной финальной записи лишь из наличия ответа.

`ReconciliationEvidence` включает EffectIntentId, request/target/adapter hashes, наблюдаемое remote identity, исход, временную/логическую границу наблюдения, метод и trust binding. Проверяется актуальным адаптером; клиентская строка `not_found` или `success=true` доказательством не является. Несовпадение привязки даёт `EFFECT_EVIDENCE_MISMATCH`, неподдерживаемый метод — `UNSUPPORTED_RECONCILIATION`, противоположные допустимые результаты — `EFFECT_EVIDENCE_CONFLICT` с сохранением исходных evidence, без автоматического выбора.

Для CONFIRMED_NOT_APPLIED требуется не просто отсутствие записи в момент lookup. Основание должно также исключать позднее применение ранее отправленного запроса: например, подтверждённая необратимая отмена точного remote request вместе с закрытием его эпохи, либо контракт удалённой системы с permanent rejection для этого intent. Eventually consistent lookup, timeout или отрицательный cache этого не дают.

Общий адаптер может отдельно объявить `retry_same_remote_intent`, только если одновременно установлены: стабильный remote key и exact параметры; текущий remote dedup/fence contract; подтверждённая возможность повторить в его сроке; невозможность автоматического переназначения key; текущие полномочия и отсутствие других blocker. Если remote retention истёк, разрешение прекращается. Локальный at-most-once журнал не превращает конечный remote TTL в бесконечную гарантию. Для адаптера без такого контракта default — сверка/разрешение человеком в рамках политики, без автоматической отправки.

`CONFIRMED_NOT_APPLIED` завершает старый intent с соответствующим результатом; это не команда «выполнить теперь». Отдельное новое действие может потребоваться пользователю, но проходит новый явный semantic request и все действующие guards. Нельзя встроить его в `continue`, GC, retirement или восстановление. При MAY_HAVE_RUN смена ключа, модели или namespace не превращает прежний intent в новый; WorkState effect debt остаётся блокирующим для автоматического продолжения этого действия.

## 13. Восстановление: почему старого backup недостаточно

Есть две истории: (A) после checkpoint действие не выполнялось; (B) после checkpoint действие выполнилось, затем запись о нём утрачена. После восстановления одного и того же старого checkpoint локальные bytes могут совпадать. Алгоритм без дополнительного достоверного сведения не может различить A и B. Поэтому он не может одновременно гарантировать автоматическое продолжение в A и отсутствие повторения в B. Это ограничение информации, а не вопрос качества summary.

V1 требует `RecoveryAuthority` вне области отката выбранного backup либо явного запрета автоматического продолжения при его отсутствии. Authority хранит текущую ServiceEpoch, область назначения, admission/commit frontier или цепочку commitments, закрытые key namespaces и recovery barriers. Его собственная freshness должна быть подтверждена deployment contract; подписанный, но столь же старый файл не является текущим authority.

Recovery controller закрывает write admission **до** загрузки backup и до попытки записать RecoveryReceipt. Если затем не хватает места, недоступен authority, повреждена схема или не удалось сохранить barrier, внешний запрет остаётся. Старое сохранённое поле `READY` не разрешает заново открыть сервис. Открытие требует успешно зафиксированного полного recovery и проверки текущего epoch. Предел конечной модели, при котором protective transition возвращает LIMIT_REACHED без изменения входа, не реализует эту внешнюю границу; она обязательна для host.

Для конкретной реализации выбран следующий интерфейс:

```text
reserve_mutation(scope, intent_digest, expected_anchor) -> Reservation
record_commit(reservation, storage_commit_ref, journal_root) -> AuthorityReceipt
classify_reserved_slot(reservation, admitted_storage_proof) -> COMMITTED | ABORTED | UNKNOWN
enter_recovery(scope, expected_epoch) -> NewEpochAndBarrier
admit_recovery_manifest(manifest, current_anchor) -> RecoveryCertificate | Rejection
```

Reservation долговечно фиксируется **до** бизнес-commit или выдачи возможности внешней отправки. Если хранилище и authority являются одной неделимой restore domain с доказанным полным текущим журналом, эта запись может быть частью одной транзакции. При независимых durability domains используется подготовленная reservation; crash между ними оставляет консервативно незавершённый slot. Запись `record_commit` после локального commit связывает оба факта; отсутствие второй записи не означает отсутствие первого. Прежде чем отправлять внешний запрос, адаптер требует durable reservation и local MAY_HAVE_RUN.

Неопределённый slot не удаляется по TTL. Его ABORTED можно установить только доказательством, что соответствующий storage/effect admission не произошёл и больше не может произойти; «не найдено в старом backup» недостаточно. Это явный стоимостью хранения компромисс, а не скрытая распределённая транзакция без протокола. Реализация authority log и его crash consistency остаётся обязательным integration adapter.

## 14. RecoveryManifest и два пути

Manifest содержит scope, exact snapshot/checkpoint refs, authority anchor/epoch, ожидаемый полный набор namespace/generation inventory roots, journal range и root, все reservations и их classifications, WorkState roots, pending/effect roots, retention frontier, supported schema/adapter refs и основания проверки. Он проходит независимую проверку текущим authority; публичный caller не передаёт `complete=true` как разрешение.

### 14.1 Полное восстановление

Требуется непрерывный полный журнал **до текущего доверенного frontier**, сохранность admission inventory и всех unsettled intents, проверка committed/aborted reservations, отсутствие UNKNOWN slots вне явно сохранённых effect debts. Самосогласованность старого backup не равна полноте.

Recovery transaction устанавливает новую ServiceEpoch, сохраняет ключи/generations/closed_through и исторические receipts, инвалидирует старые leases, публикует восстановленный WorkState и RecoveryReceipt. Старый `KeyRef` по-прежнему адресует прежний record. Pending local job может получить нового владельца после проверки входов; MAY_HAVE_RUN остаётся доступным только для сверки. Authority прежней эпохи не может писать после восстановления.

### 14.2 Неполный журнал или неизвестная полнота

Scope переводится в `QUARANTINED`; допускаются чтение разрешённых исторических данных, diagnosis и административное recovery/reconciliation. Новые бизнес-записи этой области запрещены, включая новые keys, поколения и автоматически создаваемые namespaces. Нельзя восстановить только `closed_through`, забыть active-generation records и снова открыть приём.

Если известен последний выданный generation frontier, authority может выполнить **emergency burn** всего потерянного интервала. Если frontier неизвестен, permanently retired становится весь старый namespace. Burn не притворяется обычным retirement: его receipt содержит missing range, новые запреты, сохранённые/неизвестные obligation roots и обязательный recovery barrier. UNKNOWN не становится терминальным, даже когда старые адреса больше никогда не принимаются.

Снятие barrier — отдельная административная операция с точным RecoveryCertificate. Требуются полное восстановление потерянной области либо разрешение каждого gap и эффекта допустимыми основаниями, fencing старых работников, сохранность нового WorkState и проверка текущего authority. Если невозможно перечислить потерянные намерения, нельзя объявить перечень разрешённым пустым. Для затронутой области barrier остаётся. Это может ограничивать доступность до внешнего выяснения; конечный исследовательский профиль не реализует снятие такого barrier.

Старые worker tokens не получают право записывать даже по исторически правильному результату. Позднее evidence может быть импортировано как новый факт после валидации, а не как продолжение отозванной записи. Клонирование backup для чтения не создаёт новый рабочий endpoint с прежними идентичностями.

## 15. Требования к storage и authority adapters

| Интерфейс | Обязательная семантика | Независимая проверка |
| --- | --- | --- |
| `IdempotencyStore` | Unique KeyRef; exact digest binding; сериализация lookup/insert; atomic record/receipt/work/journal | Две реальные конкурентные команды; crash до/после commit; повтор после потерянного ответа |
| `WorkStore` | CAS ревизии и journal head; сохранность всех obligations/pending refs | Конкурирующий refresh; старый checkpoint; missing refs |
| `AuthorityLog` | Неоткатываемая текущая эпоха/frontier либо fail-closed; prepared reservations | Откат backup; потеря хвоста; stale signed anchor; crash между двумя durability domains |
| `Clock` | Объявленная uncertainty и epoch; монотонный admission seal | Точная граница; rollback; широкий интервал; недоступность |
| `LeaseGate` | Проверка owner/fence/epoch/expiry в точке записи | Старый worker после takeover/restore; revocation race |
| `EffectAdapter` | Durable intent до send; exact remote binding; консервативный outcome | Timeout после применения; поздний ответ; expired remote dedup; stale negative lookup |
| `RetentionStore` | Committed retirement до удаления; pins; missing live artifact не считается отсутствующей командой | Crash между retirement/GC; delete race; archive outage |
| `RecoveryVerifier` | Сверка manifest с текущим authority, а не с самим собой | Старый целый backup; неизвестный inventory; незакрытый slot |

Матрица задаёт необходимые проверки и точки интеграции. Она **не является отчётом их выполнения**. Транзакционная SQLite-проверка R13 упоминалась в предыдущем отчёте разговора; её файлы здесь недоступны, поэтому R16 не использует её как заново проверенное evidence.

## 16. Диагностики и допустимое продолжение

| Код | Что установлено | Разрешённый следующий шаг |
| --- | --- | --- |
| `IDEMPOTENCY_CONFLICT` | Сохранённый key уже связан с другим digest | Исправить ошибку выбора намерения; не переписать binding |
| `KEY_EXPIRED` | Адрес навсегда закрыт; точный ответ мог быть удалён | Читать сохранившиеся рабочие/effect refs; исход неизвестен без evidence |
| `KEY_ADMISSION_CLOSED` | Нового record здесь не было; поколение не принимает новые keys | Получить новое поколение только для явно нового допуска |
| `KEY_NOT_ISSUED` | Номер не выдавался текущей namespace authority | Исправить scope/generation, не выдумывать их |
| `PENDING` | То же принятое намерение ещё не завершено | Читать status; назначить допустимого работника отдельно |
| `EFFECT_UNKNOWN` | Возможно внешнее применение, исход не установлен | Reconciliation того же EffectIntentId |
| `STALE_OWNER` / `LEASE_EXPIRED` | Текущий sender не вправе фиксировать эту работу | Получить актуальное состояние; не terminal-fail чужую работу |
| `STALE_WORK` / `STALE_POLICY` | Новое исполнение не проходит live guards | Пересмотреть запрос; исторический exact receipt не переписывать |
| `RECOVERY_REQUIRED` | Недостаточна полнота/достоверность восстановленного state | Recovery/сверка; новые бизнес-записи блокируются |
| `JOURNAL_GAP` / `INTEGRITY_ERROR` | Нарушена целостность нужных записей | Сохранить gap и провести восстановление |
| `STORAGE_PRESSURE` / `ADMISSION_PAUSED` | Нет объявленной ёмкости для нового допуска | Дождаться разрешённой очистки/расширения; pending не вытеснять |
| `TIME_UNCERTAIN` / `COUNTER_EXHAUSTED` | Нельзя безопасно выдать временное/числовое право | Восстановить authority/мигрировать профиль; не обнулять счётчик |

Каждый ответ содержит machine code, область, exact refs и допустимые actions как данные. Actions не исполняются автоматически из текста explanation. `KEY_EXPIRED` не утверждает «выполнено», «не выполнено» или «можно повторить»: для этих выводов нужны отдельные основания.

## 17. Сценарии приёмки общего контракта

Ниже — обязательные **будущие интеграционные** сценарии; фактически выполненные finite сценарии перечисляются отдельно в report. Старые K01–K15 R13 не переименовываются и не объявляются выполненными без восстановления исходных текстов.

| ID | Воздействие | Обязательный наблюдаемый результат |
| --- | --- | --- |
| IL-01 | Ответ успешной локальной записи потерян | Exact retry возвращает прежний результат; одна business mutation |
| IL-02 | Тот же KeyRef с другим semantic request | Conflict; binding/WorkState не меняются |
| IL-03 | Изменились head/policy после успешной команды | Exact receipt читается по текущим правам до live execution guards |
| IL-04 | Доступ на чтение отозван перед replay | Нет выдачи закрытого receipt и нет нового выполнения |
| IL-05 | Deadline достигнут ровно на границе | Новый absent key не допускается; старый pending не удаляется |
| IL-06 | Lease истёк; новый worker получил fence | Старый worker не пишет; новый действует по текущим guards |
| IL-07 | Late old worker после restore | Эпоха отклоняется; исторический ответ может войти только как проверенное evidence |
| IL-08 | Rotation при pending/UNKNOWN | Старое поколение DRAINING, обязательства сохранены, retirement заблокирован |
| IL-09 | GC после committed retirement | Старый отсутствующий key даёт KEY_EXPIRED, не новое выполнение |
| IL-10 | Разные параметры после полного GC | Key conflict по expiry; сравнение удалённого digest не заявляется |
| IL-11 | Долгое UNKNOWN и предел поколений/места | Backpressure без вытеснения/пропуска старого поколения |
| IL-12 | Crash между business mutation и receipt | Один атомарный commit либо recoverable невидимый partial state; нет повторного эффекта |
| IL-13 | Crash после MAY_HAVE_RUN, до/после отправки | Оба случая консервативно UNKNOWN без автоповтора |
| IL-14 | Remote lookup временно пуст | Не превращается в CONFIRMED_NOT_APPLIED |
| IL-15 | Remote idempotency retention истёк | Retry permission отсутствует, даже если локальный key уже закрыт |
| IL-16 | Старый checkpoint и новые obligations | Resume дочитывает journal, сохраняет новые обязательства; ничего не исполняет |
| IL-17 | Refresh конкурирует с новым WorkState | CAS conflict; нет потери чужой работы |
| IL-18 | Самосогласованный, но старый backup | Полнота не принимается без текущего authority frontier |
| IL-19 | Потеря части active-generation journal | Quarantine/burn с сохранением gap, запрет новых keys/namespaces для старой работы |
| IL-20 | Authority anchor тоже неизвестно старый | RECOVERY_REQUIRED, а не новое пустое состояние |
| IL-21 | Retirement commit/GC/crash в разных порядках | Frontier переживает удаление; живой отсутствующий payload — integrity error |
| IL-22 | Rollback часов, overflow fence, malformed JSON | Нет нового допуска/записи; точная диагностика, прежнее состояние сохранно |
| IL-23 | Изменена retention policy задним числом | Уже обещанное хранение не сокращено; закрытый key не открыт |
| IL-24 | Удаление/создание namespace с тем же именем | Старые IDs не оживают; нерешённый effect debt остаётся в WorkState |

Для каждого интеграционного сценария фиксируются точные versions/source/toolchain/storage mode, первичные данные, независимый oracle, ожидаемый и фактический результат, fault schedule и область доказательства. Успешный pure transition trace не выдаётся за реальный filesystem/power-loss/remote test.

## 18. Граница исполненной модели R16

API конечной модели определяет её собственные малые JSON-состояния, операции и пределы. Она проверяет переходы generation/key/owner/outcome и conservative restore на явно допущенных trusted context/proof inputs. Целые model counters не являются wire decimal strings общего адаптера. Модель не декодирует все V1 operation arguments, не реализует authentication, storage durability, uncertainty clock, полный WorkState, реальные backup/remote endpoints или signing.

Её результаты могут обнаружить противоречие в выбранном алгоритме, но не подтверждают истинность входной recovery certificate. Проверка certificate относительно реального authority — отдельная обязанность RecoveryVerifier. В finite профиле quarantine необратим в пределах доступных operations; это честный запрет вне исследованного recovery path.

Оригинальные 96 критериев, знаменатель 384 и шкала SPEC-PROGRESS-1 сохранены. Даже полное предметное ревью этого текста даёт максимум основание для стадии **2** T12-C05. Стадия 3 требует независимых оснований по всему предмету критерия, стадия 4 — нормативной приёмки с зависимостями. Общий накопительный аудит R16 заблокирован недоступностью полного R15, а не заменён результатами этой модели.

## 19. Реализация по шагам

1. Восстановить точные R15 bytes; сверить R13 lifecycle draft, R14 explanations и R15 spec-change protocol. Сопоставить names/statuses и evidence scopes, не перезаписать pinned исторические источники.
2. Реализовать CJ-INT-1 и закрытые lifecycle wire types; проверить malformed/limit/cross-language vectors. Общие operation schemas T12 остаются отдельной задачей.
3. Реализовать durable namespace/key tables, unique constraints, WorkState CAS, receipts и журнал в одном transaction domain. Подключить текущую авторизацию в точки commit.
4. Реализовать owner/fence gate и authority clock. Затем rotation/retirement/GC с caps, retention pins и independent maintenance identities.
5. Подключить EffectIntent/outbox, запрет повторной отправки для не поддерживающего её адаптера, exact reconciliation evidence и конфликтующие результаты.
6. Реализовать read-only resume и отдельный refresh. Проверить журнал/обязательства/unknown до построения bounded ContextPack.
7. Реализовать authority reservations и RecoveryVerifier, полный restore и incomplete quarantine/burn. Подтвердить внешнюю относительно backup границу freshness.
8. Исполнить IL-01…IL-24 на реальном storage/процессах/адаптерах, сопоставить с finite oracle, пройти независимое ревью и только затем повышать stage/acceptance.

Параллельно следующий исходный предмет дорожной карты — **T18-C04**, установка/начальная настройка на чистой машине. Его design может продвигаться до восстановления R15, но обновление полного свода и накопительного реестра требует восстановления исходного комплекта.

Примечание к составу: экспериментальные пакеты R16–R23 не включены; упоминания их проверок описывают границы метода, а не результаты запуска этого пакета.
