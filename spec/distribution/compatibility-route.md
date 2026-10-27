# COMPATIBILITY-ROUTE-0.1 — интеграционная проверка T18-C01/C02

**Статус: NOT_RUN.** Это маршрут будущей проверки полного контракта. 26 cases ниже не являются результатами finite model и не прибавляются к её числу PASS. Для реального запуска нужны exact production inputs, которых в R19 нет.

## 1. Входной lock и независимые роли

RouteInputLock обязан перечислить:

- Exact compiler/runtime/CLI builds старой и новой среды; platform/ABI, dependency closure и R17 environment refs.
- Реальный V1 source/IR/type/value/package/protocol release profile, а не только исследовательский текст или демонстрационные W1/W2.
- Извлечённый из всех storage/protocol entrypoints inventory writer/reader kinds, production registry и направленные operation matrices.
- Fixture projects: old working и accepted source versions, nominal types, authored/observed/structural relation edges, current и historical evidence, UNKNOWN effects, unresolved work, pending jobs и израсходованный budget.
- R16 journal/keys/adapters, R17 identity/install/pin store, R18 current authority/checkpoint/capture implementations и их declared durability profiles.
- Exact transform/checker builds, observation domains, accepted proof method, fault injector, platform limits и current test authorization policy.

Любой unavailable input получает INPUT_NOT_READY с конкретным ref/ролью. Route не выбирает latest, не создаёт выдуманный production source и не заменяет real adapter словарём. Missing decoder не интерпретируется как отсутствие объектов этого вида.

**Provider** реализует resolver, transform и protocol. **Verifier** до просмотра реализации фиксирует intent cases, затем по immutable contract — точные inputs, ожидаемые results/observations и независимые state/relation checks. **Reviewer** проверяет охват исходных критериев целиком, provenance, observation gaps и saved outputs. Если roles совмещаются, это раскрывается; авторская проверка не называется независимой.

Для fault cases expected results — наблюдаемые snapshots/receipts/authority histories после всех допустимых восстановления/lookup paths. Факт отсутствия crash не является oracle. Принудительное исключение из mutated implementation не считается semantic mutant kill, если тест не устанавливает требуемую семантическую ошибку.

## 2. Подготовка и порядок исполнения

1. Verifier закрепляет RouteInputLock, cases и исходные данные. Для каждого advertised registry support entry создаётся positive case и negative boundary case; coverage closure проверяется по реальному inventory. Таблица ниже задаёт классы обязательных случаев, не ограничивает release suite ровно26 тестами.
2. Зафиксировать expected baseline observations старых программ на pinned tools: values/errors, semantic resource accounting, effects/cancel/work state и canonical relations. Для nondeterministic profile использовать exact declared relation/trace set, не произвольное сравнение одного запуска.
3. Развернуть две чистые среды и долговечные storage/authority domains. Проверить исходный closure и actual writer fences. Сохранить byte-level source/lock snapshots и logical protected-state projections.
4. Выполнить host update отдельно от project migration. Затем для каждого explicit path выполнить plan→stage→check→final fence→prepare→authority commit→local activation.
5. Вставлять сбои на каждой durable boundary; пересоздавать процессы и, где допускает профиль, storage clients. Проверить current attempt lookup, без повторного dispatch неизвестного эффекта и без старых authority tokens.
6. Снять exact actual outputs и независимые canonical state digests/observation results. Не переписывать expected oracle под фактические результаты. Исправление implementation получает новый hash, исходный failure сохраняется.
7. Проверить directions/targets/domains отдельно. Результат A→B не подставляется в B→A; engine/model class coverage не подменяет полный release inventory.
8. Reviewer принимает или отвергает весь исходный критерий. Перед нормативной приёмкой проверяются dependencies и полномочия; публикация языка/пакета не входит автоматически в этот маршрут.

## 3. Обязательные cases

Во всех строках статус **NOT_RUN**. `C01` и `C02` означают исходные T18-C01 и T18-C02.

