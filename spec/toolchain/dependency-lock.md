# DEPENDENCY-LOCK-0.1 — точный граф входов сборки

Статус: проект контракта R20 для **всего T13-C02**, не принятый стандарт и не готовый package manager. Дата: 2026-10-22 UTC / 2026-10-23 Europe/Moscow. Формулировка исходного критерия: «Lock определяет точные зависимости, а не плавающие названия». Уточнение выпуска — [release.md](../distribution/release.md). Независимая проверка всего предмета — [release-lock-route.md](../distribution/release-lock-route.md); реальные интеграционные запуски пока `NOT_RUN`.

## 1. Обязательство и область

После успешного `verify_locked` ни компилятор, ни линкер, ни генератор, ни runtime-loader не выбирают версию по имени, диапазону, ветке, тегу, переменной окружения или содержимому текущего registry index. Они получают точный граф, проверенные объекты и таблицу разрешённых импортов. Отсутствие точного объекта вызывает отказ. Изменение зависимости требует отдельной операции обновления и нового LockRef.

V1 этого контракта поддерживает конечный ациклический граф package instances, один выбранный descriptor на `(publisher, name, domain)`, положительные feature requirements и явно объявленные конфликты features. Разные host/target domains могут содержать разные instances. Несколько версий одного package key внутри одного domain, prerelease/build-версии, отрицательные feature conditions, явно запрошенный профиль циклической линковки и неперечислимые динамические imports завершаются `UNSUPPORTED_PROFILE`; они не разрешаются эвристикой. Цикл в одной пробной assignment устраняет эту ветку поиска, но не мешает выбрать другую ациклическую assignment (§4.2). Это явная граница package profile, а не заявление о полной готовности языка V1, ABI или FFI.

Полные байты SourceBundle/SourceIR, MeaningLock, Environment, ABI/effect interface и toolchain из предшествующих задач должны поступать извне с точными версией, codec и digest. R20 не подменяет их выдуманным исходным синтаксисом. До появления этих входов производственный маршрут имеет `INPUT_NOT_READY`.

## 2. Тождество, байты и метаданные

`ObjectRef = {kind, format, codec, sha256, bytes}`. Digest — SHA-256 **ровно сохраняемых байтов**, размер — каноническая десятичная строка без ведущих нулей, максимум uint64. `kind/format/codec` участвуют в проверяемом типе ссылки. Одинаковый digest в неверном kind не разрешает type substitution. Это outer byte-integrity reference: он не заменяет внутреннюю semantic identity другого формата. В частности, R19 MeaningLock использует собственный domain-separated hash; decoder проверяет и outer bytes, и его native identity по закреплённому codec, без приравнивания двух digest. Расположение, URL, тег, registry hostname и имя файла не входят в content identity; доверие происхождению проверяется отдельно.

Внутренние метаданные R20 используют `BAG-META-JSON-1`: UTF-8 без BOM; только ASCII object keys; duplicate keys, unknown required semantics, NaN, floats, lone surrogates и неканоническая запись запрещены. Числовые счётчики передаются строками, версии — тройками таких строк. Keys сортируются по ASCII; пробелы вне строк отсутствуют; boolean/null имеют JSON spelling; строки кодируются UTF-8 без NFC-преобразования, `"`, `\\` и U+0000..001F экранируются, для controls применяется `\u00xx` с lowercase hex. Arrays сохраняют порядок; поля, обозначенные множествами, заранее сортируются по каноническим байтам элемента и не содержат повторов. Проверяющий повторно кодирует объект и сравнивает байты. Внешние кодеки не перекодируются в этот профиль незаметно.

Content Ref объекта находится во внешнем envelope, не в хешируемом теле самого объекта. Порядок создания: source bundle/descriptors/resolution rules → manifest/catalog snapshot → lock body → PackageInterfaceClosure → final MeaningLock/Environment → SourceVersionBinding/acceptance → build plan. Final MeaningLock зависит от exact selected closure; Manifest поэтому фиксирует только независимый `resolution_contract_ref`, не final MeaningLock. PackageInterfaceClosure связывает LockRef и exact node/source/interface/feature projections, а не только похожие ABI signatures. Изменение package bytes меняет эту closure даже при том же interface.

