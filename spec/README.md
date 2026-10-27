# Спецификация bagaev

Текущее дерево технических контрактов V1 и исследовательских расширений. Эталонный интерпретатор находится в `ref/`; наличие документа само по себе не подтверждает реализацию или выполнение критерия.

Начните с [основы](foundation.md), [границы реализации](baseline.md) и [краткого руководства по языку](language/guide-llm.md). Нормативные формы языка заданы в [лексике](language/lexical.md), [грамматике](language/grammar.ebnf) и [конструкциях](language/surface.md). Термины собраны в [глоссарии](glossary.md).

Проверки описаны в [руководстве](../docs/verification.md); исполнимые правила связаны со случаями через [conformance-manifest.json](conformance-manifest.json). Метки R07–R24 обозначают поколения исследовательских профилей. В `models/` включены входы R07, необходимые текущим проверкам; пакеты R16–R23 в состав не входят. Эти метки не являются Git-тегами публичного пакета.

Расширения, отмеченные как замороженные вне V1, не входят в текущий runtime. Статус `WORKING_DESIGN` означает рабочий проект контракта. Изменять документ следует вместе с его потребителями и независимыми проверками.

## Основа

| Документ | Содержание | Статус |
| --- | --- | --- |
| [foundation.md](foundation.md) | bagaev: язык связанной программы | каноническая основа |
| [baseline.md](baseline.md) | Граница реализации и профилей | принято |
| [conformance-manifest.json](conformance-manifest.json) | Нормативные правила → случаи `conformance/` (EXEC-1) | машиночитаемый реестр правил |

## Архитектура (R07)

| Документ | Содержание | Статус |
| --- | --- | --- |
| [architecture/01-program-model.md](architecture/01-program-model.md) | Модель программы: идентичность, связи и основания | база R07 |
| [architecture/02-language-runtime.md](architecture/02-language-runtime.md) | 02. Язык, исполнение и границы V1 | база R07 |
| [architecture/03-change-algorithms.md](architecture/03-change-algorithms.md) | Алгоритмы изменения и действительности знания | база R07 |
| [architecture/04-agent-tooling.md](architecture/04-agent-tooling.md) | Инструменты, агентный протокол и продолжение работы | база R07 |
| [architecture/05-authorship-experiment.md](architecture/05-authorship-experiment.md) | 05. Первый опыт: один автор → несколько | база R07 |
| [architecture/06-specification-completeness.md](architecture/06-specification-completeness.md) | Полнота спецификации и передача в реализацию | база R07 |
| [architecture/07-decisions.md](architecture/07-decisions.md) | Архитектурные контракты и предложения | база R07 |

## Язык

| Документ | Содержание | Статус |
| --- | --- | --- |
| [language/guide-llm.md](language/guide-llm.md) | Шпаргалка: весь язык за ~2,5k токенов, с перечнем std (ненормативно) | рабочая |
| [language/lexical.md](language/lexical.md) | LEX-1 — лексика исходника | контракт V1 |
| [language/grammar.ebnf](language/grammar.ebnf) | GRAMMAR-1 — грамматика; проверяется `tools/grammar_lint.py` | контракт V1 |
| [language/surface.md](language/surface.md) | SURFACE-1 — конструкции, их форма BIR-1, порядок, статические правила | контракт V1 |
| [language/effects.md](language/effects.md) | EFFECTS-1 — атомы, ряды, эффект-переменные, точки входа | контракт V1 |
| [language/format.md](language/format.md) | FORMAT-1 — канонический формат `bag fmt`, назначение `@id` | WORKING_DESIGN |
| [language/checking.md](language/checking.md) | CHECK-1 — `bag check`: порядок, std, диапазоны и `data` диагностик resolve/type/effect | WORKING_DESIGN |
| [language/data-values.md](language/data-values.md) | DATA-TYPES-0.1 — неизменяемые данные V1 | база R07 |
| [language/errors.md](language/errors.md) | ERR-0.1 — фазы отказа и значения ошибок | база R07 |
| [language/semantic-core.md](language/semantic-core.md) | SEM-0.1 — общий семантический контракт V1 | база R07 |
| [language/types.md](language/types.md) | TYPES-0.1 — проверка типов и локальный вывод | база R07 |

## Ядро форматов и диагностики

| Документ | Содержание | Статус |
| --- | --- | --- |
| [kernel/canonical.md](kernel/canonical.md) | KERNEL-CANON-1 — BAG-CJSON-1, ObjectRef, KeyRef, наблюдаемое значение | контракт V1 |
| [kernel/outcomes.md](kernel/outcomes.md) | KERNEL-OUTCOMES-1 — единый словарь исходов и статусов | контракт V1 |
| [diagnostics/README.md](diagnostics/README.md), [registry.json](diagnostics/registry.json) | DIAG-1 — единый реестр кодов | контракт V1 |
| [glossary.md](glossary.md) | Глоссарий терминов и ID контрактов | справочник |

