# RECOVERY-ROUTE-0.1 — маршрут проверки восстановления проекта

**T18-C03 · проект интеграционного маршрута · все RI-01..RI-24 имеют статус NOT_RUN.** Этот файл определяет предмет будущей проверки, входы, порядок действий и независимый ожидаемый результат. Исследовательская Python-модель не заменяет выполнение этого маршрута.

Основной контракт: [RECOVERY-SET-0.1](recovery-set.md). Установка среды: [R17 bootstrap](bootstrap.md). Ключи, эффекты и current authority: [R16 lifecycle](../protocol/idempotency-lifecycle.md).

## 1. Обязательный комплект для запуска

IntegrationInputLock — подписанный/доверенный по deployment policy описатель с точными хешами и версиями. Пустой placeholder в любом обязательном поле означает INPUT_NOT_READY.

| Вход | Что необходимо предоставить |
| --- | --- |
| V1FixtureRef | Реальная программа на принятой source grammar T03, typed core и независимый expected result; placeholder-псевдосинтаксис не допускается |
| SourceHistoryFixtureRef | Несколько точных source versions, working/accepted heads, pending changes и relation graph с version-bound edges |
| SemanticContractRefs | Grammar, value/IR codecs, execution/verification/effect profiles, exact pure journal reducers |
| EnvironmentLockRef | Compiler/runtime/target/package closure R17/T13, проверенное происхождение и offline bytes |
| ProjectDataFixtureRef | Конфигурация, данные, recorded inputs, исторические evidence и полные declared external requirements |
| StorageAdapterRef | Реальный checkpoint/journal/object store с подтверждённым atomic commit и crash durability |
| AuthorityAdapterRef | Текущий источник полномочий вне rollback domain; maintenance slots, actual fencing, final frontier, CAS и lookup |
| ParticipantAdaptersRef | IdentityRoot и install-store launch pins R17, effect ledger, secret resolver, runtime checkpoint adapter |
| ExternalEndpointFixtureRef | Контролируемый endpoint с журналом фактических запросов, exact remote keys и управляемыми задержками/ответами |
| RecoveryVerifierRef | Отдельный verifier, реализующий точные format/closure/root/authority проверки |
| IndependentOracleRef | Замороженное expected state и outcome rules, созданные из fixture и workload до запуска capture/restore |
| FaultPlanRef | Точные crash points, lost responses, disk-full/readonly/corruption injection и seed |
| DeploymentContractRef | Платформа, filesystem/DB mode, durability/power-loss assumptions, время, trust policy, read/write permissions |
| ResultArchiveRef | Место для машинных результатов, stderr/trace, input hashes, actual state roots и failure evidence |

Текущие файлы R18 не объявляют эти входы существующими. Первую фактическую платформу можно наследовать от выбранного R17 профиля Linux x86-64, но R18 не присваивает ей PASS. Платформенные свойства проверяются на точной версии backend, а не выводятся из успешного Python-перехода.

## 2. Небольшой, но полный предмет интеграции

Одна программа содержит детерминированный чистый вычислительный путь и отдельно изолированный эффектный путь. Не нужен большой демонстрационный продукт; нужны все роли состояния:

- Две версии исходника, отдельные working и accepted heads, одно pending изменение и непринятое обязательство проверки.
- Граф минимум из requirement/spec/code/evidence nodes; несколько входящих связей к одному объекту и одна связь к старой версии, чтобы rebuild не смешал версии.
- Историческое PASS на старый exact subject и действующее обязательство проверки нового.
- Один завершённый idempotency key, один pending local command, один retired namespace/closed prefix.
- Один effect, точно не отправленный; один подтверждённый effect; один MAY_HAVE_RUN/UNKNOWN с уникальным remote key.
- Одна чистая restartable job и одна suspended checkpoint job с уже потраченным budget.
- Один незавершённый cross-store launch pin/intent и один terminal launch с доказуемо допустимым release pin.
- Полный source/package/config/data closure и как минимум один declared external binding.

