# Глоссарий

Справочник для чтения спецификации. Определения нормативны в указанных документах; здесь — одна строка смысла и ссылка. Таблица контрактов построена из [README](README.md) и пополняется новыми документами.

## Термины

| Термин | Смысл | Где определено |
| --- | --- | --- |
| ActiveBinding | долговечная пара «код + схема данных + epoch», выбранная для среды; не равна принятому head | [architecture/02-language-runtime.md](architecture/02-language-runtime.md) |
| AcceptanceRecord | запись приёмки кандидата: снимок, свидетельства, контракт изменения, политика | [architecture/03-change-algorithms.md](architecture/03-change-algorithms.md) |
| BIR-1 | единый типизированный IR (D77); схема — Ф3 | [language/surface.md](language/surface.md) |
| boundary / граница | элемент, раскрытый в ContextPack только контрактом, с основанием | [architecture/04-agent-tooling.md](architecture/04-agent-tooling.md) |
| ChangeContract | контракт изменения: что разрешено менять, что сохранить, что добавить | [architecture/03-change-algorithms.md](architecture/03-change-algorithms.md) |
| command / query / handler | точки входа: транзакция записи / только чтение / обработка одного события | [language/effects.md](language/effects.md) |
| ContextPack | пакет контекста шага агента с бюджетом и frontier; в V1 — LNK-08-19, LNK-08-20 | [links/08-bagaev-extraction.md](links/08-bagaev-extraction.md) |
| CoverageRecord | полнота извлечения связей сущности: COMPLETE или PARTIAL с причинами | [links/01-records-and-invariants.md](links/01-records-and-invariants.md) |
| D83-сертификат | основание исключения из влияния: проверенный контракт или невлияние по типам и эффектам | [../registry/PLAN.md](../registry/PLAN.md) |
| EntityId / @id | устойчивая непрозрачная идентичность декларации; не имя, не ревизия, не хеш | [language/surface.md](language/surface.md) |
| evidence / свидетельство | неизменяемая запись о проверке; применимость оценивается отдельно | [architecture/01-program-model.md](architecture/01-program-model.md) |
| Fault | определённая языком остановка программы (переполнение, повтор ключа, провал теста) | [kernel/outcomes.md](kernel/outcomes.md) |
| frontier | то, до чего анализ или раскрытие контекста не дошли; не «нет влияния» | [links/03-impact-and-context.md](links/03-impact-and-context.md) |
| L1-TRACE / L2-OBS | уровни соответствия: точная трасса эталона / наблюдаемое поведение всех реализаций (D76) | [language/semantic-core.md](language/semantic-core.md) |
| HOST-1 | хост исполнения: SQLite, квитанции команд, доставка событий, журнал и replay, миграция, точки сбоя (r31) | [runtime/host.md](runtime/host.md) |
| MACHINE-1 | единая CEK-машина CORE ∪ DATA ∪ Perform ∪ транзакции (D77); Ф3 | [runtime/machine.md](runtime/machine.md) |
| opaque-тип | номинальный тип, конструктор и разбор которого доступны только в его модуле | [language/surface.md](language/surface.md) |
| outbox / inbox | события, зафиксированные вместе с изменением / отметки обработки событий | [language/effects.md](language/effects.md) |
| provenance | происхождение ребра: extracted (из кода), declared (написано), inferred | [links/02-extraction-and-refresh.md](links/02-extraction-and-refresh.md) |
| receipt | сохранённый исход операции, возвращаемый при повторе с тем же ключом | [runtime/host.md](runtime/host.md) |
| ряд эффектов (row) | множество атомов reads/writes/emits/host плюс не более одной эффект-переменной | [language/effects.md](language/effects.md) |
| snapshot | неизменяемый манифест версии программы; свидетельства хранятся снаружи | [architecture/01-program-model.md](architecture/01-program-model.md) |
| StateVersion | версия атомарного состояния хранилища; не версия отдельной записи | [language/semantic-core.md](language/semantic-core.md) |
| TOP / unknown | «влияние не установлено»; неизвестное не считается независимостью | [links/01-records-and-invariants.md](links/01-records-and-invariants.md) |
| union(old, new) graph | анализ влияния по объединению старого и нового графа, чтобы не терять удалённые связи | [architecture/03-change-algorithms.md](architecture/03-change-algorithms.md) |
| UseSummary | описание того, какие свойства данных использует потребитель | [links/01-records-and-invariants.md](links/01-records-and-invariants.md) |
| WorkState | полное состояние работы вне разговора: входы хранятся, обязательства и готовность пересчитываются (CHG-13) | [protocol/agent-protocol.md](protocol/agent-protocol.md) |
| метод правила | тест, чей применимый PASS закрывает обязательство правила: неизменённый тест базы с `checks` или тест, названный условием контракта; выбывший тест базы — только через `replace_test` (CHG-13) | [protocol/agent-protocol.md](protocol/agent-protocol.md) |