## IR

| Документ | Содержание | Статус |
| --- | --- | --- |
| [ir/bir.md](ir/bir.md) | BIR-1 — единое промежуточное представление (D77) | WORKING_DESIGN |
| [ir/data-forms.md](ir/data-forms.md) | DATA-IR-0.1 — формы данных и соединение с CORE | исследовательский профиль, заменён BIR-1 (r30) |
| [ir/typed-core.md](ir/typed-core.md) | IR-CORE-0.1 — закрытое ядро и граница полного IR | исследовательский профиль, заменён BIR-1 (r30) |

## Runtime

| Документ | Содержание | Статус |
| --- | --- | --- |
| [runtime/machine.md](runtime/machine.md) | MACHINE-1 — CEK-машина BIR-1, уровни L1/L2, `bag run`/`bag test` (D76, D77) | WORKING_DESIGN |
| [runtime/host.md](runtime/host.md) | HOST-1 — хост: SQLite, квитанции, события, журнал, replay, миграция, точки сбоя (D9, D10, D43–D46, D81) | WORKING_DESIGN |
| [runtime/core-machine.md](runtime/core-machine.md) | MACHINE-CORE-0.1 — шаг, окружение и остановка | исследовательский профиль; подмножество MACHINE-1 (MCH-11), оракул моста core01 |
| [runtime/data-work.md](runtime/data-work.md) | DATA-WORK-0.1 — возобновляемые операции над данными | исследовательский профиль; поштучная цена данных в MACHINE-1 не входит (MCH-07) |

## Данные

| Документ | Содержание | Статус |
| --- | --- | --- |
| [data/authorship-transition.md](data/authorship-transition.md) | AUTH-TX-0.1 — смена авторства, поисковая проекция и восстановление | база R07 |
| [data/authorship-values.md](data/authorship-values.md) | AUTH-DATA-0.1 — чистые данные авторства и обратный индекс | база R07 |
| [data/value-codec.md](data/value-codec.md) | CODEC-0.1 — точное представление неизменяемых данных | база R07 |

## Связи LNK-0.4

| Документ | Содержание | Статус |
| --- | --- | --- |
| [links/01-records-and-invariants.md](links/01-records-and-invariants.md) | LNK-0.2 · Записи, свойства и инварианты | база R07 |
| [links/02-extraction-and-refresh.md](links/02-extraction-and-refresh.md) | LNK-0.2. Извлечение и обновление связей | база R07 |
| [links/03-impact-and-context.md](links/03-impact-and-context.md) | LNK-0.2 · Влияние изменения и достаточный контекст | база R07 |
| [links/04-acceptance.md](links/04-acceptance.md) | LNK-0.2 · Требования и приёмка | база R07 |
| [links/05-executable-profile.md](links/05-executable-profile.md) | LNK-0.2 · Исполнимый исследовательский профиль OBS-0.1 | база R07 |
| [links/06-law-checking.md](links/06-law-checking.md) | LNK-0.3 · Проверяемые законы уточнения зависимостей | база R07 |
| [links/07-call-composition.md](links/07-call-composition.md) | 07. Композиция зависимостей через вызовы · R04 | база R07 |
| [links/README.md](links/README.md) | ТЗ на поддерживаемые связи bagaev · LNK-0.4 | база R07 |
| [links/08-bagaev-extraction.md](links/08-bagaev-extraction.md) | LINKS-1 — извлечение графа из BIR-1, влияние по объединению графов с сертификатами D83, ContextPack | WORKING_DESIGN; переводит 01–04 в термины bagaev, 05–07 остаются исследовательскими |
| [links/graph.schema.json](links/graph.schema.json) | Языконезависимая схема графа связей bagaev-graph/1 | WORKING_DESIGN |

## Профиль V1

| Документ | Содержание | Статус |
| --- | --- | --- |
| [profiles/v1.md](profiles/v1.md) | V1 — реестр области и правила её завершения | база R07 |

## Протокол инструментов

