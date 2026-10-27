# Проверяемый маршрут чистой установки

**R17 · BOOTSTRAP-ROUTE-0.1 · proposed · 23 октября 2026 (Москва).** Это инструкция для будущей реализации и её независимой приёмки. Команды ниже пока описывают контракт CLI. Они **не запускались** как установка bagaev. Исполненный исследовательский опыт находится отдельно и моделирует только переходы bootstrap/install.

Общие обязательные правила: [bootstrap.md](bootstrap.md). Исходный предмет: [T18-C04](../../registry/tasks/T18-release-ecosystem.md). Для стадии 2 можно описать маршрут при объявленных входах; стадия 3 требует выполнить его на всём объявленном профиле, используя настоящий дистрибутив и исходник языка.

## 1. Входной комплект

Проверяющий получает неизменяемые входы до запуска тестируемой реализации:

| Вход | Как фиксируется | Что блокирует запуск |
| --- | --- | --- |
| Чистый host image | OS/image digest; CPU/ABI; kernel; mount и storage profile; доверенный clock | Неизвестный/несовместимый host profile |
| Bootstrap verifier | Binary digest, independent trust provenance, поддерживаемые schema refs | Исполнение verifier до установления доверия |
| Trusted root и policy | Exact root metadata; цепочка доверия; versions/floors; expiry; issuer | Self-signed bundle без независимого доверия |
| ReleaseDescriptor | Exact signed target bytes, `ISSUED`, полный roster/format matrix | Draft, отсутствующий tool role, неразрешённый format |
| EnvironmentLock | Content digest, exact tool/native/package closure | Range/latest/PATH dependency либо missing blob |
| StarterDescriptor | Exact source/template bytes, profile, entry, package lock, independent golden | Нет настоящего T03-source, mapping или golden |
| Limits | Exact semantic и host budgets, timeout policy, memory/output/disk bounds | Неограниченный запуск или разные скрытые defaults |
| Recording policy | Что сохранять; допущенные redactions; reviewer identity | Включение credentials/полного частного проекта в отчёт |

Archive sources R07, R16 и finite model в этом дополнении не являются таким готовым release. Здесь нет сфабрикованных compiler binaries, production signing keys или якобы совместимого минимального source syntax. Будущий producer должен выдать реальные bytes по этим интерфейсам. Если их нет, route завершается `RELEASE_INCOMPLETE`/`TEMPLATE_UNVERIFIED`; это честный отказ, а не PASS.

Reference route использует отдельные пустые `./tools-root` и `./demo`, без другой установки bagaev. Предварительное наличие обычных host tools не влияет на выбор compiler; доверенный launcher вызывается по проверенному absolute path. Сеть отключена на уровне тестового стенда, не только CLI flag. Состояние cache заранее инвентаризовано; warm cache не считается clean-cache опытом.

## 2. Positive route: от bytes к результату

В shell примерах имя `bag-bootstrap` означает заранее проверенный absolute-path bootstrap binary. Значения из JSON receipts передаются как точные ссылки, не вычисляются эвристикой из имени каталога. Запись `--*-file` включает strict decode, exact schema/hash check и current guards; произвольный JSON-файл не является полномочием.

### A. Установить installation root

```sh
bag-bootstrap install root create --root ./tools-root --trust-file ./bootstrap-trust.json --offline --json
```

Expected: exit0, свежий InstallRootId, generation`0`, empty active selector, bounded RootReceipt. Destination создан exclusive; project state отсутствует. Crash/retry использует host reservation той же операции. Root trust metadata не предоставляется неизвестным bundle автоматически.

Для новой identity domain создаётся отдельный корень, который нельзя удалять при удалении tools:

```sh
bag-bootstrap identity root create --directory ./identity-root --request-key identity-root-001 --receipt-file ./identity-root.receipt.json --json
```