SourceBundle — неизменяемые authored source/config bytes до resolve; он не включает generated Manifest/lock/binding, receipt, output или собственный inventory. Derived metadata монтируются отдельно; попытка читать исключённый undeclared input отвергается. Typed/linked IR возникает после разрешения и не является предварительным manifest input. Свидетельство проверки LockRef не включается в тело того же lock. Transport signatures/locators — отдельные objects. Корень inventory содержит точные refs, но не собственный ref. Попытка построить cyclic content dependency между этими objects — INPUT_NOT_READY/INVALID_OBJECT_GRAPH, а не поиск hash fixed point.

### 2.1 Что фиксируют объекты

| Объект | Обязательные поля и смысл |
| --- | --- |
| Manifest | `profile`, exact SourceBundleRef/resolution-contract ref, root requirements, declared target matrix, explicit build recipe ref, toolchain input requirements, required feature set; только пожелания до resolve |
| CatalogSnapshot | identity/version of trusted catalog adapter, exact descriptor refs and immutable alias expansion table, catalog origin evidence refs; полный конечный каталог конкретного resolve, не живой HTTP endpoint |
| PackageDescriptor | package key, version, exact source ref, source kind, nominal namespace identity, supported domains, dependencies with stable local import names, feature declarations/implications/exclusions, interface refs, declared build inputs and recipe refs |
| LockBody | profile, ManifestRef, CatalogSnapshotRef, resolver identity and policy ref, target domains, sorted root bindings, node bindings, exact dependency edges, build-input refs, exact update-parent/ref or `null`, declared bounds |
| LockNode | instance ID, package key/domain, version, DescriptorRef, SourceRef, activated features, exact nominal namespace ref, ABI/effect interface refs |
| LockEdge | source package instance, stable import name, dependency role, exact target instance, activated-by descriptor clause ID, requirement digest; только descriptor node→node, roots хранятся отдельно |
| LockVerification | LockRef, verifier identity/profile, recomputed closure root, validated input inventory ref, result and bounded diagnostics; хранится отдельно |
| Materialization | LockRef, exact input inventory ref, tree rules/profile, mount mapping, fetched-byte checks, origin policy result; не предоставляет execute или publish capability |

`instance_id = sha256(canonical({package_key, domain, version, descriptor_ref, source_ref, features, nominal_namespace_ref, interfaces}))`. Edges не входят в node identity: они целиком связаны LockBody. Так node IDs не образуют рекурсивную хеш-ссылку. Несовпадение пересчитанного ID — `LOCK_INVALID`.

`domain` — точная тройка `role ∈ {build,host,target}`, `platform_ref`, `abi_profile_ref`; сравнение по полному typed ref. Cross-compilation tool исполняется только в соответствующем host/build domain, а не автоматически в domain генерируемого артефакта. Linker получает explicit instance-to-symbol namespace mapping. Разные nominal namespaces не отождествляются по совпадению текста имени или представления значений.

### 2.2 Ограничения версий и features

Версия V1 — `[major,minor,patch]`, каждое 0..4294967295; порядок числовой лексикографический. Constraint — disjunction не более 16 conjunctions, каждая не более 16 atoms `{op ∈ eq,lt,le,gt,ge, version}`; пустая conjunction означает любую stable version, пустая disjunction запрещена. Синтаксический сахар `^`, `~`, `*` может быть UI-командой только после явного разворачивания в эти atoms; lock хранит результаты и exact requirement refs. Resolver никогда не интерпретирует строковый semver по библиотеке с неопределёнными настройками.

