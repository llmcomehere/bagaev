# AUTH-TX-0.1 — смена авторства, поисковая проекция и восстановление

Статус: **рабочий контракт R05 с проверенной конечной абстрактной моделью**. Это первая отдельно замкнутая операция контура данных авторства. Она продолжает [исходный сценарий](../architecture/05-authorship-experiment.md), использует разграничения [SEM-0.1](../language/semantic-core.md) и уточняет T07/T12. Модель начинается с подготовленного D1 / ArticleV2. Она не исполняет миграцию D0→D1, активацию кода, экспорт или A/B/C опыт.

Точные frozen records, preimages хеширования, ограничения и executable API: [API.md](../../models/r07-core/experiments/authorship-transition/API.md). Здесь определяется смысл операции и путь её будущей реализации через storage adapter. У API профиля и этой главы одна область AUTH-TX-0.1; при дальнейшем несовместимом изменении создаётся новая revision, старые результаты не переписываются.

## 1. Пользовательское действие и результат

Редактор заменяет непустой упорядоченный список авторов существующей статьи. Все PersonId должны существовать; повторов нет. Порядок является частью значения. Статья с `[Алина, Борис]` отличается от статьи с `[Борис, Алина]`, даже если множество авторов одинаково. Авторство — атрибуция, а editor ACL — отдельное право изменения.

Операция имеет три последовательные долговечные границы:

1. Записать новое авторство, исходное событие и квитанцию команды.
2. Применить событие к поисковой проекции и записать результат обработки вместе с inbox.
3. Подтвердить producer, что именно это событие имеет сохранённый результат обработки.

Между этими границами допускается явно видимое незавершённое состояние. Нельзя объявить поиск актуальным только по факту записи статьи. И нельзя объявить событие доставленным только потому, что producer попытался вызвать handler.

## 2. Идентичности и версии

| Поле | Назначение | Когда меняется |
| --- | --- | --- |
| store_id | Пространство долговечных записей | Внутри профиля фиксировано |
| article_id / PersonId | Номинальные предметные идентичности | Эта операция их не создаёт и не меняет |
| command_id + actor_id | Ключ намерения в пределах store | Назначается вызывающим для отдельной команды |
| StateVersion | Версия целого атомарного store | Каждая новая запись command receipt, processing receipt или ACK |
| article_revision | Версия упорядоченного авторства статьи | Только UPDATED, на один |
| projected article_revision | Какое авторство отражает проекция | При применении более нового full snapshot |
| logical handler_id | Устойчивая идентичность обязанности обработать событие | В этом профиле фиксирована, не равна code revision |

NOOP сохраняет receipt и увеличивает StateVersion, но не article_revision. Delivery и ACK также не создают новую ревизию статьи. Поэтому свежесть поиска проверяется по версии и ordered значению статьи, а не равенством projected version с глобальным StateVersion.

StateVersion и article_revision — положительные Int64; переполнение даёт явный VERSION_EXHAUSTED до новой фиксации. Никакого оборачивания версии и повторного использования event ID нет.

## 3. Хранимые записи и инварианты

`Article` хранит ID, article_revision, ordered author_ids и отдельные editor_ids. `ReplaceAuthorship` хранит command_id, actor_id, article_id, expected_article_version и ordered author_ids. Event содержит полный новый список авторов, article_revision, store, type/schema и causation actor+command.

CommandReceipt фиксирует полный исходный request, exact binding, UPDATED/NOOP, результирующую article_revision, event_id при UPDATE и committed_state_version. ProjectionReceipt фиксирует exact event, logical handler, APPLIED/SUPERSEDED/ALREADY_CURRENT, фактическую projected revision и исходную committed_state_version. AckReceipt связан с exact event и конкретным ProjectionReceipt.

Основные инварианты:

