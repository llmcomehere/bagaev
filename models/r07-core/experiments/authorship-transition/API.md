# AUTH-TX-0.1 · Точный контракт конечной машины

Исследовательская Python-модель абстрактной durable boundary. Она не использует реальную СУБД, не исполняет bagaev и не доказывает физическую атомарность, сохранность диска или конкурентный storage adapter. Начальное состояние — подготовленное **D1 / ArticleV2** из опыта авторства. Миграция, активация кода/схемы и A/B/C опыт не запускаются.

## Область и идентичности

Один store, последовательные whole-state переходы; фиксированные people и редакторские ACL. Авторство — непустой упорядоченный набор существующих PersonId без повторов. Порядок является частью значения: перестановка — UPDATE. Участие среди авторов не даёт разрешения редактировать.

`state_version` всего store — положительный Int64. Любая новая durable запись command receipt, projection/inbox или ACK увеличивает его на один. `article_revision` — отдельный положительный Int64, увеличивается только при UPDATE упорядоченного авторства. NOOP, delivery и ACK его не меняют. Freshness проекции проверяется по article_revision, не по state_version.

Все ID — непустые Unicode scalar strings без неявной нормализации. Version допускает только настоящий int, не bool. Все входные collections глубоко фиксируются в tuple; порядок semantic ID-коллекций канонизируется, а порядок авторов сохраняется. Канонический JSON различает bool/int; хеш сопровождает точное сравнение значения, а не заменяет его.

Constants: `PROFILE_REVISION='authorship-transition/r05-v1'`, `OPERATION_ID='ReplaceAuthorship/v1'`, `HANDLER_ID='authorship-index'`, `EVENT_TYPE='ArticleAuthorshipChanged'`, `EVENT_SCHEMA='AuthorshipEventV2'`. Handler ID устойчив и не зависит от code revision/epoch. Записи не удаляются; TTL, GC и смена handler отсутствуют.

## Frozen records

- `Article(article_id, article_revision, author_ids, editor_ids)`; authors ordered, editor IDs unique/canonical.
- `ReplaceAuthorship(command_id, actor_id, article_id, expected_article_version, author_ids)`; request допускает пустой/дублированный список как типизированный запрос, который операция отвергает предметной ошибкой.
- `Event(event_id, store_id, causation_id, causation_actor_id, article_id, article_revision, author_ids, event_type=EVENT_TYPE, schema_revision=EVENT_SCHEMA)` — полный новый authored snapshot.
- `CommandReceipt(store_id, request, request_binding, status, article_revision, event_id, committed_state_version)`; status `UPDATED` или `NOOP`.
- `Projection(article_id, article_revision, author_ids)`.
- `AuthorIndexEntry(person_id, article_ids)`; article IDs unique, sorted.
- `InboxEntry(handler_id, event_id, event_binding)`.
- `ProjectionReceipt(store_id, handler_id, event, event_binding, status, projected_article_revision, committed_state_version)`; status `APPLIED`, `SUPERSEDED` или `ALREADY_CURRENT`.
- `AckReceipt(store_id, handler_id, event_id, event_binding, projection_receipt_binding, committed_state_version)`.
- `DurableState(store_id, state_version, people, articles, outbox=(), command_receipts=(), projections=(), author_index=(), inbox=(), projection_receipts=(), acknowledgements=())`. Все перечисленные collections — tuples соответствующих records; people — tuple PersonId. У articles/projections ключ article_id; outbox/ack — event_id; receipt команды — actor_id+command_id; inbox/projection receipt — handler_id+event_id. Store namespace задаётся внешним store_id.

`make_initial_state(store_id, people, articles) → DurableState` создаёт version 1 с согласованной начальной проекцией и индексом, пустыми журналами. Article revisions уже заданы входом; это подготовка D1, не доказательство миграции.

`validate_state(state)` проверяет формы, ключи, ссылки, ограничения, соответствие index↔projections, source event↔command receipt, inbox↔projection receipt и ACK↔сохранённый outcome. Это проверка инвариантов модели, не криптографическая аутентификация произвольной истории.

## Durable truth отдельно от полученного ответа

`Observation(status, code, receipt=None, observed_state_version=None, replayed=False)`:

| status | Смысл |
|---|---|
| `RESULT` | Получен сохранённый receipt; code — его предметный результат или ACKNOWLEDGED |
| `REJECTED` | Получен явный отказ; новый receipt не записан |
| `UNKNOWN` | Ответ потерян или чтение недоступно; receipt и observed_state_version равны None |
| `ABSENT_AT_READ` | В этом последовательном чтении receipt отсутствовал; code=NO_RECEIPT |