Это exclusive host-provisioning операция на действительно чистом стенде с durable destination reservation вне будущей DB. Expected: новый IdentityRootId, пустой used-id index, начальная key generation и config ref. Повтор использует ту же reservation; отсутствие старого registry на существующем host не доказывает новую domain и ведёт к recovery. Каталог `./identity-root` отдельный от `./tools-root` и `./demo`. Его locator/root identity передаются init явно через receipt/config; registry не ищется по случайным parent paths.

### B. Подготовить точный план

```sh
bag-bootstrap install plan --root ./tools-root --release-file ./release.json --lock-file ./environment.lock.json --offline --write-plan ./install-plan.json --json
```

Expected: полный closure, missing`[]`, exact EnvironmentRef, base generation`0`, scope host/trust проверок, declared actions; source/run effects`0`. `--write-plan` явно разрешает только запись этого plan artifact и соответствующего admitted planning record по contract. Для чистого preview используется `--preview`, без durable admission. Ни один package hook или source файл не исполняется.

Expected negative variant: удалить один настоящий необходимый blob перед новым plan → `OFFLINE_MISSING`, exact missing ref, active selector по-прежнему empty. Успех с незаявленным системным compiler запрещён.

### C. Установить подготовленное окружение

```sh
bag-bootstrap install apply --root ./tools-root --plan-file ./install-plan.json --key install-001 --receipt-file ./installation.receipt.json --json
```

CLI объединяет `install-001` с root identity и живой key generation; эти значения возвращаются в ответе для повторов. Expected: immutable sealed capsule, active generation`1`, один InstallationReceipt и terminal intent, exact environment identity. Receipt-file — экспорт committed receipt; его отсутствие после crash не означает отсутствия самого receipt в control store.

Повтор exact команды с тем же key возвращает тот же receipt и generation`1`, без новой установки. После другой активации replay старого key не переключает selector обратно. Подмена plan body при том же key даёт `IDEMPOTENCY_CONFLICT`.

### D. Проверить installed environment

```sh
bag-bootstrap doctor --root ./tools-root --environment-receipt ./installation.receipt.json --json
```

Expected: `environment_ready=true` только для текущей policy и проверенных bytes; fields `source_checked=false`, `run_result=not_run`, `normative_acceptance=not_run`. Это metadata/byte inspection; запуск чужого `--version` до origin verification не допускается. Explicit `doctor --probe` отдельным вызовом выполняет только разрешённые host probes.

### E. Создать минимальный новый проект

```sh
bag-bootstrap project init --root ./tools-root --directory ./demo --identity-root-config ./identity-root.receipt.json --template starter-minimal --environment-receipt ./installation.receipt.json --policy-file ./minimal-project-policy.json --key genesis-001 --json
```

`starter-minimal` разрешается исключительно внутри exact release из receipt, без сети. Policy включает пустой capability set для starter run; не даёт deployment, messaging, FFI, package install hooks. Expected: свежие ProjectId/AuthorityId/GenesisId, exact starter source/lock hashes, genesis journal, open verification obligations и ProjectReceipt. Init не объявляет source принятым и не выполняет run.

Повтор exact key возвращает тот же ProjectReceipt. Новый key на существующем `./demo` даёт `PROJECT_EXISTS`; новый путь со старым ProjectId не является supported argument. Потеря journal при сохранённых identity markers → `PROJECT_RECOVERY_REQUIRED`.

### F. Проверить исходник и собрать

Команда `bagaev` ниже — launcher из exact установленной capsule; по нему известны binary digest и EnvironmentRef. При пути проекта он использует project pin, даже если default selector изменился.

```sh
bagaev --project ./demo source check --json
bagaev --project ./demo build --locked --offline --json
```

Expected source result: parsing/resolution/type/effect checks PASS для настоящих T03/T13; source format/profile exact, entry без аргументов, result Int64, effects empty. BuildReceipt связывает source head, package lock, compiler/runtime/schema refs, semantic profile и resulting ArtifactRef. Missing dependency не подгружается. Не должно быть скрытой записи accepted head либо принятия обязательств, которые этот check не проверял.