## Идентификаторы контрактов

| ID | Предмет | Документ |
| --- | --- | --- |
| `LEX-1` | Лексика исходника | [language/lexical.md](language/lexical.md) |
| `GRAMMAR-1` | Грамматика | [language/grammar.ebnf](language/grammar.ebnf) |
| `SURFACE-1` | Поверхностный язык и отображение в BIR-1 | [language/surface.md](language/surface.md) |
| `EFFECTS-1` | Эффекты, ряды, точки входа | [language/effects.md](language/effects.md) |
| `KERNEL-CANON-1` | Канонический JSON BAG-CJSON-1, ссылки, наблюдаемое значение | [kernel/canonical.md](kernel/canonical.md) |
| `KERNEL-OUTCOMES-1` | Единый словарь исходов и статусов | [kernel/outcomes.md](kernel/outcomes.md) |
| `DIAG-1` | Единый реестр кодов диагностик | [diagnostics/README.md](diagnostics/README.md) |
| `BAG-CJSON-1` | Профиль канонического JSON | [kernel/canonical.md](kernel/canonical.md) |
| `EXEC-1` | Нормативные правила → случаи `conformance/` (EXEC-1) | [conformance-manifest.json](conformance-manifest.json) |
| `DATA-TYPES-0.1` | DATA-TYPES-0.1 — неизменяемые данные V1 | [language/data-values.md](language/data-values.md) |
| `ERR-0.1` | ERR-0.1 — фазы отказа и значения ошибок | [language/errors.md](language/errors.md) |
| `SEM-0.1` | SEM-0.1 — общий семантический контракт V1 | [language/semantic-core.md](language/semantic-core.md) |
| `TYPES-0.1` | TYPES-0.1 — проверка типов и локальный вывод | [language/types.md](language/types.md) |
| `DATA-IR-0.1` | DATA-IR-0.1 — формы данных и соединение с CORE | [ir/data-forms.md](ir/data-forms.md) |
| `IR-CORE-0.1` | IR-CORE-0.1 — закрытое ядро и граница полного IR | [ir/typed-core.md](ir/typed-core.md) |
| `MACHINE-CORE-0.1` | MACHINE-CORE-0.1 — шаг, окружение и остановка | [runtime/core-machine.md](runtime/core-machine.md) |
| `DATA-WORK-0.1` | DATA-WORK-0.1 — возобновляемые операции над данными | [runtime/data-work.md](runtime/data-work.md) |
| `AUTH-TX-0.1` | AUTH-TX-0.1 — смена авторства, поисковая проекция и восстановление | [data/authorship-transition.md](data/authorship-transition.md) |
| `AUTH-DATA-0.1` | AUTH-DATA-0.1 — чистые данные авторства и обратный индекс | [data/authorship-values.md](data/authorship-values.md) |
| `CODEC-0.1` | CODEC-0.1 — точное представление неизменяемых данных | [data/value-codec.md](data/value-codec.md) |
| `LNK-0.2` | LNK-0.2 · Записи, свойства и инварианты | [links/01-records-and-invariants.md](links/01-records-and-invariants.md) |
| `OBS-0.1` | LNK-0.2 · Исполнимый исследовательский профиль OBS-0.1 | [links/05-executable-profile.md](links/05-executable-profile.md) |
| `LNK-0.3` | LNK-0.3 · Проверяемые законы уточнения зависимостей | [links/06-law-checking.md](links/06-law-checking.md) |
| `CHANGE-1` | изменение, приёмка и протокол агента (r34) | [protocol/agent-protocol.md](protocol/agent-protocol.md) |
| `LINKS-1` | извлечение графа, влияние и ContextPack bagaev (r33) | [links/08-bagaev-extraction.md](links/08-bagaev-extraction.md) |
| `LNK-0.4` | ТЗ на поддерживаемые связи bagaev · LNK-0.4 | [links/README.md](links/README.md) |
| `IDEM-LIFECYCLE-0.2` | IDEM-LIFECYCLE-0.2 — ключи, повтор, владение и восстановление | [protocol/idempotency-lifecycle.md](protocol/idempotency-lifecycle.md) |
| `RECOVERY-ROUTE-0.1` | RECOVERY-ROUTE-0.1 — маршрут проверки восстановления проекта | [distribution/recovery-route.md](distribution/recovery-route.md) |
| `RECOVERY-SET-0.1` | RECOVERY-SET-0.1 — восстановление проекта из объявленных входов | [distribution/recovery-set.md](distribution/recovery-set.md) |
| `COMPATIBILITY-ROUTE-0.1` | COMPATIBILITY-ROUTE-0.1 — интеграционная проверка T18-C01/C02 | [distribution/compatibility-route.md](distribution/compatibility-route.md) |
| `VERSION-BINDING-0.1` | VERSION-BINDING-0.1 — версии, совместимость и смысл программы | [distribution/compatibility.md](distribution/compatibility.md) |
| `MIGRATION-PLAN-0.1` | MIGRATION-PLAN-0.1 — явный переход проекта между версиями | [distribution/migration.md](distribution/migration.md) |
| `RELEASE-INTENT-0.1` | RELEASE-INTENT-0.1 — выпуск из точных входов и отдельное внешнее действие | [distribution/release.md](distribution/release.md) |
| `DEPENDENCY-LOCK-0.1` | DEPENDENCY-LOCK-0.1 — точный граф входов сборки | [toolchain/dependency-lock.md](toolchain/dependency-lock.md) |
| `DIAGNOSTIC-PIPE-0.1` | DIAGNOSTIC-PIPE-0.1 — ошибки, координаты и исправления | [toolchain/diagnostics.md](toolchain/diagnostics.md) |
| `CACHE-PIPE-0.1` | CACHE-PIPE-0.1 и ORIGIN-PIPE-0.1 | [toolchain/incremental-origin.md](toolchain/incremental-origin.md) |
| `ORIGIN-PIPE-0.1` | CACHE-PIPE-0.1 и ORIGIN-PIPE-0.1 | [toolchain/incremental-origin.md](toolchain/incremental-origin.md) |
| `PIPELINE-0.1` | PIPELINE-0.1 — контракт конвейера компилятора | [toolchain/pipeline.md](toolchain/pipeline.md) |
| `OPT-RULES-0.1` | OPT-RULES-0.1 · конкретный каталог преобразований | [toolchain/optimization-rules.md](toolchain/optimization-rules.md) |
| `P5-OPT-0.1` | P5-OPT-0.1 · точное включение в R21 | [toolchain/pipeline-bridge.md](toolchain/pipeline-bridge.md) |
| `PRESERVE-CHECK-0.1` | PRESERVE-CHECK-0.1 · проверка и применение | [toolchain/preservation-checking.md](toolchain/preservation-checking.md) |
| `PRESERVE-0.1` | PRESERVE-0.1 · сохранение наблюдаемого исполнения | [toolchain/preservation.md](toolchain/preservation.md) |
| `FFI-TOOLCHAIN-0.1` | FFI-TOOLCHAIN-0.1 — связь с компилятором и загрузчиком | [toolchain/ffi-bridge.md](toolchain/ffi-bridge.md) |
| `CALL-FFI-0.1` | CALL-FFI-0.1 — эффекты, вызовы и обратные вызовы | [ffi/calls-effects-callbacks.md](ffi/calls-effects-callbacks.md) |
| `CODEC-FFI-0.1` | CODEC-FFI-0.1 — точная машина обхода и стоимости | [ffi/codec-machine.md](ffi/codec-machine.md) |
| `FFI-BOUNDARY-0.1` | FFI-BOUNDARY-0.1 — явная граница внешнего кода | [ffi/contract.md](ffi/contract.md) |
| `ADAPTER-FFI-0.1` | ADAPTER-FFI-0.1 — native shim и допуск платформы | [ffi/isolation-adapters.md](ffi/isolation-adapters.md) |
| `OWN-FFI-0.1` | OWN-FFI-0.1 — владение и прекращение доступа | [ffi/ownership-lifecycle.md](ffi/ownership-lifecycle.md) |
| `WIRE-FFI-0.1` | WIRE-FFI-0.1 — переносимые значения и кадры | [ffi/wire-abi.md](ffi/wire-abi.md) |
| `STDLIB-API-0.1` | STDLIB-API-0.1 — закрытый каталог библиотеки | [stdlib/api.md](stdlib/api.md) |
| `STD-RESOLVE-0.1` | STD-RESOLVE-0.1 — замкнутый каталог и двунаправленные зависимости | [stdlib/resolution.md](stdlib/resolution.md) |
| `STD-SERVICE-1` | STD-SERVICE-1 — хранилище и события в программе (D81); заменяет STD-SERVICE-0.1 | [stdlib/services.md](stdlib/services.md) |
| `STDLIB-TYPES-0.1` | STDLIB-TYPES-0.1 — типы, ошибки и владение | [stdlib/types.md](stdlib/types.md) |
| `STDLIB-WORK-0.1` | STDLIB-WORK-0.1 — порядок, стоимость и продолжения | [stdlib/work.md](stdlib/work.md) |

## Метрики трека

| ID | Смысл | Где |
| --- | --- | --- |
| SPEC-PROGRESS-1 | проработка ТЗ: 96 критериев × 4 балла | [../registry/PROGRESS_METHOD.md](../docs/verification.md) |
| EXEC-1 | исполнимое соответствие: покрытие правил независимыми случаями | [../registry/EXEC_METHOD.md](../registry/EXEC_METHOD.md) |