`Transition(state, actual_commit, observation)` содержит новый frozen store и bool `actual_commit`: была ли **в этой попытке** новая durable запись. Это поле — truth для исследовательского harness, не знание удалённого caller. Приложение видит только observation. Replay имеет actual_commit=False.

Receipt неизменяем: `committed_state_version` — версия первоначальной записи. При повторе после дальнейших изменений возвращается тот же receipt; `observation.observed_state_version` указывает текущую версию прочитанного store. Старое article_revision в receipt не выдаётся за текущее состояние статьи.

## ReplaceAuthorship

```text
replace_authorship(state, request, *, expected_state_version=None, cut='none')
    → Transition
```

Ключ идемпотентности — `(store_id, actor_id, command_id)`. Exact binding включает fixed operation/profile/schema, store и **весь** ReplaceAuthorship, в том числе actor, expected_article_version и порядок authors. Per-attempt expected_state_version в binding не входит.

Порядок:

1. Проверить типизированную форму, целостность state, наличие статьи и **текущую** редакторскую ACL.
2. Если receipt по ключу есть: точный request возвращает прежний receipt; другой request получает IDEMPOTENCY_CONFLICT. Это происходит до stale guards.
3. Если заданный expected_state_version не совпадает, вернуть STATE_CONFLICT. None означает текущий frozen input этой последовательной модели; реальный adapter должен атомарно проверить именно прочитанную StateVersion при записи.
4. Проверить nonempty/unique/existing authors, затем business CAS expected_article_version. Конфликт — ARTICLE_CONFLICT; одинаковый список не скрывает stale expected version.
5. Если ordered authors равны текущим, атомарно записать NOOP receipt и увеличить только state_version. Event не создаётся.
6. Иначе атомарно записать Article с article_revision+1, полный Event в outbox и UPDATED receipt; state_version увеличивается один раз.

`event_id = 'ev_' + article_id + '_r' + decimal(new_article_revision)`. Это deterministic ID локальной статьи/ревизии: для `article_id='a_101'` получается `ev_a_101_r2`. Ранее illustrative fixture использовал сокращённое `ev_a101_r2`; его данные не меняются и не считаются запущенными этой моделью. Event содержит causation actor+command для однозначной связи с receipt.

Предметные отказы `UNKNOWN_ARTICLE`, `PERMISSION_DENIED`, `EMPTY_AUTHORS`, `DUPLICATE_AUTHOR`, `UNKNOWN_PERSON`, `ARTICLE_CONFLICT`, `STATE_CONFLICT`, `IDEMPOTENCY_CONFLICT`, `VERSION_EXHAUSTED` оставляют **весь** state неизменным. Неуспешная новая команда не резервирует ID. Гарантия сохранённого прежнего результата относится к committed UPDATED/NOOP receipt, а не к произвольной незафиксированной попытке.

## Projection delivery

```text
deliver_event(state, event, *, expected_state_version=None, cut='none')
    → Transition
```

Сначала проверяется точное совпадение event с retained local outbox: ID, store, schema/type, causation, article/revision и ordered authors. Неизвестное или изменённое событие получает `EVENT_CORRUPTION`, без записи и ACK. Это доверенная локальная source boundary; подписанные сообщения или внешние providers не моделируются.

Ключ inbox — `(store_id, HANDLER_ID, event_id)`. Exact completed receipt возвращается до per-attempt state guard. Затем для нового события проверяется StateVersion и версия проекции:

- Более новая article_revision: заменить projection полным snapshot; удалить прежние membership этой статьи и добавить каждого нового автора. Результат APPLIED.
- Более старая: индекс/проекция не откатываются; результат SUPERSEDED.
- Равная и одинаковое ordered значение: ALREADY_CURRENT. Равная с иным payload: `PROJECTION_VERSION_CONFLICT`, без перезаписи.

Каждый новый completed результат, включая SUPERSEDED, атомарно записывает согласованные projection/index, inbox и ProjectionReceipt и сдвигает StateVersion один раз. При одинаковом составе и новом порядке projection revision всё равно обновляется. Полный snapshot позволяет доставить v3 перед v2 без GAP; это правило не переносится на delta events.

Разные порядки доставки могут дать одинаковую конечную projection, но разные сохранённые receipt outcomes: v2 мог быть APPLIED либо SUPERSEDED. Равенство всей истории не заявляется.

## Отдельный producer ACK

```text
acknowledge_event(state, event_id, *, expected_state_version=None, cut='none')
    → Transition
```

ACK возможен только для persisted matching inbox+projection receipt этого handler. Иначе `EVENT_NOT_PROCESSED`; неизвестный event — `UNKNOWN_EVENT`. Уже сохранённый AckReceipt возвращается до stale state guard. Новый ACK атомарно добавляет AckReceipt, связанный с exact event и projection receipt, и увеличивает StateVersion. Outbox сохраняется, но событие перестаёт быть pending. Код RESULT — ACKNOWLEDGED.