- Каждая UPDATED-квитанция связана с retained source event и его полным snapshot. NOOP не создаёт event.
- Для каждой проекции membership индекса точно соответствует всем её author_ids; старые membership статьи удалены, новые добавлены.
- Inbox и ProjectionReceipt существуют согласованно для `(store, logical_handler_id, event_id)`.
- ACK существует только при сохранённом matching processing receipt. Source outbox не удаляется; pending определяется отсутствием ACK.
- Exact request/event comparison сохраняется даже при наличии digest. Хеш не заменяет равенство и сам по себе не доказывает authority или происхождение произвольной внешней записи.
- Receipt неизменяем после фиксации. Прочитанная сейчас версия store находится в Observation отдельно от исторической committed_state_version.

`validate_state` проверяет структурные и ссылочные инварианты выбранной модели. Это не доказательство достижимости произвольной импортированной истории и не механизм аутентификации сетевого сообщения. Источник событий здесь — доверенный retained local outbox.

## 4. Алгоритм ReplaceAuthorship

Вход: frozen State, типизированный Request, необязательный `expected_state_version` текущей попытки. Выход: новое frozen State и Observation. Исследовательский Transition дополнительно содержит `actual_commit`, но это знание harness; caller не получает его при потере ответа.

Порядок обязателен:

```text
1. validate state/request shape
2. find article and check current editor ACL
3. find receipt by (store_id, actor_id, command_id)
   if exists:
       if exact semantic request differs: reject IDEMPOTENCY_CONFLICT
       else return unchanged receipt, without mutation
4. compare per-attempt StateVersion if supplied
5. validate nonempty/unique/existing authors
6. compare expected_article_version to current article_revision
7. build complete atomic candidate:
   equal ordered authors → NOOP receipt only
   changed ordered authors → next Article + full Event + UPDATED receipt
8. publish candidate with one StateVersion advance
9. return persisted receipt
```

`expected_state_version=None` означает версию данного frozen input в последовательной модели. В реальной реализации adapter обязан атомарно сравнить именно прочитанную StateVersion при публикации. Это не разрешение писать без защиты от конкурирующего изменения.

Полное semantic request binding включает operation/profile/schema revisions, store и все поля Request, включая actor, expected_article_version и порядок author_ids. Per-attempt StateVersion не входит в binding: она защищает конкретную попытку записи, а не переопределяет исходное намерение. Новый state guard можно получить после конфликта, сохраняя исходный command ID и exact request.

Успешный retry возвращает старый receipt до проверки уже устаревших версий. Например, команда создала revision 2, ответ потерялся, затем другая команда создала revision 3. Повтор первой команды возвращает receipt revision 2 и текущую observed StateVersion. Он не откатывает статью и не объявляет revision 2 её текущим состоянием.

Проверка текущих прав предшествует выдаче receipt. Поэтому отозванный редактор не обходит ACL через retry. Сама гонка revocation/dispatch не моделируется: ACL фиксирована в рассматриваемом state; общий контракт её линеаризации ещё требуется T05/T06.

### 4.1. Отказы и повтор

UNKNOWN_ARTICLE, PERMISSION_DENIED, EMPTY_AUTHORS, DUPLICATE_AUTHOR, UNKNOWN_PERSON, ARTICLE_CONFLICT, STATE_CONFLICT, IDEMPOTENCY_CONFLICT и VERSION_EXHAUSTED оставляют весь store прежним. Они не создают successful receipt и не резервируют key. Это осознанная граница профиля: сохранённый результат гарантирован для committed UPDATED/NOOP, а не для каждой незафиксированной попытки.

Одинаковый текущий список авторов не скрывает stale expected_article_version. Для NOOP тоже нужен актуальный business CAS. Иначе случайный повтор устаревшего намерения мог бы выглядеть как успешная команда лишь потому, что кто-то другой уже вернул значение к прежнему списку.

Неверная host-форма или превышение конечной вместимости профиля — ModelError до публикации, отдельно от предметного отказа. Все такие границы перечислены в frozen API, а не замаскированы под результат языка bagaev.

## 5. Full snapshot event и поисковая проекция

`event_id = 'ev_' + article_id + '_r' + decimal(article_revision)`. Source ID ограничен 256 Unicode scalar values; производный event ID — 512. Порядок авторов сохраняется, canonical sorting применяется только к коллекциям записей по их ключам.

Перед delivery событие сравнивается со всеми полями retained source event. Изменённый ID, store, schema/type, causation, article, revision или authors даёт EVENT_CORRUPTION. Наличие похожего payload или того же digest другого объекта не разрешает обработку.

