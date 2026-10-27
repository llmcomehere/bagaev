# Реестр V1 — читаемое представление R05 (поправки r25)

Канонический источник: [feature-ledger.json](feature-ledger.json); это представление генерирует `tools/ledger_views.py`, руками не правится. Правила и границы: [профиль](../spec/profiles/v1.md). Редакция R05 с поправками r25: D64 для F001/F002, предложения D69/D71 для P01–P03; полный пересмотр — Ф1 [плана](PLAN.md). Все будущие случаи остаются NOT_RUN для своей указанной области; строки не являются критериями процентного счётчика.

| ID | Возможность | Обязательство | Задачи / критерии | Открытое решение |
| --- | --- | --- | --- | --- |
| V1-F001 | Точный исходный срез и доступность проверок | required | T00; T00-C01, T00-C02, T00-C04 | Закрыто D64: исходная точка — чистый старт (spec/baseline.md) |
| V1-F002 | Совместимость и прежние обязательства | required | T00, T17; T00-C03, T17-C03 | Закрыто D64: прежние обязательства DROPPED, переиспользования нет (spec/compatibility-ledger.csv) |
| V1-F003 | Версионированная область V1 | required | T01, T16; T01-C01, T01-C03, T16-C01 | Закрыть все unresolved клетки; профиль пока design |
| V1-F004 | Отказы области и неизвестных форм | required | T01, T03, T18; T01-C02, T03-C05, T18-C01 | Связать коды с финальной grammar/IR и CLI transport |
| V1-F005 | Протокол проверки пользы до измерений | required | T01, T15; T01-C04, T15-C06 | Окончательный preregistered protocol, реальные сравнимые runners |
| V1-F006 | Идентичность, имена и ревизии | required | T02, T03; T02-C01, T02-C02, T03-C03 | Точный ID codec, namespaces и edit API |
| V1-F007 | Происхождение split/merge/replace/tombstone | required | T02; T02-C03 | Закрытая схема transitions и правила ручного разрешения |
| V1-F008 | Неизменяемые snapshots и внешнее evidence | required | T02, T08; T02-C04, T08-C04 | Canonical bytes/hash registry всего V1 |
| V1-F009 | Программа, исполнение и долговечные данные | required | T02, T07, T10; T02-C05, T07-C04, T10-C06 | Wire schemas и activation adapter |
| V1-F010 | Требование и реализация | required | T05, T10; T05-C04, T10-C02 | Полная логика выражения требований и перехода версии |
| V1-F011 | Лексика и полная грамматика | required | T03; T03-C01 | Закрыть grammar, escapes, comments, ambiguities |
| V1-F012 | CST, AST, typed IR и canonical encoding | required | T03, T13; T03-C01, T13-C01 | Полные схемы всех форм и checksum preimages |
| V1-F013 | Семантический roundtrip | required | T03, T14; T03-C02, T14-C02 | Полный printer, equivalence relation и corpus |
| V1-F014 | Локальная правка и сохранение текста | required | T03; T03-C03, T03-C04 | Конфликтующие ranges, invalid partial source и formatting boundary |
| V1-F015 | Unicode, неполный исходник и diagnostics | required | T03, T04; T03-C05, T04-C03 | Полный каталог diagnostics и incremental parser recovery |
| V1-F016 | Скалярные значения и арифметика | required | T04; T04-C01, T04-C03 | Полная primitive table, conversions и syntax operators |
| V1-F017 | Records, sums, collections и порядок | required | T04; T04-C01, T04-C02, T04-C03 | Comparable/key table, map constructor API, codec limits |
| V1-F018 | Номинальные ID и persistability | required | T04, T06, T07; T04-C01, T06-C05, T07-C01 | Полная таблица структурного вывода Persistable |
| V1-F019 | Параметрические типы и local inference | required | T04, T13; T04-C01, T13-C01 | Unification, generalization, recursion inference, instantiation algorithm |
| V1-F020 | Strict evaluation, ветвление и short circuit | required | T04, T06; T04-C02, T06-C02 | Полная переходная таблица и typed IR schemas |
| V1-F021 | Pattern matching и Result/Option | required | T04; T04-C01, T04-C04 | Pattern grammar, exhaustiveness algorithm, early-return lowering |
| V1-F022 | Рекурсия и лексические замыкания | required | T04, T06; T04-C04, T06-C01, T06-C05 | Типы recursive groups, closure representation и complete cost rules |
| V1-F023 | Категории исхода и неизвестный эффект | required | T04, T06, T12; T04-C02, T06-C03, T12-C03 | Все primitive/adapter mappings и RunReceipt wire schema |
| V1-F024 | Условия type safety | required | T04; T04-C05 | Полные правила, lemmas, adapters assumptions и независимая проверка |
| V1-F025 | Эффекты, bound и рекурсивная композиция | required | T04, T05; T05-C01, T04-C01 | Полный effect syntax/registry и termination argument |
| V1-F026 | Capabilities и actual authority | required | T05, T06, T13; T05-C02, T06-C05, T13-C04 | Issuance/revocation/lifetime/limits contract |
| V1-F027 | Динамические ресурсы и coverage | required | T05, T08, T09; T05-C03, T08-C03, T09-C05 | Selector algebra и extraction всех forms V1 |
| V1-F028 | Контрактные проверки и границы decidability | required | T05, T10; T05-C05, T10-C01 | Закрытые методы, budget semantics и sufficiency policy |
| V1-F029 | Reference machine и target simulation | required | T06, T13; T06-C01, T06-C02, T13-C03 | Точный state schema и transition registry всех forms |
| V1-F030 | Память, handles и cleanup | required | T06, T13; T06-C05, T13-C04 | Ownership/borrowing/close failure и implementation guards |
| V1-F031 | Бюджеты и отмена | required | T06, T09; T06-C03, T09-C03 | Полная charge table value/call/output и backend preservation |
| V1-F032 | Последовательность, внешний ввод и replay | required | T06; T06-C02, T06-C04 | Журнальная wire schema, ordering/record failure/retention |
| V1-F033 | Схемы и долговечные codecs | required | T07, T18; T07-C01, T18-C01 | Закрытые schemas и forward/backward compatibility |
| V1-F034 | Транзакции и команды с receipt | required | T07, T12; T07-C02, T07-C05, T12-C01, T12-C02 | Общий adapter contract и реальная crash/concurrency conformance |
| V1-F035 | Локальные события, inbox и ACK | required | T07; T07-C02, T07-C05 | Общий retry/poison/backlog protocol и handler upgrade |
| V1-F036 | Проекции и поисковый индекс | required | T07, T15; T07-C03, T15-C03 | Общий query consistency contract; actual data application |
| V1-F037 | Миграция подготовленного состояния | required | T07, T15; T07-C01, T15-C03 | Все crash cuts, schema codec, writer fencing и migration runner |
| V1-F038 | Активация программы, state и epoch | required | T07, T10; T07-C04, T10-C06 | Полный atomic adapter и backlog/dedup transition rules |
| V1-F039 | Crash/recovery и retention граница | required | T07, T12; T07-C05, T12-C03, T12-C05 | Общий storage protocol, bounded retention и actual process crashes |
| V1-F040 | Извлечение typed graph и двунаправленные индексы | required | T08; T08-C01, T08-C05 | Extraction table всех V1 forms и persistent incremental engine |
| V1-F041 | Происхождение фактов и evidence applicability | required | T08; T08-C02, T08-C04 | Полная claim schema и invalidation по всем входам |
| V1-F042 | Внешние gaps и замкнутый closure | required | T08, T09; T08-C03, T09-C05 | Полная closure extraction всех V1 forms |
| V1-F043 | Полный и инкрементальный пересчёт | required | T08, T09; T08-C05, T09-C04 | Persistent delta maintenance и независимый full oracle V1 |
| V1-F044 | Влияние на old/new graph | required | T09; T09-C01, T09-C05 | Transfer table для всех V1 forms/контрактов/данных |
| V1-F045 | Циклы и основания остановки | required | T09; T09-C02, T09-C04 | Полные laws и failure semantics анализаторов |
| V1-F046 | Analysis budget и frontier | required | T09, T11; T09-C03, T11-C03 | Charge policy и resumable stable traversal |
| V1-F047 | Контракт изменения и запрет скрытого ослабления | required | T10; T10-C02, T10-C06 | Полная schema, authorize transition и comparison rules |
| V1-F048 | Sufficiency и exact candidate evidence | required | T10; T10-C01, T10-C03 | Полная policy schema и proof method registry |
| V1-F049 | Атомарное принятие и его receipt | required | T10, T12; T10-C04, T12-C01 | Реальный durable service и crash implementation |
| V1-F050 | Композиция изменений | required | T10; T10-C05 | Алгоритм conflict/rebase на общем typed IR |
| V1-F051 | Поиск intent и существенная неоднозначность | required | T11; T11-C01, T11-C02 | Ranking/tie/access rules и selection protocol |
| V1-F052 | Пошаговый ContextPack | required | T11; T11-C03, T11-C04, T11-C05 | Serializer/token counting и exact readiness contract V1 |
| V1-F053 | Durable WorkState и продолжение сессии | required | T12, T15; T12-C04, T15-C02 | Actual storage/wire schema и recovery |
| V1-F054 | Versioned agent protocol | required | T12, T14; T12-C01, T12-C02, T12-C03, T14-C05 | Закрытые request/response/error schemas |
| V1-F055 | Ключи, scope и retention протокола | required | T12; T12-C05, T12-C01, T12-C02 | TTL/GC/expiry outcome общего сервиса |
| V1-F056 | Compiler pipeline и interfaces | required | T13; T13-C01 | Полная IR schema/target contracts, phase ownership |
| V1-F057 | Модули, exports и exact package locks | required | T13, T18; T13-C02, T18-C03 | Lock schema, artifact identity и resolution algorithm |
| V1-F058 | Reference target и platform contract | required | T06, T13, T18; T06-C02, T13-C01, T18-C04 | Выбор implementation language/platform/runtime adapters |
| V1-F059 | ABI/FFI и ownership граница | required | T05, T13; T13-C04, T05-C01 | Закрытый ABI и resource lifecycle всех адаптеров |
| V1-F060 | Стандартная библиотека | required | T13; T13-C05 | Сам registry ещё не перечислен; обязательный blocker |
| V1-F061 | Оптимизация и observation domain | required | T04, T06, T13; T13-C03, T04-C02, T06-C03 | Cost-preserving backend simulation и полный optimizer policy |
| V1-F062 | CLI, stdout/stderr и safe inspection | required | T14; T14-C01, T14-C05 | Полный command registry и transport error mapping |
| V1-F063 | Editor, formatter и source navigation | required | T03, T14; T14-C02, T03-C04, T14-C05 | LSP/API schemas, formatter preservation policy |
| V1-F064 | Debugger и трассы | required | T06, T14; T14-C03, T06-C04 | Breakpoint/step/inspect schemas и journal access |
| V1-F065 | Читаемое представление и обучение | required | T14; T14-C04 | Reader format, docs и проверяемые examples |
| V1-F066 | Реальный authorship pilot и отрицательный экспорт | required | T15; T15-C01, T15-C03 | Настоящий V1 runner/миграция/export, не AUTH transition model |
| V1-F067 | Измерение локальности и смены сессии | required | T15; T15-C02, T15-C04 | Actual agent workflow и instrumentation |
| V1-F068 | Сравнение A/B/C и полная стоимость | required | T01, T15; T15-C05, T15-C06, T01-C04 | Запуск трёх условий и unbiased accounting |
| V1-F069 | Замыкание спецификации и conformance | required | T16; T16-C01, T16-C02, T16-C03, T16-C06 | Все unresolved cells и междокументные противоречия |
| V1-F070 | Независимые oracles и проверки оснований | required | T16, T17; T16-C04, T17-C01 | Полный suite и независимое review каждого спорного правила |
| V1-F071 | Решение по отрицательным результатам опыта | required | T16; T16-C05 | Фактический pilot и процедура смены scope |
| V1-F072 | Передача компонентам и integration DAG | required | T17; T17-C01, T17-C02, T17-C04 | Компонентные interfaces и последовательность сборки |
| V1-F073 | Изменение спецификации в реализации | required | T17, T18; T17-C05, T18-C02 | Политика review/versioning и migration для spec artifacts |
| V1-F074 | Версии форматов и совместимость поставки | required | T18; T18-C01, T18-C02 | Полная compatibility matrix и update protocol |
| V1-F075 | Воспроизводимая сборка и происхождение | required | T18; T18-C03 | Complete packaging/reproducibility contract |
| V1-F076 | Установка, обновление и восстановление | required | T18; T18-C04 | Supported platforms, packages, rollback и bug-report rules |
| V1-F077 | Отдельный выпуск и развёртывание | required | T10, T18; T18-C05, T10-C06 | Release gates, integrity, support and deployment interface |
| V1-X01 | Распределённое исполнение и межузловая exactly-once фиксация | separate_profile | T19; T01-C02 | Привязка точки обнаружения к полной grammar/IR/CLI; для расширения — отдельный нормативный профиль. |
| V1-X02 | GPU и специальные устройства | separate_profile | T20; T01-C02 | Привязка точки обнаружения к полной grammar/IR/CLI; для расширения — отдельный нормативный профиль. |
| V1-X03 | Специальные model-call/training/streaming-exchange профили | separate_profile | T21; T01-C02 | Привязка точки обнаружения к полной grammar/IR/CLI; для расширения — отдельный нормативный профиль. |
| V1-X04 | Живое обновление исполняемого кода и state transfer | separate_profile | T19; T01-C02 | Привязка точки обнаружения к полной grammar/IR/CLI; для расширения — отдельный нормативный профиль. |
| V1-X05 | Shared mutable threads | excluded_with_diagnostic | T06; T01-C02 | Привязка точки обнаружения к полной grammar/IR/CLI; для расширения — отдельный нормативный профиль. |
| V1-X06 | Произвольная dynamic loading | excluded_with_diagnostic | T13; T01-C02 | Привязка точки обнаружения к полной grammar/IR/CLI; для расширения — отдельный нормативный профиль. |
| V1-X07 | Higher-kinded parameters и implicit ad-hoc dispatch | excluded_with_diagnostic | T04; T01-C02 | Привязка точки обнаружения к полной grammar/IR/CLI; для расширения — отдельный нормативный профиль. |
| V1-X08 | Циклический импорт пакетов | excluded_with_diagnostic | T13; T01-C02 | Привязка точки обнаружения к полной grammar/IR/CLI; для расширения — отдельный нормативный профиль. |
| V1-P01 | Плавающая точка | excluded_with_diagnostic | T01, T04; T01-C01, T04-C01, T16-C02 | Решено D71 (accepted 23.10.2026): исключить из V1 с UNSUPPORTED_FEATURE; отдельный профиль |
| V1-P02 | Большие целые | excluded_with_diagnostic | T01, T04; T01-C01, T04-C01, T16-C02 | Решено D71 (accepted 23.10.2026): исключить из V1 с UNSUPPORTED_FEATURE; отдельный профиль |
| V1-P03 | Рекурсивные пользовательские типы | required | T01, T04; T01-C01, T04-C01, T16-C02 | Решено D69 (accepted 23.10.2026): регулярные рекурсивные номинальные ADT; Eq/Key/Persistable как gfp |