| Документ | Содержание | Статус |
| --- | --- | --- |
| [protocol/agent-protocol.md](protocol/agent-protocol.md) | CHANGE-1 — проектное хранилище, SourceEdit и идентичность, ChangeContract, свидетельства, WorkState, приёмка с CAS, протокол агента (CLI и MCP) | WORKING_DESIGN |
| [protocol/state-machines.md](protocol/state-machines.md) | Конечные автоматы работы, обязательства, квитанции и head | WORKING_DESIGN |
| [protocol/operations.schema.json](protocol/operations.schema.json) | Схема запросов и ответов протокола агента | WORKING_DESIGN |
| [protocol/idempotency-lifecycle.md](protocol/idempotency-lifecycle.md) | IDEM-LIFECYCLE-0.2 — ключи, повтор, владение и восстановление | дополнение R16; ядро (квитанция до guard'ов, конфликт ключа, без истечения) интегрировано в HST-05 и CHG-15, остальное заморожено |
| [protocol/lifecycle-wire.schema.json](protocol/lifecycle-wire.schema.json) | JSON Schema | дополнение R16, не интегрировано |

## Поставка, восстановление, совместимость, выпуск

| Документ | Содержание | Статус |
| --- | --- | --- |
| [distribution/bootstrap.md](distribution/bootstrap.md) | Установка, окружение и создание проекта | дополнение R17, заморожено вне V1 (D88) |
| [distribution/clean-install-route.md](distribution/clean-install-route.md) | Проверяемый маршрут чистой установки | дополнение R17, заморожено вне V1 (D88) |
| [distribution/release-input.schema.json](distribution/release-input.schema.json) | JSON Schema | дополнение R17, заморожено вне V1 (D88) |
| [distribution/recovery-route.md](distribution/recovery-route.md) | RECOVERY-ROUTE-0.1 — маршрут проверки восстановления проекта | дополнение R18, заморожено вне V1 (D88) |
| [distribution/recovery-set.md](distribution/recovery-set.md) | RECOVERY-SET-0.1 — восстановление проекта из объявленных входов | дополнение R18, заморожено вне V1 (D88) |
| [distribution/recovery-set.schema.json](distribution/recovery-set.schema.json) | JSON Schema | дополнение R18, заморожено вне V1 (D88) |
| [distribution/compatibility-route.md](distribution/compatibility-route.md) | COMPATIBILITY-ROUTE-0.1 — интеграционная проверка T18-C01/C02 | дополнение R19, не интегрировано |
| [distribution/compatibility.md](distribution/compatibility.md) | VERSION-BINDING-0.1 — версии, совместимость и смысл программы | дополнение R19, не интегрировано |
| [distribution/compatibility.schema.json](distribution/compatibility.schema.json) | JSON Schema | дополнение R19, не интегрировано |
| [distribution/migration.md](distribution/migration.md) | MIGRATION-PLAN-0.1 — явный переход проекта между версиями | дополнение R19, не интегрировано |
| [distribution/release-lock-route.md](distribution/release-lock-route.md) | R20 — маршрут независимой проверки настоящего toolchain и выпуска | дополнение R20, заморожено вне V1 (D88) |
| [distribution/release.md](distribution/release.md) | RELEASE-INTENT-0.1 — выпуск из точных входов и отдельное внешнее действие | дополнение R20, заморожено вне V1 (D88) |

## Toolchain: lock, pipeline, диагностика, сохранение поведения

| Документ | Содержание | Статус |
| --- | --- | --- |
| [toolchain/dependency-lock.md](toolchain/dependency-lock.md) | DEPENDENCY-LOCK-0.1 — точный граф входов сборки | дополнение R20, заморожено вне V1 (D88); lock V1 = хеши содержимого |
| [toolchain/diagnostics.md](toolchain/diagnostics.md) | DIAGNOSTIC-PIPE-0.1 — ошибки, координаты и исправления | дополнение R21, не интегрировано |
| [toolchain/incremental-origin.md](toolchain/incremental-origin.md) | CACHE-PIPE-0.1 и ORIGIN-PIPE-0.1 | дополнение R21, не интегрировано |
| [toolchain/pipeline-route.md](toolchain/pipeline-route.md) | Сквозная проверка и порядок реализации R21 | дополнение R21, не интегрировано |
| [toolchain/pipeline.md](toolchain/pipeline.md) | PIPELINE-0.1 — контракт конвейера компилятора | дополнение R21, не интегрировано |
| [toolchain/optimization-rules.md](toolchain/optimization-rules.md) | OPT-RULES-0.1 · конкретный каталог преобразований | дополнение R22, заморожено вне V1 (D88) |
| [toolchain/pipeline-bridge.md](toolchain/pipeline-bridge.md) | P5-OPT-0.1 · точное включение в R21 | дополнение R22, заморожено вне V1 (D88) |
| [toolchain/preservation-checking.md](toolchain/preservation-checking.md) | PRESERVE-CHECK-0.1 · проверка и применение | дополнение R22, заморожено вне V1 (D88) |
| [toolchain/preservation-route.md](toolchain/preservation-route.md) | R22 · маршрут реализации и приёмки | дополнение R22, заморожено вне V1 (D88) |
| [toolchain/preservation.md](toolchain/preservation.md) | PRESERVE-0.1 · сохранение наблюдаемого исполнения | дополнение R22, заморожено вне V1 (D88) |
| [toolchain/ffi-bridge.md](toolchain/ffi-bridge.md) | FFI-TOOLCHAIN-0.1 — связь с компилятором и загрузчиком | дополнение R23, заморожено вне V1 (D88) |

## FFI

| Документ | Содержание | Статус |
| --- | --- | --- |
| [ffi/calls-effects-callbacks.md](ffi/calls-effects-callbacks.md) | CALL-FFI-0.1 — эффекты, вызовы и обратные вызовы | дополнение R23, заморожено вне V1 (D88) |
| [ffi/codec-machine.md](ffi/codec-machine.md) | CODEC-FFI-0.1 — точная машина обхода и стоимости | дополнение R23, заморожено вне V1 (D88) |
| [ffi/contract.md](ffi/contract.md) | FFI-BOUNDARY-0.1 — явная граница внешнего кода | дополнение R23, заморожено вне V1 (D88) |
| [ffi/ffi-route.md](ffi/ffi-route.md) | R23 · маршрут реализации и приёмки FFI | дополнение R23, заморожено вне V1 (D88) |
| [ffi/isolation-adapters.md](ffi/isolation-adapters.md) | ADAPTER-FFI-0.1 — native shim и допуск платформы | дополнение R23, заморожено вне V1 (D88) |
| [ffi/ownership-lifecycle.md](ffi/ownership-lifecycle.md) | OWN-FFI-0.1 — владение и прекращение доступа | дополнение R23, заморожено вне V1 (D88) |
| [ffi/wire-abi.md](ffi/wire-abi.md) | WIRE-FFI-0.1 — переносимые значения и кадры | дополнение R23, заморожено вне V1 (D88) |

## Metadata-схемы

| Документ | Содержание | Статус |
| --- | --- | --- |
| [metadata/release-lock.md](metadata/release-lock.md) | R20 metadata binding и обязательные семантические проверки | дополнение R20, заморожено вне V1 (D88) |
| [metadata/release-lock.schema.json](metadata/release-lock.schema.json) | JSON Schema | дополнение R20, заморожено вне V1 (D88) |
| [metadata/pipeline.md](metadata/pipeline.md) | R21 metadata — внешние контракты compiler pipeline | дополнение R21, не интегрировано |
| [metadata/pipeline.schema.json](metadata/pipeline.schema.json) | JSON Schema | дополнение R21, не интегрировано |
| [metadata/preservation.md](metadata/preservation.md) | R22 metadata · форма и граница проверки | дополнение R22, заморожено вне V1 (D88) |
| [metadata/preservation.schema.json](metadata/preservation.schema.json) | JSON Schema | дополнение R22, заморожено вне V1 (D88) |
| [metadata/ffi.md](metadata/ffi.md) | R23 FFI metadata: closed shape and declared local links | дополнение R23, заморожено вне V1 (D88) |
| [metadata/ffi.schema.json](metadata/ffi.schema.json) | JSON Schema | дополнение R23, заморожено вне V1 (D88) |

## Стандартная библиотека

| Документ | Содержание | Статус |
| --- | --- | --- |
| [stdlib/acceptance.md](stdlib/acceptance.md) | Проверка и маршрут реализации стандартной библиотеки | R24 |
| [stdlib/api.md](stdlib/api.md) | STDLIB-API-0.1 — закрытый каталог библиотеки | R24 |
| [stdlib/resolution.md](stdlib/resolution.md) | STD-RESOLVE-0.1 — замкнутый каталог и двунаправленные зависимости | R24 |
| [stdlib/services.md](stdlib/services.md) | STD-SERVICE-1 — хранилище и события в программе (D81) | r31, переписан под D81 |
| [stdlib/types.md](stdlib/types.md) | STDLIB-TYPES-0.1 — типы, ошибки и владение | R24 |
| [stdlib/work.md](stdlib/work.md) | STDLIB-WORK-0.1 — порядок, стоимость и продолжения | R24 |

## Схемы

`*.schema.json` — JSON Schema Draft 2020-12 для внешних записей своих областей; их формы проверяются моделями (`models/*/tools/validate_*`). Описание каждой — соседний `*.md` в `metadata/` или текст области.