Точные ID, исходники, outputs, ledgers и roots определяет отдельный fixture bundle. Тестовый ожидаемый результат не генерируется вызовом восстанавливаемого provider. Independent oracle может вычислять root из канонических fixture bytes по отдельно написанному алгоритму; его входы и код фиксируются до запуска.

## 3. Сквозная последовательность

1. Проверить IntegrationInputLock. Получить чистое isolated host окружение, текущую authority identity и отдельный instrumentation log endpoint. Зафиксировать effective permissions и storage mode.
2. Создать проект через фактический R17 route. Применить детерминированный workload с заранее заданными command IDs и independent expected transitions. Сохранить oracle trace отдельно от provider output.
3. На срезе C создать checkpoint, после C выполнить известный tail до H и cross-store operations. Часть pending/UNKNOWN обязана появиться до C, часть после: иначе проверка не обнаружит потерю старого долга.
4. Выполнить capture SERIALIZED-CUT-1. Зафиксировать participant vector, pins, obligation counts/roots, журнал и seal. Проверить, что после публикации проект может создать события H+1..J, не меняя исторического RecoverySet.
5. На другом чистом host выполнить INSPECT_SNAPSHOT с отключённым dispatch. Сравнить canonical state, heads, graph, key/obligation inventory и историческое evidence с independent expected H.
6. Удалить только rebuildable reverse index/cache. Повторить materialization и сравнить reverse query results с independently sorted canonical edges. Потеря канонического edge отдельно должна блокировать успех.
7. Выполнить REPRODUCE_PROGRAM на pinned environment. Сверить actual build/runtime outputs с независимым expected, включая declared recorded inputs и effect-free policy.
8. Для RESUME_AUTHORITY закрыть gates, начать attempt, установить actual fences, получить финальный J, catchup H+1..J, перепроверить roots и подготовить candidate. Проверить, что прежний worker не может ни commit, ни новый dispatch.
9. Выполнить authority CAS и local activation как отдельные durable operations. Независимо сверить authority/local receipts и active candidate/epoch.
10. Проверить historical receipt replay под текущим разрешением чтения; проверить отказ с revoked read permission. Старые write grants и watch cursors не должны ожить.
11. Убедиться, что known UNKNOWN остался с прежним remote key и что endpoint не получил автоматического повтора. Его settlement выполняется отдельным reconciliation сценария, не частью restore.
12. Для каждого fault point восстановить процесс и повторить тот же attempt. Сверить фактический external call log, journal, authority record, local receipt и полный obligation inventory. Количество выводимых строк не заменяет сравнение состояния.

## 4. Матрица обязательных интеграционных сценариев