Каждый feature — локальное ASCII-имя. Root и dependency clauses требуют конечные sets. Root requirements безусловны; optional activation в descriptor относится к feature исходящего instance, а features requirement — к целевому. Global Manifest.features зарезервирован пустым в V1; точные compiler flags задаёт recipe. Descriptor задаёт implications `f → g`, optional dependency activation `f → edge`, и pairwise exclusions. Default features существуют только как явно переданный set; ambient default отсутствует. Features выбранного instance — наименьшая неподвижная точка объединения требований всех входящих активных edges и descriptor implications. Включение нового feature может добавить constraint/edge и заставить solver пересмотреть предыдущий выбор. Конфликт exclusions либо неизвестный feature — причина конфликта, не молчаливое отключение feature. Пустой root set допустим: package nodes/edges тогда пусты, но exact compiler/runtime/build inputs по-прежнему обязательны.

## 3. Операции и результаты

| Операция | Вход | Успех | Отказы и мутация |
| --- | --- | --- | --- |
| `resolve` | ManifestRef, verified CatalogSnapshotRef, resolver/policy refs, bounds | новый immutable LockRef, resolution trace ref, closure inventory ref | UNSAT только после полного поиска в данном конечном snapshot; UNKNOWN_LIMIT; invalid/untrusted input; прежний lock не меняется |
| `update` | то же + old LockRef + explicit mutable key set U | новый lock, точный diff nodes/edges/features/build inputs | OUT_OF_SCOPE_UPDATE, PIN_CONFLICT, UNSAT, UNKNOWN; automatic expansion U запрещён |
| `verify_locked` | ManifestRef, LockRef, exact descriptors, policy, supported semantics | LockVerification with closure and exact import map | MISSING/INVALID/UNSUPPORTED; resolver не вызывается, lock не пишется |
| `fetch_locked` | verified lock, exact missing refs, allowed locator/origin policy, network grant | content store entries после size/digest/origin checks | bytes not found/corrupt/untrusted, limits, network denied; никакого выбора версии |
| `materialize` | verified lock + complete local input objects + tree profile | isolated immutable tree/mount inventory | INPUT_NOT_READY, TREE_INVALID, PATH_COLLISION, unsupported platform; без сети и hooks |
| `plan_locked_build` | accepted/selected exact source, verified lock, environment/toolchain/recipe/target refs | BuildPlan с exact closed inputs и effect policy | stale manifest/source, missing inputs, unsupported ABI/effects; публикации нет |

Resolve/Update могут иметь сетевую подготовку catalog/source, но она отдельная, явно разрешённая, завершающаяся immutable snapshot **до** поиска. Сам поиск чистый и конечный. Нельзя обращаться к live registry при backtracking. Fetch скачивает только уже названный exact ref; HTTP response с другим content digest не становится «подходящей новой версией».

`ResolveResult` содержит `status ∈ SOLVED, UNSAT_SNAPSHOT, UNKNOWN_LIMIT, INVALID_INPUT, UNTRUSTED_INPUT, UNSUPPORTED_PROFILE`, exact request/snapshot refs, deterministic work counters, lock/trace refs только когда они существуют. `UNSAT_SNAPSHOT` не утверждает отсутствие решения в других registry snapshots. Статус `INPUT_NOT_READY` используется до начала операции при отсутствии обязательных upstream bytes. Для всех результатов диагностики ограничены и содержат IDs причин, а не бесконечный обход.

## 4. Конкретный resolver V1

### 4.1 Preflight

1. Проверить typed refs, canonical bytes, catalog trust по текущей политике, уникальность descriptor identity. Два descriptor с одним `(publisher,name,version,domain)` и разными source/interface/descriptor bytes — `CATALOG_EQUIVOCATION`. Их нельзя выбирать по меньшему hash.
2. Развернуть alias таблицу snapshot ровно один раз. Локальные aliases уникальны в scope; alias cycles/ambiguity отвергаются. Результат — explicit package keys, не URLs. Зафиксировать исходные constraints и root domain mapping.
3. Проверить bounds и допустимый профиль. Unsupported constraint, feature expression, native mechanism или dynamic resolver hook даёт отказ до выполнения кода package.
4. При update проверить old lock независимо. Для каждого его key вне U сделать exact descriptor/source/features/domain pin; старые build/toolchain inputs вне явно отдельного update scope также pinned. Исчезновение неиспользуемого узла допустимо лишь как явно перечисленная garbage removal в diff; изменение surviving key запрещено. Новый key, возникающий только из изменённого узла, должен входить в заявленный `allow_new` set; иначе `OUT_OF_SCOPE_UPDATE`. Автоматическое «разблокирование всего дерева» отсутствует.