Дальнейший алгоритм:

```text
1. validate exact local source event
2. find (store, logical_handler_id, event_id) processing receipt
   if exists: return exact historical receipt
3. check per-attempt StateVersion
4. compare event.article_revision with projection.article_revision
   newer → replace complete projection; outcome APPLIED
   older → preserve projection; outcome SUPERSEDED
   equal + equal ordered authors → ALREADY_CURRENT
   equal + different value → reject PROJECTION_VERSION_CONFLICT
5. derive index consistently from chosen projections
6. atomically publish projection + index + inbox + receipt
```

Модель пересчитывает индекс целиком из проекций. Будущий incremental adapter может обновлять membership одной статьи, только если сохраняет тот же результат и atomic boundary; преимущество производительности здесь не заявлено.

Full snapshot разрешает доставить revision 3 раньше revision 2. Обработчик сразу устанавливает revision 3, а поздняя revision 2 получает SUPERSEDED и не откатывает индекс. Для delta events такой переход через пропущенную версию был бы необоснован: там требуется другой протокол полноты. Это одна из причин выбрать полный авторский snapshot для начального контура.

Перестановка двух авторов создаёт новую projection revision, даже если поиск возвращает то же множество article IDs. Иначе watermark перестал бы подтверждать актуальность ordered представления.

Одинаковая итоговая проекция при порядках `v2→v3` и `v3→v2` не означает равенства всей истории. Receipt v2 в первом случае APPLIED, во втором SUPERSEDED. Это разные правдивые сведения о выполнении; их нельзя нормализовать до вымышленной одинаковой трассы.

## 6. ACK и критерий завершённости

Producer ACK — отдельная идемпотентная операция. Она проверяет exact source event, saved inbox и matching ProjectionReceipt, затем атомарно сохраняет AckReceipt с новой StateVersion. ACK без processing receipt даёт EVENT_NOT_PROCESSED. Старый ACK возвращается до stale guard и не создаёт второй записи.

Сбой после projection commit и до получения ответа оставляет событие pending. Повтор delivery возвращает уже сохранённый ProjectionReceipt; после этого можно выполнить ACK. Поэтому флаг доставки не опережает durable outcome.

Read-only `status` возвращает текущую StateVersion, pending event IDs, lagging article IDs и complete. Complete требует одновременно актуальной проекции каждой статьи и отсутствия pending source events. Это завершённость данной операции данных и её доставки. Она не означает соответствия всей программы требованиям, принятия нового snapshot или выполнения T15.

`search(person_id)` читает текущий индекс. Пока status сообщает lag, поиск может отражать прежнюю проекцию. Вызвавшая сторона должна учитывать этот явный контракт. Линеаризуемый read-your-write search для общего сервиса ещё требует отдельного API и не приписывается этой модели автоматически.

## 7. Потеря ответа и recovery

Для каждой новой commit boundary рассматриваются три cuts:

| Cut | Хранимое состояние | Что видит caller | Допустимый следующий шаг |
| --- | --- | --- | --- |
| none | Полностью новый state | RESULT с receipt | Продолжить по типизированному результату |
| before_commit | Полностью прежний state | UNKNOWN, receipt отсутствует | Читать receipt по исходному intent |
| after_commit_before_reply | Полностью новый state | Такой же UNKNOWN | Читать receipt по исходному intent |

Cuts не создают искусственную потерю ответа у уже найденного replay или явного rejection: новой commit boundary там нет. В реальной сети reply может потеряться и на чтении; это отдельный read availability результат, не новая mutation.

`recover_command` и `recover_event` ничего не исполняют. Exact saved receipt возвращается при успешном чтении; mismatch binding конфликтует; текущая ACL команды сохраняет силу. Отсутствующий receipt даёт ABSENT_AT_READ с observed StateVersion. Недоступность чтения даёт UNKNOWN без receipt и без версии.

ABSENT_AT_READ не доказывает, что конкурирующий writer никогда не завершится после этого чтения. Для разрешённого retry сохраняются исходные key и binding, а real adapter должен атомарно обеспечивать уникальность key. Внешний эффект с иным contract нельзя повторять на основании этого локального результата.