| ID | Воздействие | Независимый ожидаемый результат | Статус |
| --- | --- | --- | --- |
| RI-01 | Полный исторический snapshot и tail C..H | Exact state/roots/coverage на H; только readonly | NOT_RUN |
| RI-02 | Полное воспроизведение source/environment/data | Реальный decode/check/build, expected outputs; PROGRAM_REPRODUCED только после сравнения | NOT_RUN |
| RI-03 | Resume старого H при текущем J>H | Exact catchup до frozen J, новая эпоха, сохранённые долги | NOT_RUN |
| RI-04 | Удалена роль из manifest, остальные hashes правильны | ROLE_MISSING; нет полного результата | NOT_RUN |
| RI-05 | Удалена транзитивная package/data dependency | CLOSURE_GAP; без PATH/network latest fallback | NOT_RUN |
| RI-06 | Пропуск, дубликат, перестановка и fork в tail | JOURNAL_GAP/FORK; ни один вариант не допускает writer | NOT_RUN |
| RI-07 | UNKNOWN существовал до C, затем исчез из checkpoint | OBLIGATION_MISMATCH или UNPROVEN_CAPTURE_COMPLETENESS | NOT_RUN |
| RI-08 | Snapshot разных stores снят в несогласованные моменты | Participant correlation mismatch; CAPTURE_INCOMPLETE | NOT_RUN |
| RI-09 | Effect отправлен до barrier, remote ответ после него | Один прежний intent остаётся UNKNOWN; replay не отправляет его | NOT_RUN |
| RI-10 | Reservation есть, local commit возможен, подтверждения нет | QUARANTINED до допустимой классификации; absence не ABORTED | NOT_RUN |
| RI-11 | Current anchor изменился после validation | CURRENT_FRONTIER_CHANGED; stale candidate не активирован | NOT_RUN |
| RI-12 | Старый worker пишет после fence/restore | Отказ в реальной commit/dispatch boundary, включая поздний worker | NOT_RUN |
| RI-13 | Crash до/во время FENCING и до PREPARED | Gates закрыты; same-attempt continuation; старая эпоха не оживает | NOT_RUN |
| RI-14 | Crash после authority commit до local activation | Lookup того же attempt; exact candidate activates либо остаётся CLOSED | NOT_RUN |
| RI-15 | Потерян ответ local activate и повтор запроса | Один bound result/epoch; historical receipt после current read auth | NOT_RUN |
| RI-16 | Две recovery attempts и конфликтующий retry digest | Один активный reservation; conflict не перезаписывает намерение | NOT_RUN |
| RI-17 | Candidate bytes/environment изменились после PREPARED | CANDIDATE_CHANGED, commit/activation запрещены | NOT_RUN |
| RI-18 | Rollback архива authority, counters или retired keys | Stale authority/monotonicity отказ; старые адреса не допускаются заново | NOT_RUN |
| RI-19 | Удалён reverse index и отдельно canonical edge | Index перестроен без потерь; edge loss отдельно блокирует полный graph recovery | NOT_RUN |
| RI-20 | Старый PASS, иной working head, новые watch/session | PASS остаётся историческим; applicability пересчитана, старые cursors invalidated | NOT_RUN |
| RI-21 | Отсутствует checkpoint job, secret или environment byte | Точный suspended/binding/closure отказ; budget не обнулён | NOT_RUN |
| RI-22 | Неизвестный формат или скрытая semantic migration | FORMAT_UNSUPPORTED/MIGRATION_REQUIRED, без reinterpretation | NOT_RUN |
| RI-23 | Crash публикации, partial upload, потерян pin release | Нет ложного SEALED; неизвестный pin не снят по TTL | NOT_RUN |
| RI-24 | Disk-full, limit/epoch overflow, permission revoke | Gates остаются закрыты; no eviction debts; no leaked historical receipt | NOT_RUN |

Один ID может иметь несколько заранее заданных вариантов, но не создаёт новых критериев прогресса. Запись PASS возможна только с exact inputs, oracle, actual outputs и проверенными scope assumptions.

## 5. Формат фактического результата

Каждый RI record содержит: id, input lock digest, fixture/oracle refs и freeze time, provider/verifier build identities, platform/storage deployment refs, seed/fault point, expected и actual outcomes, before/after roots, authority/local phase trace, actual external call count+request identities, preservation checks по каждой роли, started/finished times и verdict.

Сбой запуска, import error, timeout без диагностики и несовместимый fixture — ERROR/INCONCLUSIVE, не успешная проверка ожидаемого отказа. UNKNOWN remote outcome — допустимое ожидаемое состояние только при сохранённом полном intent и независимом наблюдении отсутствия автоповтора; он не означает, что внешний эффект не случился.

Для crash tests отдельно указываются процессный kill, системный reboot и фактическая проверка power-loss durability. Kill одного Python-процесса не доказывает сохранность при потере питания. Взаимодействие двух независимых stores проверяется именно двумя adapters/процессами с раздельными fault points.

## 6. Gate перехода к следующему уровню

Stage 2 относится к полноте проекта контракта. Для stage 3 T18-C03 нужны все объявленные roles, поддерживаемые modes/platforms, реальные capture/restore/runtime/authority integration и независимые результаты; сужать критерий до удачного finite примера нельзя. Stage 4 требует принятия, точных evidence и выполненных dependencies по SPEC-PROGRESS-1.

Если отдельный mode или platform пока не поддержан, поддержка фиксируется до запуска проверки и остаётся явным ограничением V1; отсутствие результата не маскируется сменой формулировки исходного критерия.