### 4.2 Поиск

State поиска — partial assignment package key/domain→descriptor и decision stack. Derived constraints/features/edges всегда пересчитываются из roots и assignment, не переносятся из отменённой ветки.

```text
search(assignment):
  charge decision visit; on exhausted bound return UNKNOWN_LIMIT
  closure := propagate_from_roots(assignment)
  if closure violates assigned descriptor/feature/pin constraints:
      return CONFLICT(reason_ids)
  if no unassigned reachable keys:
      if dependency cycle (including self-edge): return CONFLICT(CYCLE)
      if exact interface checker unavailable: return INPUT_NOT_READY
      if interface semantics unsupported: return UNSUPPORTED_PROFILE
      if checker proves host/target/ABI/effect mismatch: return CONFLICT(INTERFACE)
      return COMPLETE(closure)
  domains := all admissible candidates for each reachable unassigned key
  if some domain empty: return CONFLICT(key, all restricting reasons)
  key := smallest (candidate_count, canonical_package_key, canonical_domain)
  for candidate in domain[key] sorted by descending numeric version:
      result := search(assignment plus exact candidate)
      if COMPLETE: return result
      if UNKNOWN_LIMIT or INPUT_NOT_READY or UNSUPPORTED_PROFILE: return result
      retain bounded conflict trace
  return CONFLICT(all tried candidates and their reason refs)
```

`propagate_from_roots` начинает с root requirements, сортированной очереди `(key, clause_id, feature)` и пустых derived sets. Для каждого assigned reachable descriptor применяет только активные clauses, добавляет requirements/features/edges, пока ни один set не растёт. Повторный элемент множества не добавляет работу; проверка entailment и просмотр каждого clause всё равно учитываются в work counter. При неподходящем assigned candidate возвращается conflict, а не принудительная замена. При backtrack propagation начинается заново; dead nodes предыдущей ветки исчезают. Rootless extra nodes в итоговом lock запрещены.

Первое решение в заданном порядке — выбранное. Новая циклическая версия может быть отброшена в пользу старой ациклической. Если исчерпаны все assignments, результат `UNSAT_SNAPSHOT` означает отсутствие решения **в объявленном DAG-профиле и данном snapshot**; trace отдельно показывает CYCLE/INTERFACE conflicts. Это не утверждение невозможности циклического linking в другом профиле. Недоступная ABI/effect семантика или metadata не считаются conflict и не позволяют перебрать менее изученный вариант: весь request останавливается INPUT_NOT_READY/UNSUPPORTED. Циклы feature implications допустимы: конечные sets сходятся к наименьшей неподвижной точке; это не package dependency cycles. Параллельный solver допустим только если выдаёт то же решение и deterministic logical counters либо имеет другой explicit resolver profile. Wall-clock cutoff может остановить поиск с UNKNOWN; не меняет UNSAT в успех. Сложность общего поиска экспоненциальна; ограниченность входов и work обязательна.

### 4.3 Завершение

1. Пересчитать closure, feature fixed point, domains и edges из окончательного assignment независимым locked verifier (§5).
2. Построить stable node IDs, sorted root bindings/edges, complete build-input inventory и canonical LockBody. Сохранить body; вычислить LockRef.
3. Сохранить trace и verification отдельно. Успех resolution не равен доверенной сборке и не делает origin evidence вечным.
4. Локальную указательную запись project lock обновлять только CAS по ожидаемому previous LockRef/working version. Конкурирующее редактирование — `STALE_BASE`, созданные immutable bytes можно оставить unreachable до GC. Acceptance состояния исходника выполняется своим контрактом.

## 5. Locked verification без повторного решения

Verifier не смотрит на «последние версии». Он читает ManifestRef, LockBody и названные descriptor/source metadata refs. Catalog нужен для проверки сохранённого resolution provenance и origin policy, но current registry contents не могут заменить узел. Если первоначальный snapshot требуется trust policy и недоступен, получается INPUT_NOT_READY.