Index commit не очищает producer outbox. Поэтому потеря ответа после обработки оставляет pending событие: повтор delivery вернёт receipt, после чего отдельный ACK завершит доставку. Локальная транзакция не обещает exactly-once внешнего действия.

## Crash cuts и восстановление

Для каждой новой durable mutation поддержаны `none`, `before_commit`, `after_commit_before_reply`. Cuts применяются только если достигнута новая commit boundary; rejected/replayed операции не имеют новой границы и возвращают свой обычный наблюдаемый результат.

| cut | Durable state | actual_commit | Caller observation |
|---|---|---|---|
| none | Все записи одной boundary | True | RESULT |
| before_commit | Полностью прежний | False | UNKNOWN / REPLY_LOST |
| after_commit_before_reply | Все записи одной boundary | True | UNKNOWN / REPLY_LOST |

`recover_command(state, request, *, available=True)` и `recover_event(state, event, *, available=True)` возвращают Observation и ничего не исполняют. Чтение команды сохраняет shape/current-ACL и exact-binding checks. Событие проверяется по retained source. Receipt возвращается неизменным; отсутствие — ABSENT_AT_READ с текущей observed_state_version. `available=False` возвращает UNKNOWN / READ_UNAVAILABLE без receipt и версии.

ABSENT_AT_READ не является обещанием о будущих interleavings или свидетельством отсутствия внешнего действия. В закрытой local model все успешные mutations имеют retained receipt; отсутствие records в реальной системе требует её собственного recovery protocol.

## Read-only views и ограничения

`search(state, person_id) → tuple[article_id,...]` читает индекс и возвращает sorted IDs; неизвестный person диагностируется.

`status(state) → TransitionStatus(state_version, pending_event_ids, lagging_article_ids, complete)` проверяет exact projection version+ordered authors для каждой текущей статьи и отсутствие pending outbox. Complete — завершённость данной local data/event boundary, не приёмка программы или закрытие требований T15.

## Канонизация, exact bindings и порядок records

`canonical(value)` рекурсивно преобразует dataclass во все его именованные поля, tuple/list в JSON array, dict в object. `digest(value)` — SHA-256 UTF-8 сериализации `json.dumps(canonical(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)`. Рабочая область helpers — типизированные records этого профиля и показанные ниже preimages; они не являются универсальным JSON parser. Exact сравнение сохраняется отдельно от digest.

Публичные helpers используют следующие полные preimages; дополнительных скрытых полей нет:

```text
request_binding(state, request) = digest({
  "binding": "authorship-command/r05-v1",
  "profile_revision": PROFILE_REVISION,
  "operation_id": OPERATION_ID,
  "event_schema": EVENT_SCHEMA,
  "store_id": state.store_id,
  "request": canonical(request)
})
event_binding(event) = digest({
  "binding": "authorship-event/r05-v1",
  "profile_revision": PROFILE_REVISION,
  "event": canonical(event)
})
projection_receipt_binding(receipt) = digest({
  "binding": "authorship-projection-receipt/r05-v1",
  "profile_revision": PROFILE_REVISION,
  "receipt": canonical(receipt)
})
```

People сортируются по ID; articles/projections — по article_id; outbox/acknowledgements — по event_id; command_receipts — по `(request.actor_id, request.command_id)`; author_index — по person_id; inbox — по `(handler_id, event_id)`; projection_receipts — по `(handler_id, event.event_id)`. Редакторские IDs и article IDs в index rows сортируются. Повтор ключа диагностируется, author order не сортируется.

## Диагностика и граница профиля

`ModelError(code, detail='')` — диагностика неверного host input/повреждённого state/предела профиля. Предметный отказ операции находится в Observation, а не маскируется внутренним исключением. Пределы: 32 people/articles, 32 authors/editors в одном record, 512 записей каждого журнала; исходные ID до 256 Unicode scalar values, производные event IDs до 512; signed64 versions. Таким образом детерминированный event ID помещается для каждой допустимой article ID и версии. Превышение вместимости даёт CAPACITY_LIMIT до публикации новой записи; прежние receipts/outbox/inbox сохраняются. Неизвестный cut/schema/operation или превышение профиля не получает приблизительной семантики.

`bagaev_execution=false`, `abstract_durable_model=true`, `real_storage_tested=false`, `hypothesis_tested=false`. Нет миграции, code activation, concurrency/disk testing, внешнего exactly-once или завершённого A/B/C опыта. T06/T07 не закрываются этим ограниченным результатом.