Compiler stdout не становится oracle. Golden исход и статические требования получены из заранее зафиксированного StarterDescriptor независимой стороны. Проверяющий сравнивает exact объявленные результаты, не корректирует ожидания после исполнения.

### G. Явно запустить starter

```sh
bagaev --project ./demo run --locked --offline --capabilities none --steps 1024 --output-bytes 4096 --json
```

Для этого starter declared budgets должны покрывать эталонный вычислительный путь; несогласованные release budgets → `RELEASE_INCOMPLETE`, а не увеличение лимита по факту опыта. Физические timeout/memory bounds закрепляются отдельной environment test policy. Logical budget не заменяет wall-time containment.

Expected program observation:

```json
{
  "termination": "Returned",
  "value": {"type": "Int64", "decimal": "42"},
  "application_stdout_bytes": "0",
  "host_calls": [],
  "unsettled_effects": []
}
```

Это точная **проекция** будущего RunReceipt, а не весь wire response. Full receipt дополнительно содержит input refs, LaunchBinding, limits, trace/evidence refs и actual method. CLI exit0; JSON stdout содержит receipt, application stdout пуст; stderr не содержит скрытых credentials. `BudgetExceeded`, `ImplementationStop`, UNKNOWN и вернувшееся `Result.Err` не подменяются значением42.

### H. Перезапустить процессы и повторить осмотр

Остановить launcher/control processes без удаления диска, запустить trusted bootstrap заново. Expected: та же project identity/source/journal/frontier, прежний committed installation receipt, тот же environment pin. Повтор source check/build/run с теми же входами даёт те же объявленные semantic observations; run может иметь новую instance identity, поэтому весь receipt не обязан совпасть byte-for-byte. Невыполненные приёмочные обязательства остаются невыполненными.

Фиксируется результат `CLEAN_INSTALL_ROUTE_PASS` только для exact host/release/profile и выполненной матрицы. Это не `SPEC_READY`, не принятие исходника целиком и не публикация/развёртывание. End-to-end проверка не создает внешние credentials или аккаунты.

## 3. Existing project route

1. Получить exact existing ProjectManifest/lock и существующее authority state; source archive отдельно от history не приравнивается к полному проекту.
2. На новом host установить exact pinned environment через тот же offline closure/trust route. Если release недопустим текущей policy, отказ, а не silent upgrade.
3. `tools attach` проверяет ProjectRef/head/lock/epoch и installed environment, записывает только local association; source/history/debt не меняются. Новый LaunchBinding выпускается отдельным current guarded шагом.
4. Если history отсутствует, `project recover` выполняет R16-authority restore. До valid currentness/complete evidence — read-only/quarantine; init не fallback.
5. Изменение environment pin требует отдельного proposal/CAS/compatibility evidence. Default tools update само по себе не выполняет этот шаг.

## 4. Crash route

Стенд должен внедрять fault **между** стадиями: admission; each staging file; manifest sync; directory publication; source/destination directory sync; SEALED metadata; DB transaction write; durable commit; receipt export; process restart. Для границы внутри настоящего DB/FS нужны соответствующие fault adapter, а не просто исключение Python между чистыми функциями.

Инварианты: active selector указывает только на complete sealed durable closure; receipt и activation не расходятся; old project identity/journal не обнуляются; authoritative lookup разрешает неизвестный исход до нового intent; GC не удаляет reachable closure. Power-loss/full-disk correctness нельзя вывести только из последовательного state-machine теста. Синтетический `restart(state)` использует уже корректный input state и не заменяет disk recovery.

<a id="integration-matrix"></a>
## 5. Будущая интеграционная матрица