| ID | Предмет и ввод | Независимое ожидаемое наблюдение | Критерии |
| --- | --- | --- | --- |
| IC19-01 | Извлечь registry inventory из всех real writers/readers; добавить один незарегистрированный persistent kind | Release gate сообщает точный REGISTRY_COVERAGE_GAP. Без вставленного вида coverage замкнут по всем F01–F18, а не только по заранее составленному списку | C01 |
| IC19-02 | Два contract/build artifacts с одинаковым label, разными bytes; отдельно SemVer labels с build metadata | Exact refs различаются; конфликт не разрешается по порядку версии; ни read-admission, ни project repin не меняются молча | C01,C02 |
| IC19-03 | Old source использует имя, ставшее keyword новой edition; установить новый host tool | Старый pinned MeaningLock продолжает прежнюю трактовку либо явно отказывает из-за недоступного old reader; новая grammar не применяется автоматически | C01,C02 |
| IC19-04 | Values с missing/null/empty/default, nominally distinct same-layout types, max integer и ordered entries | Transform/checker сохраняют typed relation каждого случая; overflow/truncation/default injection/nominal collapse отвергаются. Parse-only success отдельно от rewrite | C01,C02 |
| IC19-05 | Old/new textual IR, binary IR, opcode/cost/optimizer metadata, supported и unsupported revisions | Operation matrix различает decode/execute/rewrite. Неизвестный required opcode/cost не пропускается; metadata removal требует declared inert-preservation policy | C01,C02 |
| IC19-06 | Same wire-compatible package c изменённым API/ABI или generated-code/runtime pair | Link/execute refuse несовместимый exact interface/runtime pair; wire compatibility не даёт runtime compatibility | C01,C02 |
| IC19-07 | Unknown inert annotation bytes с важными пустыми/default формами; lossless formatter и JSON/field-copy converter | Opaque/allowed metadata view работает; preserving rewrite оставляет exact bytes. Потеря annotation даёт PROTECTED_STATE_LOSS | C01,C02 |
| IC19-08 | Неизвестная required semantic feature; ordinary unknown field; вход самостоятельно ставит critical=false | Trusted policy определяет критичность; decode/execute/resume refuse. Input label не даёт себе права быть inert | C01,C02 |
| IC19-09 | A→B и B→C с несовпадающими domains/observations; обратный B→A; два overlapping claims для разных targets | Нет автоматической транзитивности/обратимости. Exact target/domain/scope обязателен; неоднозначность без explicit claim отклоняется | C01 |
| IC19-10 | Один artifact, query каждого из восьми operation capabilities; checker только value domain | Ответы перечисляют exact capability. Inspect не исполняет payload; VERIFY historical не выдаёт REUSE; value certificate не разрешает full preservation | C01,C02 |
| IC19-11 | Working source мигрирует на новую edition/environment, accepted head остаётся old | Оба source versions сохраняют свои MeaningLock/Environment refs; old accepted не интерпретируется новым default, new working не получает acceptance | C01,C02 |
| IC19-12 | Два transforms дают тот же final scalar, но меняют semantic cost, момент cancel или порядок/target эффекта | Full preservation checker отвергает их либо выдаёт UNKNOWN недостаточного observation coverage. Explicit SEMANTIC_CHANGE создаёт новые obligations | C02 |
| IC19-13 | Canonical graph содержит structural, authored и observed edges, UNKNOWN/gap; новый extractor не умеет воспроизвести старое observation | Structural edges пересчитаны с mapping; authored/observed history не потеряны. Reverse queries корректны в обе стороны после rebuild; old subject refs не переназначены | C01,C02 |
| IC19-14 | Historical PASS на old build/subject; repin bug-fixed build; попытка reuse без transfer basis | Historical receipt unchanged. Новая acceptance видит affected applicability/known defect; proof transfer требует exact method/domain basis | C01,C02 |
| IC19-15 | Persisted job с pending reservation, spent budget, cancel request; новый runtime использует другие cost units | Exact continuation relation или SUSPENDED_INCOMPATIBLE_RUNTIME; долг, budget и cancellation не reset. Current RESUME admission отдельно | C01,C02 |
| IC19-16 | Endpoint пересылает иной negotiation transcript/выбирает контракт ниже required capabilities; reconnect на другой сервер | Authentication/integrity adapter обнаруживает подмену; выбранный exact SessionBinding проверен; отсутствие общего contract — explicit refusal, без silent downgrade | C01,C02 |
| IC19-17 | После смены protocol codec повторить старый key/request с original revision; тот же key с новым meaning/digest | Сначала current read rights и historical lookup; exact receipt или bounded original wrapper. Иной digest конфликтует; decoder retirement не освобождает namespace | C01,C02 |
| IC19-18 | Host default update, parallel launch, install GC; old project pinned environment | Project/environment/version refs unchanged; GC сохраняет live и UNKNOWN launch pins. Новый default не подменяет executable старого проекта | C02 |
| IC19-19 | Обычная запись после preview/check; затем вернуть content hash к старому значению при выросшей generation | Final cut mismatch и ABA дают STALE_SOURCE_CUT; candidate/certificate/semantic intent не перепривязываются. Новый plan/key связывает current state | C02 |
| IC19-20 | Старый worker продолжает actual storage write/dispatch при FENCING и после activation; один participant не отвечает | FENCING не объявляется final без реального барьера; actual commit/dispatch guard отвергает stale epoch/write contract. Silence не считается fenced | C02 |
| IC19-21 | Crash перед/после каждого durable phase, authority reply loss, local commit acknowledgement loss, cancel/commit race | Однозначный authority outcome по same attempt; до authority commit допустим доказанный abort, после — завершение выбранного target/QUARANTINED. Нет двойного действия или partially published binding | C02 |
| IC19-22 | Authority committed migration A; recovery B получила свежий epoch; A запоздало пытается local activation | Actual commit guard отказывает A по exact current authority/attempt/target. Старый receipt не открывает прежний epoch и не перезаписывает B | C02 |
| IC19-23 | После activation создать новые writes/UNKNOWN effects/receipts и потратить budget, затем запросить old snapshot rollback | Snapshot не становится active. Новая reverse migration строится от current state; unsupported inverse/domain отклоняется, свежие записи/долги не теряются | C01,C02 |
| IC19-24 | Максимальные refs/depth/object counts, uint64 exhaustion, large annotations, small state→oversized response, staging quota | Точный bounded refusal до irreversible publication; counters не wrap; committed result доступен только объявленным bounded receipt protocol. Нет silent truncation | C01,C02 |
| IC19-25 | Retire decoder, когда old project/job/key/evidence/recovery ref ещё reachable; затем объявленный archival service недоступен | Retirement gate удерживает необходимые codecs/refs либо явно отказывает; ARCHIVE_UNAVAILABLE не превращает history в empty object и не разрешает key reuse | C01,C02 |
| IC19-26 | Разрешённый SEMANTIC_CHANGE и независимый STORAGE_REENCODE; release/deploy adapters подключены | Первый создаёт новый working candidate и обязательства принятия; второй не присваивает acceptance. Ни migration, ни acceptance не запускают publish/deploy без отдельного admission | C02 |

## 4. Машинный report и gates

Report содержит RouteInputLockRef, case IDs и exact instances, expected/actual refs, observation relation, provider/checker builds, failure injection point, before/after state roots, authority/receipt history, status PASS/FAIL/UNKNOWN/INPUT_NOT_READY/NOT_RUN и независимые reviewer conclusions. Счётчик scenarios не смешивается со счётчиком transition assertions, guards, mutants и schema probes.

Для C01 требуются полный inventory closure и per-kind/per-operation results на заявленной release matrix. Для C02 требуются pinned old program observations, реальный host update, explicit project transition, protected-state checks, current authority/crash routes и refusal semantic changes без заявленного intent. Исключение операции/платформы явно сужает released support matrix; оно не удаляет исходный критерий из плана.

Finite report R19 полезен как проверка принципов resolver/typed transform/CAS, но не исполняет IC19-01–IC19-26. JSON Schema probes проверяют форму исследовательских метаданных; они не являются evidence фактической совместимости.

Stage3 не присваивается по одному успешному bounded executable. Stage4 требует принятия с зависимостями T01/T13/T14 и связанными T03–T12 в действующем общем реестре. Полные bytes R15 до reconciliation всё ещё необходимы для изменения общего числа stage points.