## Наблюдаемые взаимодействия

| ID | Связанные позиции | Правило | Что осталось |
| --- | --- | --- | --- |
| I01 | V1-F020, V1-F025 | Неиспользуемый аргумент не теряет эффект; невзятая If-ветвь не исполняется. | Полная typed IR/cost/effect таблица; OBS/CALL только research fragment. |
| I02 | V1-F022, V1-F031 | Recursion/call depth исчерпывается по semantic rule, не по host stack. | Complete closure and recursion machine. |
| I03 | V1-F061, V1-F031 | Value/error/trace equality не подменяет budget/cancel preservation. | Cost-preserving optimization evidence. |
| I04 | V1-F023, V1-F031 | Cancel не стирает Indeterminate/committed receipt. | RunReceipt и реальный adapter lifecycle. |
| I05 | V1-F026, V1-F018 | Capability в контейнере не сериализуется; author_id не даёт edit rights. | Все persistability/authority boundary checks. |
| I06 | V1-F034, V1-F039 | Receipt lookup до stale guards, current authority перед выдачей receipt. | AUTH покрывает только фиксированный ACL и retained receipts. |
| I07 | V1-F035, V1-F036 | Поздний full snapshot не откатывает index; history outcomes могут различаться. | Общий queue/retry/poison/upgrade protocol. |
| I08 | V1-F037, V1-F038, V1-F035 | Migration учитывает writers, backlog и dedup; accept не activation. | Migration/activation runner не исполнен в R05. |
| I09 | V1-F040, V1-F044 | Удалённое ребро исчезает в новом graph, но прежний consumer остаётся в impact. | Full V1 extraction and incremental oracle. |
| I10 | V1-F046, V1-F052, V1-F053 | Context budget не удаляет obligations; неполный impact не ready. | Actual agent/session protocol conformance. |
| I11 | V1-F049, V1-F009 | Source acceptance и data activation имеют разные commits и receipts. | Durable services + activation protocol. |
| I12 | V1-F074, V1-F032 | Несовместимый journal/adapter revision не запускает external effect заново. | Версионированные codecs/replay adapters. |
| I13 | V1-F066, V1-F068 | Finite AUTH переход не засчитывается за migration/export/A-B-C измерение. | Actual pilot remains NOT_RUN. |