Все строки ниже имеют исходный статус **NOT_RUN**. Это условия приёмки реального adapter/release, не дополнительные критерии знаменателя384. Для каждой строки нужны immutable inputs, expected/actual, scope, real method, provider identity и независимый review.

| ID | Испытание | Обязательное наблюдение |
| --- | --- | --- |
| CI-01 | Чистый offline host, полный release | Positive route A–H; exact Int64(42), effects empty |
| CI-02 | Нет одного tool/native blob | OFFLINE_MISSING; нет скрытого PATH/network fallback |
| CI-03 | Повреждение одного byte | ARTIFACT_CORRUPT; без activation |
| CI-04 | Другая architecture/ABI | ENVIRONMENT_UNSUPPORTED/ABI_MISMATCH до execution |
| CI-05 | Недоверенный root / неверная подпись | TRUST_INVALID до исполнения install payload |
| CI-06 | Expired metadata / неизвестное время | TRUST_EXPIRED/TRUST_TIME_UNKNOWN; без force |
| CI-07 | Старые metadata ниже retained floor | Rollback rejected, даже при правильной подписи |
| CI-08 | Path traversal, symlink, duplicate path, file parent | PATH_UNSAFE; ни одного чужого write |
| CI-09 | Несовместимая новая schema или unknown fields | Явный INVALID_INPUT/format refusal |
| CI-10 | ENOSPC/EIO при write/fsync до commit | Старый selector цел; нет success receipt |
| CI-11 | Сбой после capsule publish, до DB seal | Orphan recovered/GC; capsule не active |
| CI-12 | Crash во время commit | Recovery old-or-new transaction; неизвестный caller outcome разрешён lookup |
| CI-13 | Commit сделан, ответ/receipt export потерян | Same-key replay одного receipt, без второго commit |
| CI-14 | Два concurrent plans от одной generation | Ровно один победитель CAS, второй conflict |
| CI-15 | ABA A→B→A | Stale generation plan не проходит |
| CI-16 | Переустановка tools для существующего проекта | Identity/head/journal/pending/effects неизменны |
| CI-17 | Init поверх markers с отсутствующим journal | PROJECT_RECOVERY_REQUIRED; нет нового genesis |
| CI-18 | Stale/неполный backup существующей authority | QUARANTINED; unknown debts не исчезают |
| CI-19 | Current complete restore | Новый epoch, preserved debt/keys/head; old LaunchBinding rejected |
| CI-20 | GC при active/project/running/pending pin | Полный reachable closure сохранён |
| CI-21 | GC/launch race | Pin либо DELETING побеждает атомарно, запуск half-delete невозможен |
| CI-22 | Default tools update при project pin | Проект продолжает exact pinned environment, без migration |
| CI-23 | Нет template/golden или нарушено expected source behavior | TEMPLATE_UNVERIFIED / acceptance FAIL, без подгонки oracle |
| CI-24 | Revocation/permission change перед activation/launch | Current authorization проверена; historical receipt не разрешает новый run |

## 6. Содержимое результата приёмки

`CleanInstallReport` содержит schema/profile; source/contract revisions; host image+capabilities; trusted verifier/root refs; release/environment/template/lock digests; testcase roster; запуск/отказы; complete observation projection; before/after control/project refs; captured fault point; evidence attachments с bytes/hash; chronology; independent golden provenance; scope limits; reviewer disposition. Сам report не подписывает собственную доверенность и не ссылается циклически на свой hash.

PASS требует всех обязательных случаев для объявленного profile и независимой сверки исходов. Любой skipped/unknown обязательный случай остаётся gap. Испытания других ОС/FS не подразумеваются и добавляются вместе с новой support matrix. Экспорт материалов проекта — отдельное действие; report collection не публикует source/credentials автоматически.

В R17 выполнены только проверки ограниченной модели и внутренней согласованности пакета. Реальный CLI, parser/compiler/runtime, signing verifier, filesystem adapter и эта CI-матрица ещё не реализованы и не запускались.