Алгоритм:

1. Проверить size/hash/kind/format/codec каждого входа; запретить неизвестные семантические поля. Сверить ManifestRef, resolution contract и target matrix с фактической командой. Для build/release дополнительно проверить, что final MeaningLock.PackageInterfaceClosure выведена именно из этого LockRef, а его resolution rules совпадают с Manifest. Результат для чужого manifest/source не принимается.
2. Проверить uniqueness keys/instance IDs/import names, canonical order и вычислить IDs заново.
3. От roots пройти **объявленные descriptors** и вывести минимальный feature closure и требуемые edges. У каждого активного requirement должна существовать ровно одна lock edge с подходящими key/domain/version/features. Каждый edge должен иметь действительный source clause. Сравнить полные множества derived и stored nodes/edges/features; лишние и недостающие entries запрещены.
4. Проверить exact nominal identities и interfaces; алгоритм проверки ABI/effects вызывается по точной upstream версии. Если семантика недоступна/неподдержана, `UNSUPPORTED_PROFILE`/`INPUT_NOT_READY`, не `compatible=true` от вызывающего.
5. Проверить DAG через deterministic Kahn (очередь по instance ID); остаток означает CYCLE. Строить топологический порядок независимо от сохранённого порядка.
6. Замкнуть build-input graph: compiler/linker/stdlib/generator/FFI data/sysroot/plugins и platform image — exact refs с declared roles. Любой transitive dependency tool сам является input. Полнота declarations подтверждается enforced sandbox/build adapter, а не лишь перечнем в JSON.
7. Вернуть exact import map и verification evidence. Компилятор имеет доступ только к mapped declared imports. Ambient `PATH`, parent directories, global node/module cache и mutable registry не участвуют.

Линейный обход графа сам по себе не доказывает честность package descriptor. Trust/origin и фактическая изоляция выполнения — отдельные предпосылки; их неизвестность блокирует квалификацию сборки как closed/reproducible.

## 6. Source acquisition и деревья

Все fetch операции требуют текущего разрешения для network target и ограничений размера; credentials не являются частью lock и не передаются новому origin при redirect без отдельного разрешения. Локальный cache ищет exact content ref, затем повторно проверяет bytes. Trusted mirror допустим только по отдельной locator/origin policy; он не может подменить content identity.

Source profiles:

| Источник | Что обязательно pinned | Что запрещено в locked mode |
| --- | --- | --- |
| Registry archive | exact archive ref + extracted TreeRef + extraction-profile ref + origin evidence | новый архив под тем же version label, install scripts, fallback package |
| Git snapshot | full repository object algorithm/commit ID + independent TreeRef + every submodule/LFS object ref + fetch profile | branch/tag как identity, незамеченные submodules, smudge/clean hooks, live checkout |
| Local path/workspace | immutable snapshot TreeRef + exact selection rules + captured file refs | чтение живого path в процессе сборки, скрытые parent imports |
| Generated/native | generator/tool refs + exact recipe/input refs + environment + output refs after execution | поиск `cc`/linker в текущем PATH, скачивание SDK внутри script, runtime-loaded unpinned library |

`BAG-TREE-1` — sorted inventory of relative portable ASCII paths и exact file refs. Каждый path segment состоит из `[A-Za-z0-9._-]`; non-ASCII path явно UNSUPPORTED_PROFILE (это ограничение имён файлов данного профиля, не строк языка). Root `.` не entry. Пустые segments, `.`/`..`, absolute paths, NUL, backslash, duplicate path и ASCII case-fold collision запрещены; fold определён ровно как A..Z→a..z без зависимости от locale/Unicode version. File/ancestor conflict также запрещён: file `a` и file `a/b` не могут сосуществовать, в том числе после ASCII fold. Symbolic/hard links, device/FIFO/socket entries, trailing dot и Windows reserved base names `CON,PRN,AUX,NUL,COM1..COM9,LPT1..LPT9` (без учёта ASCII case, до первого `.`) отвергаются. Files имеют только executable bit или non-executable mode; timestamps/UID/GID/ACL не являются входом и materializer задаёт fixed values. Directories выводятся из paths, их metadata фиксирована. Archive link/path entries проверяются до записи; extraction идёт в новый staging root, без следования существующим links. Затем повторно вычисляются tree inventory и TreeRef. Platform, не обеспечивающая правила, отказывается. Будущий Unicode-path profile обязан pin normalization/casefold version; BAG-TREE-1 его не подразумевает.