В профиле retained receipts/outbox/inbox/ACK не удаляются. При заполнении лимита новый commit отвергается до публикации. TTL и GC требуют отдельного versioned retention contract, включая исход позднего retry; удалять ключ и молча считать старую команду новой запрещено.

## 8. Завершение, ресурсы и требования к storage adapter

Конечный профиль ограничен 32 people/articles, 32 authors/editors в записи и 512 записями каждого журнала. Переходы используют конечные обходы этих коллекций. Программа с произвольной пользовательской рекурсией здесь не исполняется. Пределы — граница исследовательской модели, не выбранные пользовательские лимиты полного V1.

Реальный adapter должен предоставить:

1. Уникальность key и атомарную проверку StateVersion вместе с публикацией всех записей boundary.
2. Durable восстановление либо полностью старого, либо полностью нового состояния после каждого поддержанного сбоя. Проверка чистой immutable модели не устанавливает это свойство диска.
3. Чтение exact committed receipts и правильное различение unavailable/absent/committed; отсутствие слепого повторения внешнего действия.
4. Согласованное восстановление index/inbox/receipts, schema validation и сохранение source events до заявленной границы retention.
5. Политику конкурентной смены ACL, handler upgrades, poison events, backlog и миграции. В AUTH-TX-0.1 эти области намеренно не реализованы и сохраняются в V1 ledger.

Выбор СУБД и формата физического журнала ещё не сделан. Следующий adapter-level oracle должен включать действительное прерывание процесса, повторное открытие хранилища, контроль всех связей и конкурентные CAS. Набор abstract cuts не подменяет такие проверки.

## 9. Фактическая проверка R05

Источники: [engine](../../models/r07-core/experiments/authorship-transition/engine.py), независимый [oracle](../../models/r07-core/experiments/authorship-transition/oracle.py), [verifier](../../models/r07-core/experiments/authorship-transition/verify.py), [корпус](../../models/r07-core/fixtures/authorship-transition.json), полный отчёт (`r07:results/authorship-transition/report.json`).

Oracle использует самостоятельные JSON records и переходы, не импортирует implementation engine. Сравнивается весь durable state, а не только результат поиска, вместе с caller Observation и доступным harness actual_commit. Дополнительно authored expectations фиксируют ключевые значения сценариев заранее. Обе реализации исходят из одного рабочего контракта; совпадение не доказывает отсутствие общей ошибки спецификации.

Фактический результат: 25/25 именованных групп; 12 сценариев и 77 шагов; 10 групп границ; 3 выполненных неверных варианта различены. Матрица включает 8 authored snapshots, 66 допустимых пар state/action, 3 вида state guard и 3 cuts: **594/594 whole-state comparisons, 0 mismatches**. Это точный конечный набор выбранных входов, не полный перебор всех историй.

Неверные варианты: раздельная запись Article без outbox/command receipt; разрыв согласованной записи projection/inbox; принятие другого request под прежним idempotency key. Каждый реально исполнен и дал различимый результат. Число 594 не включает три независимых storage реализации и не является статистикой реальных аварий.

В отчёте явно false: bagaev execution, real durability/storage/database testing, physical crashes, concurrent interleavings, migration, hypothesis testing, universal proof, requirement satisfaction и performance benchmark. T06/T07 остаются NOT_CLOSED; T15 A/B/C — NOT_RUN. Хеши семи входных файлов сохранены и не менялись в ходе фактического прогона.

## 10. Выход к следующей итерации

AUTH-TX-0.1 даёт конкретный образец паспорта операции: точные записи, порядок проверок, atomic boundary, outcomes, limits, recovery и independent expected results. Этот образец нужно перенести на следующие обязательные компоненты, сохраняя их собственные правила.

Ближайшие незакрытые части: general data adapter, schema codec, stopped-writer migration и ActiveBinding; полная grammar/typed IR и semantic machine для рекурсии/замыканий/generics; реальный export/search pilot и A/B/C. Наличие хорошо определённой ReplaceAuthorship не закрывает их автоматически.