Для Git/path captured snapshot включаются выбранные bytes, executable bit и exact inclusion policy; игнорирование файла по ambient `.gitignore` недопустимо. Если рецепт читает файл вне captured tree, adapter выдаёт `UNDECLARED_INPUT` и сборка не получает successful closed status. Нельзя сначала дать процессу полный filesystem, а после записать только замеченные reads.

`fetch_locked` не является `build`, `install` или `publish`. Lifecycle hooks отсутствуют в materialization. Нужный генератор становится явным отдельным build step с declared effects, exact code/input refs и новым output evidence. Secret input, способный влиять на bytes, несовместим с публичным воспроизводимым профилем без отдельного confidential-input contract; публиковать secret/digest secret по умолчанию запрещено. V1 отвергает такой build profile.

## 7. BuildPlan, reproducibility и двунаправленная связь

BuildPlan фиксирует SourceRef, AcceptedSourceRef если цель release, MeaningLockRef, LockRef, EnvironmentRef, recipe/toolchain refs, target, declared input inventory, compiler flags, locale/timezone, deterministic time/random policy, filesystem layout, allowed observations/effects и budget. Отсутствующее поле не берётся из окружения.

Нормативные результаты различаются:

- `LOCK_VALID`: полный declared graph согласован; это не факт исполнения.
- `INPUTS_MATERIALIZED`: все exact bytes доступны и сверены, origin/trust policy выполнена на указанном epoch.
- `BUILD_SUCCEEDED`: конкретный build invocation завершён по указанному adapter/profile, outputs exact.
- `INPUT_CLOSED`: adapter реально ограничил процесс объявленными входами и эффектами; аудит самого adapter остаётся предпосылкой.
- `REPRODUCED`: независимый invocation на declared supported environment дал те же сравниваемые artifact bytes; профиль сравнения указан, hidden normalization запрещена.

`INPUT_CLOSED` не влечёт `REPRODUCED`: compiler может зависеть от scheduler, nondeterministic backend или аппаратных особенностей. Если output сравнивается после нормализации, нормализатор pinned как отдельный transformation; raw artifacts и normalized artifacts имеют разные refs. SLSA provenance полезен как переносимое evidence, но его список dependencies не принимается за доказательство complete lock (§10).

Для bagaev package edge входит в структурный граф зависимостей. Изменение exact node/interface/features/recipe помечает затронутые MeaningLock/program/check/run/release evidence как stale согласно их declared footprints. Старое успешное свидетельство не переносится на новый lock по равенству имени пакета. Обратный запрос «почему этот binary зависит от X?» идёт candidate→build result→plan→LockRef→edge clause→descriptor/source. Предлагаемая правка package constraint сначала создаёт candidate lock/diff, а затем новый проверяемый исходник; remote публикация от этого не возникает.

## 8. Bounds, ошибки и атомарность

Default V1 limits: 4 MiB canonical Manifest, 64 MiB CatalogSnapshot metadata, 64 MiB LockBody; ≤4096 keys, ≤64 candidates/key, ≤32768 edges, ≤256 features/descriptor, ≤16 target domains, ≤1,000,000 search visits, ≤10,000,000 clause/feature evaluations. Work counters — uint64, checked addition; overflow=UNKNOWN_LIMIT. Tree: ≤100000 files, ≤16 GiB total uncompressed, ≤256 MiB/file, depth≤64, relative path≤1024 UTF-8 bytes. Context may reduce limits; raising them requires exact policy profile in request. Output/diagnostic transport caps are separate from object caps.

Before publishing a local state pointer, serialize/measure complete post-state and response/receipt envelope. Capacity rejection leaves pointer/version/receipts unchanged. Large existing immutable objects need not be embedded in response: exact refs are returned. Partial fetched blobs remain quarantined and cannot enter verified inventory. Crash before project-pointer CAS leaves old lock active; crash after CAS is recovered by exact transaction/receipt lookup under R16. Resolver retries use the same exact snapshot/request; a newer snapshot is a different operation.

| Code | Значение и дальнейшее действие |
| --- | --- |
| LOCK_MISSING / INPUT_NOT_READY | Получить конкретные missing refs; locked build не переходит к resolve |
| LOCK_INVALID / HASH_MISMATCH / TYPE_MISMATCH | Отвергнуть объект; не исправлять silently |
| MANIFEST_MISMATCH / STALE_BASE | Новое explicit resolve/update или повторная подготовка по новой базе |
| CATALOG_EQUIVOCATION / UNTRUSTED_INPUT | Не выбирать произвольный источник; требуется разрешение origin/conflict по отдельной политике |
| UNSAT_SNAPSHOT | Полный поиск исчерпан в заданном finite snapshot; diagnostic trace связывает clauses |
| UNKNOWN_LIMIT | Не сделан вывод о существовании решения; можно увеличить explicit budget новым request |
| PIN_CONFLICT / OUT_OF_SCOPE_UPDATE | Показать exact scope diff, пользователь/делегированная политика выбирает новый scope |
| UNSUPPORTED_PROFILE / CYCLE | Профиль явно не реализован; автоматического downgrade нет |
| UNDECLARED_INPUT / EFFECT_DENIED | Invocation не получает closed/success evidence; побочный эффект обрабатывается по runtime effect contract |

## 9. Независимая проверка всего критерия

Stage2 требует контракт и воспроизводимый метод; stage3 требует выполнения метода на настоящих форматах/инструментах во всей объявленной области. Проверяющий строит closure из descriptors, а не доверяет полю `complete=true`; использует отдельный resolver/constraint enumerator на exhaustive small graphs и metamorphic cases на больших. Перестановка входов не меняет LockRef; смена текущего registry alias после resolve не меняет locked build; удаление transitive edge, source substitution, host/target confusion, feature activation и narrow update должны давать установленный результат. Нужны реальные sandbox read/exec/network traces и два независимых builds, включая отказ при missing bytes. Все классы и ожидаемые наблюдения перечислены в [integration route](../distribution/release-lock-route.md).

Конечный RELEASE-LOCK-FINITE-0.1 эксперимент проверяет только маленькую часть этих правил. Его pure serial engine не реализует native compiler, registry trust, Git/archive materializer, full feature solver, multi-platform ABI, OS isolation или crash consistency. Ни число его проверок, ни schema acceptance не дают stage3 всему T13-C02.

## 10. Источники и проектные решения

- [Cargo: manifest versus lock](https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html) показывает различие broad dependency requirements и exact selected revisions. В R20 дополнительно фиксируются domain/interface/recipe/evidence связи bagaev.
- [Cargo build](https://doc.rust-lang.org/cargo/commands/cargo-build.html) разделяет locked/offline/frozen и предупреждает, что offline resolution может зависеть от локально доступных packages. Поэтому наш verify/build не запускает даже offline resolver; explicit offline update имеет собственный snapshot.
- [npm ci, CLI v11](https://docs.npmjs.com/cli/v11/commands/npm-ci/) документирует frozen install и отдельную настройку lifecycle scripts. Наш materialize contract запрещает hooks, а нужные генераторы выносит в declared build steps.
- [SLSA v1.2 Build Provenance](https://slsa.dev/spec/v1.2/build-provenance) считает completeness `resolvedDependencies` best effort даже через Build L3. Поэтому наличие provenance здесь не заменяет полную проверку графа и enforced input closure.

Источники прочитаны 2026-10-22 UTC. Это первичные основания отдельных ограничений; конкретные структуры/алгоритмы DEPENDENCY-LOCK-0.1 являются проектом bagaev и не приписываются внешним стандартам. Content addressing и lock files сами по себе не заявляются новым изобретением.
