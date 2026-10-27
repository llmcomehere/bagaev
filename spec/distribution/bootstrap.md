# Установка, окружение и создание проекта

**BOOTSTRAP-0.1 · R17 · проект контракта · 23 октября 2026 (Москва).** Предмет: исходный [T18-C04](../../registry/tasks/T18-release-ecosystem.md), «Чистая установка и создание минимального проекта имеют проверяемый маршрут». Это самостоятельное дополнение к ТЗ. Оно не утверждает наличия выпущенного дистрибутива, запуска языка на чистой машине или согласования с недоступными байтами R08–R15. Полная основа языка не расширяется.

«Обязан» в этом документе означает правило предлагаемого контракта после его принятия. Нормативная приёмка и готовность конкретной реализации фиксируются отдельно. Имена команд ниже — предлагаемый интерфейс; они не являются уже установленными командами. Общие границы повторов и восстановления взяты из сохранённого [R16](../protocol/idempotency-lifecycle.md). Его историческая независимая рекомендация стадии 2 не равна принятию.

## 1. Результат и четыре независимых состояния

Установка должна позволить человеку или агенту получить проверенный набор инструментов, создать минимальный новый проект, проверить его и явно запустить. Для этого нужно различать:

| Предмет | Что фиксируется | Что из этого не следует автоматически |
| --- | --- | --- |
| Release | Происхождение, точные артефакты, версии форматов и платформа | Последняя доступная версия или право выполнять действия проекта |
| Environment | Неизменяемый замкнутый набор инструментов и зависимостей | Принятие исходника и изменение проекта |
| Installation | Проверка среды на конкретном host и транзакционное включение | Восстановление прежней authority |
| Project | Новая уникальная identity либо восстановленная история существующей | Публикация, развёртывание и разрешение неизвестных эффектов |

Ключевое предложение: **EnvironmentRef отдельно от ProjectRef; LaunchBinding связывает их только на конкретный запуск.** Установка новой версии default-инструментов не меняет проектный lock. Возврат к старой среде создаёт новую install generation, а не откатывает счётчик и состояние проекта.

### 1.1. Объявленная первая платформа

Предлагаемый install profile `BAG-INSTALL-LINUX-X64-1`: Linux, little-endian x86-64 с базовым набором x86-64-v1, kernel не ниже 5.10, один владелец installation root, локальное файловое хранилище. Дистрибутив несёт замкнутый executable runtime closure; недекларированные динамические библиотеки из host запрещены. Compiler, runtime, CLI, библиотеки и native dependency versions записываются точными digest; числа здесь не означают, что такие binaries уже собраны.

Поддерживаемый storage adapter требует корректных file/directory sync, локальной межпроцессной блокировки, транзакционного CAS, атомарного создания без замены и доступа через защищённый root. Для эталонной реализации предлагается local ext4 либо XFS с явно проверенной конфигурацией; NFS/SMB/FUSE, произвольный overlay, удалённая shared database и Windows/macOS находятся вне первого install profile. Это ограничение поставки, а не исключение возможностей языка. Наличие подходящего имени FS не доказывает исправность носителя. Поддержка profile означает результаты будущей платформенной матрицы, а не текущего Python-опыта.

Проверяются архитектура, ABI closure, необходимые системные возможности, достаточность объявленных ресурсов, права владельца, доступность durable operations и отсутствие конфликтующих корней. Неизвестная capability даёт `ENVIRONMENT_UNSUPPORTED`; нельзя продолжать с ослабленным режимом, сохранив прежнюю метку profile. Контейнер допускается только с отдельным проверенным storage/host profile, не по одному признаку Linux.

## 2. Форматы и идентичности

В install wire используются UTF-8 JSON без duplicate keys, unpaired surrogate, нечисловых значений и неизвестных полей. Семантические counters — decimal strings `0..9223372036854775807`; `bool` числом не является. Переполнение даёт `LIMIT_REACHED`, без wrap. Объекты для digest кодируются каноническим JSON из R16 (CJ-INT-1); profile-specific arrays сортируются только где это явно указано. Даты, случайные operation IDs и абсолютные пути не входят в content identity среды.

SHA-256 здесь идентифицирует bytes, а происхождение подтверждается отдельным доверенным механизмом. Digest не считается подписью или доказательством отсутствия уязвимостей. Нельзя вычислять identity через поле, содержащее эту же identity. Направление content refs: EnvironmentLock → ReleaseDescriptor → StarterDescriptor → portable package lock/source bytes. Portable starter lock не содержит enclosing EnvironmentRef, будущий ProjectId или GenesisReceipt; эти поля появляются только в сгенерированном ProjectManifest после genesis. ReleaseDescriptor не включает enclosing EnvironmentLock hash. Это предотвращает цикл даже при шаблоне проекта с lock-файлом. Подпись, TUF target metadata и attestation, subject которых содержит digest release, хранятся отдельными envelopes: ReleaseDescriptor не включает их hashes. Его provenance policy может описывать требования к таким evidence, не ссылаясь на свой подписанный результат.

| Тип | Обязательные данные |
| --- | --- |
| `ArtifactRef` | `sha256`, точный `size_bytes`, media type; для файла ещё relative path и режим |
| `FormatRef` | имя формата, точная revision, schema/semantic-contract digest |
| `ReleaseDescriptor` | schema revision; release label; status; platform profile; tool inventory; closure graph; environment policy; format matrix; starter; verification-suite refs; provenance policy ref (trust envelope отдельно) |
| `EnvironmentLock` | profile; exact release descriptor digest; полный отсортированный список ArtifactRef и dependency edges; compiler/runtime/CLI/stdlib refs; допустимые format refs; build recipe ref при наличии |
| `EnvironmentRef` | SHA-256 canonical EnvironmentLock; lock body не содержит этот digest |
| `InstallPlan` | stable InstallKey; intent body digest; EnvironmentRef; root identity; base install generation; trust snapshot ref; capacity plan; mode; exact declared actions |
| `InstallationReceipt` | InstallKey, intent digest, EnvironmentRef, committed generation, verification report refs, observed host profile, trust decision ref, commit ref |
| `ProjectIdentity` | свежий ProjectId, GenesisId, AuthorityId; не зависит от имени каталога или EnvironmentRef |
| `ProjectManifest` | ProjectIdentity; format refs; working source head; accepted head (nullable); package lock ref; pinned EnvironmentRef; initial policy; authority mode; journal/frontier refs |
| `LaunchBinding` | ProjectRef; source head; package lock; EnvironmentRef; authority epoch; effective policy digest; work/operation guard; launch nonce |
| `StarterDescriptor` | точный template artifact; полный file inventory; source format/profile; package lock; entry; static expectations; runtime golden outcome; provenance независимого golden |

[Структурная схема](release-input.schema.json) закрывает поля ReleaseDescriptor, EnvironmentLock и StarterDescriptor. Она проверяет форму; алгоритм ниже дополнительно проверяет семантические связи, реальные bytes, authority/trust и ресурсные ограничения до аллокации. Все ссылки включают тип/формат и exact digest либо authority-qualified ID. Нельзя заменить missing digest строкой `latest`, semver range, URL без ожидаемого hash или именем доступного executable из PATH. Сетевой адрес — locator, не identity.

### 2.1. Проверка графа closure

`verify_closure(lock, release, available)` выполняет конечный обход графа от всех tool roots и starter roots. Каждый узел должен иметь ровно одно описание, все ссылки разрешаться, sizes/hashes совпадать. Файл, требуемый tool, но не достижимый из объявленного closure, означает `RELEASE_INCOMPLETE`. Orphan artifacts не добавляются в execution closure автоматически. В closure допускаются циклы метаданных зависимостей, если все nodes конечны и каждый blob независим; обход ведёт visited set. Циклические вычисления content digests и неразрешённые build recipes запрещены.

Список файлов внутри capsule проверяется отдельно: точные bytes, режимы только regular file или directory; никаких symlink/hardlink/device/FIFO/socket entries, absolute paths, `..`, empty components, NUL, двусмысленного повторного пути. Устанавливаемые пути ограничены ASCII `[A-Za-z0-9._/-]`, компонент не равен `.`/`..`, длина компонента ≤128, весь relative path ≤1024 bytes. В FileEntry schema перечисляются regular files; необходимые directories выводятся из уникальных parent prefixes, создаются внутри private staging и перед seal получают mode0555. Пустые/лишние directory entries отвергаются. Отдельные directory entries входного архива могут лишь совпасть с этим набором и не создают дополнительных объектов. Case-sensitive profile; изменение file inventory через Unicode normalization не допускается. Порядок unpack не должен позволить file-as-parent. Каждая запись создаётся относительно уже открытого staging root, no-follow/no-replace; containment проверяется перед каждой записью, а не только строковой нормализацией.

Пределы предлагаемого profile: descriptor ≤4 MiB, depth≤32, ≤100000 JSON nodes; ≤4096 blobs, ≤65536 файлов, один blob≤1 GiB, общий unpacked размер≤8 GiB, metadata/diagnostic response≤256 KiB. Resource reservation рассчитывает staging+sync overhead+control DB reserve; bounded free-space probe не гарантирует отсутствие ENOSPC позже. Превышение limits диагностируется до соответствующей аллокации. Ограничения профиля не выводятся из результатов benchmark.

### 2.2. EnvironmentLock не является InstallationReceipt

Lock описывает portable content; receipt — факт конкретной установки. В lock отсутствуют host paths, hostname, wall-clock timestamps, credentials, ProjectId и install generation. В receipt могут быть локальные пути и timestamps с заявленной областью доступа; по умолчанию экспорт отчёта их редактирует. Подписанный lock не даёт гарантию reproducible build: повторная установка готовых одинаковых bytes и независимая воспроизводимая сборка — разные проверки.

## 3. Доверие перед исполнением

### 3.1. Объявленные доверенные входы

Чистая установка начинается не с самопроверяющегося неизвестного скрипта. Входы: доверенный host/OS профиль, ранее проверенный bootstrap verifier, trusted root metadata, явная политика доверия и монотонная информация о ранее принятых metadata versions там, где она уже существует. Происхождение verifier/root устанавливается независимым каналом поставки или доверенным администратором; сам скачанный bundle не объявляет себя собственным trust anchor. В ТЗ нет вымышленного уже опубликованного ключа bagaev.

Предлагаемый repository trust adapter — TUF с зафиксированным POUF, root chain и версиями библиотеки в release tooling lock. Клиент проверяет metadata signatures/thresholds, последовательное обновление root, snapshot/targets bindings, rollback floors и срок действия. Основание выбора — [TUF specification](https://theupdateframework.github.io/specification/latest/), просмотренная редакция 1.0.37 от 8 октября 2026; документ TUF прямо оставляет начальный bootstrap доверия внешней системе. Принятие конкретного POUF/implementation и ключей — отдельная зависимость выпуска.

Host adapter предоставляет достоверный time interval `[lower, upper]`; metadata действительно только если весь интервал лежит до expiry и не нарушен lower bound. Если время нельзя обосновать, `TRUST_TIME_UNKNOWN`. Бесконечный срок metadata ради offline режима не вводится. Одна операция проверки фиксирует time snapshot; длительная подготовка требует повторной проверки актуальности перед новой активацией.

### 3.2. Offline режим

Default install route `--offline`: fetch недоступен; `plan` возвращает полный отсортированный список missing artifact refs. Клиент ничего не подгружает скрыто из сети, системного package manager, кэша другой версии или PATH. Если список не помещается в ответ, выдаётся exact report ref и snapshot-bound pages, с `complete=false` у неполного ответа.

Offline допускает проверку заранее доставленного комплекта при действительных trust metadata и известной политике. Он не доказывает `latest` и не обнаруживает обновление, о котором host не получил сведений. Restore старого trust DB вместе с bundle не обнуляет rollback floors: нужен актуальный внешний trust state либо явно новый изолированный installation root с честно объявленной границей истории доверия. Даже новый root не получает права старой ProjectIdentity.

Для воспроизведения исторического release отдельная reviewable `HistoricalUsePermit` связывает exact EnvironmentRef, цель, actor, scope, срок, issuer и ограничения запуска. Она не превращает истёкшую TUF metadata в валидную и не применяется в обычной чистой установке. Первая версия route не реализует этот режим: `HISTORICAL_USE_UNSUPPORTED`. Это исключает неявный обход fresh install rules через `--force`.

Сетевой `fetch` — отдельное действие с явно разрешёнными origins, total bytes/time budgets и только скачиванием. Он записывает quarantine cache, не запускает bytes и не меняет active environment. `fetch` не считается `install`, `install` не считается `project init`.

## 4. Control store, receipts и состояние установки

Installation root получает собственный случайный `InstallRootId`, control-store schema revision, trust state и genesis marker. Existing directory без валидного control state не превращается в новый root автоматически. `install root create` требует exclusive create в пустом/отсутствующем destination и выдаёт отдельный root receipt. Наличие tombstone/old root marker, partial DB, неизвестного файла или вложенного project marker — `RECOVERY_REQUIRED` либо `PATH_OCCUPIED`.

Для первого adapter предлагается встроенный SQLite с `journal_mode=DELETE` и `synchronous=EXTRA(3)`, с exact build digest в closure. Каждая connection до mutations выставляет и перечитывает эти PRAGMA; unknown pragma может быть молча проигнорирована, поэтому сам факт успешного вызова не доказывает настройку. Неверное readback значение — `ENVIRONMENT_UNSUPPORTED`. Согласно [официальной документации SQLite](https://sqlite.org/pragma.html#pragma_synchronous), FULL в rollback mode может потерять последний commit при power loss; EXTRA добавляет directory sync после удаления journal. Эта настройка является частью design, а не заявлением, что нынешний опыт реализует SQLite или проверил накопитель. Проверки app schema, integrity, lock semantics, журналов и host flush обязательны. DB и его journal не перемещаются по отдельности. Нельзя удалять hot journal, чтобы «починить» установку.

Authoritative selector `ActiveEnvironment{generation,EnvironmentRef}` находится в той же DB transaction, что receipt, completion intent и control journal. Symlink/default launcher cache — производные; их устаревание не разрешает выбрать иной compiler. Launcher читает selector один раз, получает durable run pin и работает с exact immutable capsule path. Если производный cache повреждён, его можно пересоздать из DB; обратное восстановление DB из symlink запрещено.

### 4.1. InstallKey и повтор

Stable `InstallKey=(InstallRootId,key_generation,opaque_id)` определяет попытку. Intent digest включает EnvironmentRef, base generation, root identity, режим и semantic policy; транспортный request_id не входит. Общий lifecycle R16 применяется к admission window, key generation retirement, compact tombstones, capacity и uncertainty. Для bootstrap root операция создания имеет отдельный host-controlled exclusive destination reservation; это нижняя граница control store, не бесконечная рекурсия создания ключей.

После current read authorization retained receipt ищется **до** проверки нового current generation/trust expiry. Совпавший intent возвращает тот же исторический receipt, но не запускает среду и не утверждает, что ей разрешён новый запуск сегодня. Другой body при том же key — `IDEMPOTENCY_CONFLICT`. Отсутствие ключа на повреждённом индексе — `RECOVERY_REQUIRED`, не новая попытка.

Receipt не исчезает раньше закрытия key generation. Cleanup payloads допускается только после durable closed prefix и retention policy R16. Pending/unknown installation не вытесняется ради места. После retirement запрос даёт `KEY_ADMISSION_CLOSED`, не повторное выполнение и не выдуманный известный старый исход.

### 4.2. Стадии

`PLANNED → STAGING → VERIFIED → SEALED → ACTIVATED`; до активации возможны `ABORTED` и `FAILED`. `UNKNOWN_COMMIT` — знание caller об исходе, а не разрешение уничтожить устойчивые записи или повторить с новым ключом. `RECOVERY_REQUIRED` блокирует control mutations до восстановления.

`PLANNED` описывает действия без запуска payload. `VERIFIED` означает проверенные артефакты и static release completeness, но не активный selector. `SEALED` означает immutable capsule с durable directory entries и durable verification refs. Только `ACTIVATED` содержит committed generation+receipt. Два environment могут быть sealed одновременно; active selector один на installation root, с монотонным generation.

## 5. Алгоритм подготовки и активации

### 5.1. `install plan`

1. Strict-decode command; проверить current authorization, root identity, exact descriptor и policy. Считать base selector generation и trust snapshot.
2. Проверить release status `ISSUED`, exact profile/format matrix, complete tool roles, starter и независимые golden expectations. Для draft/неполной поставки `RELEASE_INCOMPLETE`; отсутствие договора starter — `TEMPLATE_UNVERIFIED`.
3. Вычислить замыкание, размеры, запреты путей и наличие всех bytes. Проверить provenance/trust и host preconditions. Не запускать compiler, package hooks, template код или arbitrarily supplied command.
4. Сформировать canonical plan, missing list, exact actions и required capabilities. Если payloads отсутствуют, вернуть `OFFLINE_MISSING` с полным report; план не становится executable.
5. Сохранение plan/intent — явная bounded control mutation. Если command работает `--preview`, вернуть immutable plan bytes без durable admission. От preview к apply требуется новый guard freshness.

### 5.2. `install apply`

```text
lookup retained receipt with current read permission
if found: compare semantic intent; return the same historical receipt
check write permission, live key generation, exact root and base generation
admit intent by unique key in control store
stage exact closure into private operation-owned directory
verify every file hash, size, path, mode and dependency; do not execute hooks
write canonical manifest; fsync files and all affected directories
atomically publish immutable capsule path without replacing existing content
fsync source and destination parent directories as required by adapter
record SEALED capsule and verification refs; orphan capsule is safe, not active
revalidate current trust, host requirements, permissions and capsule identity
BEGIN control transaction
  compare active.generation == plan.base_generation; compare exact plan/intent
  require capsule SEALED and not DELETING
  recheck current policy/trust revision and time upper bound < metadata expiry
  reject if the observed host/security premise can no longer be established
  increment generation with overflow guard
  write active selector + InstallationReceipt + intent terminal + journal atomically
COMMIT durably
return receipt; launch remains a separate explicit command
```

Входящая среда с тем же EnvironmentRef, но несовпадающими bytes означает integrity failure, не «обновление на месте». Содержимое опубликованной capsule не дописывается. Если проверка требует запуска verifier или compiler из release, этот запуск разрешён только после проверки происхождения, в отдельном capability-empty verification sandbox и с bound resources. В первой `apply` выполняются только предусмотренные metadata/byte checks; end-to-end starter run — отдельный acceptance шаг, см. route. Hook scripts отсутствуют в install format.

SQLite transaction обеспечивает одну control-store boundary; она не включает file writes магически. Порядок `durable files → DB references` является обязательным: crash может оставить unreferenced files, но не должен оставить committed receipt, указывающий на недолговечные bytes. Носитель/FS, нарушающий contract sync, исключает такую гарантию.

### 5.3. Конкуренция и ABA

Install plans A и B от generation7 конкурируют. Если A получает generation8, B возвращает `INSTALL_CONFLICT`, даже если B EnvironmentRef совпадает с текущим или после дальнейшего переключения A→B→A content снова тот же. Generation не откатывается и не переиспользуется. CAS проверяет root identity, selector generation и semantic plan; один digest среды недостаточен.

При повторе committed A тот же receipt возвращается даже после generation9, если retention/read policy это допускает. Этот replay не меняет selector обратно на A. Для сознательного выбора A снова создаётся новый plan от current generation и новая операция; project pin остаётся прежним.

## 6. Crash recovery и удаление

| Момент сбоя | Устойчивое состояние | Допустимое восстановление |
| --- | --- | --- |
| До durable admission | Нет admitted operation | Повтор того же request после проверки authority |
| После admission, до complete staging | Pending intent, private partial directory | Проверить ownership; продолжить exact plan либо abort; active неизменен |
| После публикации capsule, до SEALED DB record | Orphan immutable bytes | Сверить manifest; привязать к exact intent либо удалить как недостижимые |
| После SEALED, до commit | Старый selector, готовая capsule | Повторная актуальная проверка/CAS; без автоматической активации другого плана |
| Внутри DB commit / потеря ответа | Исход может быть неизвестен caller | Открыть и восстановить store; `lookup(InstallKey)`; не генерировать новый key |
| После commit, до launcher cache update | Новый selector+receipt | Восстановить производный cache; вернуть тот же receipt |
| Потеря/повреждение control DB | Утрата authority selector | `RECOVERY_REQUIRED`; не создавать пустую DB и не выбирать последний каталог по mtime |

EIO/ENOSPC/permission loss на fsync — не успешная установка. Если commit точно не произошёл, `IO_FAILED` с retained old selector. Если commit outcome нельзя доказать, `UNKNOWN_COMMIT` и lookup/recovery; сообщение «не установлено» запрещено. В startup первым действием закрывается write gate; только успешная recovery проверка открывает его. Недостаток места для записи failure marker не делает старый READY актуальным.

`install abort` отменяет только незавершённую установочную операцию. Он не отменяет состоявшуюся активацию и не является rollback программы. `install deactivate` создаёт новую generation с empty selector, не уничтожая ProjectIdentity, project pins, receipts или unknown obligations. `install select` старой capsule — новая checked activation, без отката project/source/authority.

GC вычисляет roots из active environment, project pins, retained verification/acceptance requirements, running launch pins и pending installs. Удалению подлежит полный недостижимый closure, а не только старый compiler executable. В одной DB transaction GC проверяет отсутствие всех roots и переводит capsule в `DELETING`; создание новых pins запрещено. Затем удаляются принадлежащие store bytes, синхронизируются directories, фиксируется completed deletion. Сбой допускает продолжение DELETING, но не повторное включение half-deleted capsule. Launch pins не снимаются просто по TTL: нужен подтверждённый завершённый процесс/job либо session-fencing proof; unknown launch сохраняет pin. Обычное удаление tools не удаляет проекты. `project destroy` вне этого route и требует отдельного контракта.

## 7. Новый проект: уникальная genesis без обнуления истории

### 7.1. Когда `project init` допустим

Новая identity создаётся только командой NEW. Caller задаёт destination, имя, template ref, environment и policy; **не задаёт произвольные старые ProjectId/AuthorityId**. Новый ID выделяется trusted generator, с exclusive insert в identity registry и запретом reuse. ProjectId содержит identity domain (`IdentityRootId`) и новый local nonce; новая domain не позволяет назвать её identity прежним ProjectId. Fresh domain identity — явная предпосылка trusted host provisioning, не вывод из отсутствия каталога. Случайность уменьшает риск collision, но collision при наличии authoritative registry всё равно проверяется. Имя/путь не являются доказательством identity.

Destination должен быть отсутствующим либо явно пустым согласно profile. Проверяются parent ownership, absence of project/authority/tombstone markers, отсутствие metadata известного проекта и exclusive create reservation. Старый проект с missing journal даёт `PROJECT_RECOVERY_REQUIRED`. Непустой каталог исходников может быть импортирован отдельной явной операцией; `init --force` не выполняет импорт или очистку. Потеря собственного root registry не даёт возможности безопасно отрицать существование прежней identity: сначала recovery.

### 7.1.1. Independent identity registry и BootstrapKey

`IdentityRoot` расположен в явно указанном отдельном durable каталоге, не внутри удаляемого installation root или будущего project destination. Trusted host configuration хранит его root identity/location и recovery anchor; CLI не ищет его эвристически в случайных parent directories. Для reference single-host adapter используется собственная SQLite DB с DELETE/EXTRA и теми же readback/durability правилами. Registry root создаётся однажды exclusive host-controlled операцией; потеря/несоответствие trusted root metadata блокирует новое использование прежнего identity domain. Новый domain может создать только новые identities, без права продолжения старых.

`BootstrapKey=(IdentityRootId,key_generation,opaque_id)` и semantic digest включают exact destination reservation, template/environment/policy, mode NEW. Stable `BootstrapReservation={BootstrapKey,intent_digest,ProjectId,AuthorityId,GenesisId,destination_ref,state,genesis_commitment?,receipt?}`. Состояния RESERVED→PUBLISHED→COMPLETED; ABANDONED означает permanently burned identities. Registry сохраняет used-id index, destination reservations, live intents и key closed prefix; R16 admission/retention/unknown rules применяются здесь отдельно от install keys. Новая команда не принимает caller-selected ProjectId.

Сначала current read authorization и lookup exact BootstrapKey; equal digest возвращает сохранённое состояние/receipt, conflict отказывает. При незавершённой reservation `resume genesis` продолжает её, а не выделяет другой ID. DestinationRef состоит из доверенного parent handle identity и relative leaf; строка пути не разрешает перейти в заменённый parent. При первом admission unique constraints на bootstrap key, identity IDs и active destination reservation обеспечивают единственное выделение. RESERVED intent уже содержит все IDs **до** записи project directory.

После опубликования project registry сохраняет exact GenesisRecord digest и locator. Existing project сам содержит IdentityRootId/BootstrapKey, чтобы восстановление могло найти reservation. Если crash произошёл до project directory, request key и trusted registry configuration по-прежнему позволяют lookup. Если registry утрачена, наличие папки не позволяет заново сделать COMPLETED receipt: требуется проверяемое восстановление registry authority; новые tools не исправляют её молча. Потерянный caller key не повод повторить init: destination-reservation lookup разрешён только соответствующему владельцу и возвращает уже выделенную intent.

### 7.2. Транзакционная genesis

Для первого single-host adapter authority metadata, GenesisRecord, initial working head и nullable accepted head, initial WorkState, journal, namespace registry и bootstrap receipt хранятся в одной project control DB. Source files и package artifacts подготавливаются immutable перед ссылкой на них. Начальный working head указывает на starter, а accepted head равен null; genesis commitment — факт создания, не нормативная приёмка исходника. Команда выполняет:

1. Проверку current authorization, exact starter/env/policy, destination reservation и форматов; исходники не исполняются.
2. Регистрацию `BootstrapIntent` с Id/key/digest до создания project authority. Повтор с тем же key не создаёт второй ProjectId.
3. Выделение fresh ProjectId/AuthorityId/GenesisId; запись reservation в install-independent identity registry. Нарушение no-reuse или неизвестное состояние reservation блокирует genesis.
4. Копирование exact starter files, lock и policy в private staging; проверку hashes и прочности записи. Структурные файлы ProjectManifest создаются по схеме; template не исполняет генератор и не подставляет произвольный shell.
5. Формирование initial project DB со всем genesis bundle; initial head указывает на template source snapshot. `WorkState` начинает с явных обязательств verify/build/run; отсутствие приёмки не заменяется пустым списком.
6. Durable publication project directory без замены destination; registry фиксирует published location и genesis commitment. При нескольких хранилищах используется порядок reservation→durable project→registry completion. Незавершённая reservation всегда ведёт к lookup/recovery, не к повторному выделению identity.
7. `ProjectReceipt` возвращает identity, manifest/source/lock refs и initial authority epoch. Он не сообщает `SOURCE_ACCEPTED` либо `RUN_PASS`, пока соответствующие отдельные операции не выполнены.

Если crash после durable project, но до registry completion, recovery проверяет exact GenesisRecord и завершает ту же reservation. Если crash до publication, повтор использует тот же reserved identity или окончательно закрывает её без reuse. Конфликт destination сохраняет исходное содержимое; частичная чужая папка не удаляется. Installed environment может отсутствовать после cleanup ошибки, но ProjectIdentity и история остаются восстановимыми; это `ENVIRONMENT_MISSING`, не новый проект.

### 7.3. Source portability и authority

ProjectManifest имеет portable/source часть и authority/storage часть. Архив исходников без authority state допускает **явный fork/import как новую identity**, с lineage refs и outstanding review obligations; это не восстановление старого проекта и не продолжение его внешних операций. Это отдельная будущая операция, не автоматический fallback `restore`. В первом install route fork/import не выполняются.

## 8. Существующий проект: attach, repin и восстановление

| Операция | Разрешённое изменение | Обязательный отказ |
| --- | --- | --- |
| `tools attach` | Локальная association exact installed capsule ↔ existing pinned EnvironmentRef; host-only observation | Missing/incompatible exact lock; изменение source/history/identity запрещено |
| `project environment plan` | Proposal новой среды и compatibility obligations | Неопределённая format matrix |
| `project environment apply` | Явная CAS-правка project environment pin с сохранением истории | Stale source/project/authority guard; незакрытая обязательная совместимость |
| `project recover` | Восстановление той же authority/history по актуальным evidence | Stale/unverifiable backup, missing frontier, невозможность доказать полноту |

`tools attach` не выводит новый ProjectId из пути, не rewrites lock на доступную версию и не выполняет миграции. Восстановление tools после их удаления достаточно для работы с прежним project lock, если все точные bytes и текущие полномочия доступны. Отсутствующие artifacts в offline режиме дают exact missing list.

Recovery переносит правила R16 без ослабления. Backup сам по себе не доказывает currentness. Нужен current authority anchor вне rollback domain восстановленных bytes и полная цепочка до него; другая signature с правильным key не доказывает свежесть. Complete restore выделяет новый service epoch, сохраняет ProjectId, head, WorkState, key bindings, closed prefixes, pending jobs и UNKNOWN effects. Старые worker/LaunchBinding не могут совершать mutation в новом epoch.

Incomplete restore даёт `QUARANTINED` с разрешённым read-only inspection; неизвестные долги остаются. Emergency burn key namespace не является подтверждением отсутствия эффекта. Новый инструмент, новый namespace, переименование каталога или новый InstallRootId не снимают quarantine старого проекта. Recovery controller сначала закрывает writes, затем загружает backup. Невозможность записать quarantine marker из-за resource exhaustion не открывает старую authority.

Для локального проекта без внешних effects можно восстановить source snapshot как **новый** проект только явно, с новым lineage и без утверждения continuing authority. Для прежней identity применяются те же freshness требования. Первая версия route не делает такой fork автоматически и не объявляет, что local-only filesystem rollback resistance решена.

## 9. LaunchBinding и проверка среды

Перед запуском launcher получает immutable `LaunchBinding`: exact ProjectRef/head/package lock/environment, authority epoch, policy and work guards. Install store и project store независимы; общей транзакции между ними не предполагается. Используется безопасный порядок с допустимыми лишними pins:

1. В install DB создать `ExecutionPin{PinId,EnvironmentRef,LaunchIntentId,owner,PREPARED}` при SEALED, допустимой текущей policy и отсутствии DELETING. Root active generation не подставляется вместо project lock.
2. В project DB текущий read/run authorization и exact source/lock/environment/epoch/work guard проверяются одним CAS; записывается `LaunchIntent{LaunchIntentId,PinRef,Binding,ADMITTED}`. При конфликте admission отсутствует; pin можно снять только после доказанного отсутствия или terminal rejection этой exact intent.
3. Dispatcher получает текущий project fence и проверяет, что durable pin существует и не retired. Запускается immutable source snapshot из binding. Последующая обычная правка working head не меняет уже admitted snapshot; операции, способные менять project state, дополнительно проверяют актуальные commit guards. Revocation/новый service epoch блокируют новые dispatch и mutations прежнего worker; не заявляют, что уже начавшийся OS process физически отменён.
4. Завершение/доказанный отказ записывается в project DB. Release pin — отдельная идемпотентная control operation только после exact terminal evidence; unknown process/launch outcome удерживает pin. Crash после шага1 оставляет избыточный pin, а не право GC. Missing project store не доказывает, что launch не был admitted. Recovery сначала проверяет journal/LaunchIntent, затем завершает release либо сохраняет hold.

Environment должен быть SEALED и пройти актуальные host/trust проверки перед dispatch; PinRef предотвращает удаление bytes, но не выдаёт полномочий. Project lock сравнивается с environment content; install default не участвует в выборе после binding. Этот протокол не обещает atomic rollback процесса ОС и двух DB; его инвариант — ни один допустимый dispatch не ссылается на удаляемую capsule.

Если project head или authority epoch изменились **до admission запуска**, `LAUNCH_STALE`; текущие значения не подставляются автоматически. После admission сохраняется exact snapshot, а epoch/current permission дополнительно проверяются перед dispatch и mutation, как указано выше. Pure historical inspection/run возможны только отдельным явно обозначенным snapshot mode, без mutation старой authority, и не входят в первый route. Изменение default environment при неизменном project lock не делает binding устаревшим само по себе. Source/content revision, project environment-pin revision и binding generation разделены: регистрация binding не изменяет собственный исходный source guard. ProjectRef в binding не включает hash этого же binding; committed control journal ссылается на тела уже вычисленных refs, без циклического хеширования.

`doctor` по умолчанию проверяет metadata, hashes, format compatibility, root ownership, guards и references. Он не запускает source, не выполняет package lifecycle hooks, не чинит authority и не пытается повторить external effects. `doctor --probe` — отдельный явно названный bounded host check; пишет только в operation-owned scratch и оставляет результат наблюдения. Если требуется executable ABI probe, допускается только доверенный digest-pinned probe из bootstrap closure с объявленными capabilities. Самостоятельно восстановить проект doctor не может. Вызов чужого `--version` является исполнением binary, а не чтением файла; origin verification и явная probe policy требуются до такого запуска.

Различаются `environment_ready`, `project_binding_valid`, `source_checked`, `build_verified`, `run_result` и `normative_acceptance`. Одна зелёная галочка «всё готово» без этих областей недопустима. Отчёты включают profile, input refs, expected/actual, gaps, time/trust scope, actual test method; simulation report обозначается явно.

## 10. Минимальный проект без параллельной грамматики

Установщик не знает собственный упрощённый язык. Он копирует exact `starter-minimal` из конкретного release. Его `StarterDescriptor` задаёт полный file roster с hashes, source format/revision и semantic profile, entry symbol, package lock, capability set, expected diagnostics и golden outcome. Для первого starter задаётся смысл: замкнутая pure entry без аргументов возвращает `Int64(42)`, не делает host calls, не требует сетевых/файловых/временных capabilities; external stdout приложения пуст, machine-readable результат отдаёт CLI. Это простая программа для маршрута установки, не сужение V1 до литерала.

Golden expectation фиксируется независимо от тестируемого compiler/runtime до первого запуска. Release producer обязан включить **реальные точные source bytes** совместимые с T03 и mapping в T13, а не автоматически сгенерировать golden из результата своего compiler. Starter closure и expected outcome входят в signed descriptor. Недоступная реальная grammar/source template сейчас честно остаётся зависимостью интеграции: этот R17 не изобретает строку синтаксиса и не выдаёт её за актуальную bagaev grammar.

Gate выпуска: отсутствующие exact template bytes, source-format compatibility mapping или независимый golden дают `TEMPLATE_UNVERIFIED`/`RELEASE_INCOMPLETE` **до включения такого release как пригодного для clean-install route**. Можно хранить draft artifacts в quarantine cache, но установка не получает usable-release receipt. Таким образом алгоритм route задан полностью при объявленных входах; фактическая поставка и end-to-end evidence ещё должны быть созданы.

Пошаговый [маршрут](clean-install-route.md) задаёт команды, expected observations и отрицательные случаи. Наличие finite bootstrap model не означает, что эта программа уже разбиралась, компилировалась, линковалась или исполнялась.

## 11. Публичные операции и диагностика

Machine command envelope: `schema`, `request_id`, `operation`, `arguments`, `guard`, `idempotency_key?`. Credentials и trusted host evidence передаются вне untrusted arguments через проверенный adapter. Установщик не принимает пользовательское `signature_valid=true` либо `journal_complete=true` как доказательство. В finite модели такие поля — явно маркированные premises симуляции, не публичный API.

| Команда | Содержательные inputs | Результат |
| --- | --- | --- |
| `install plan` | exact release/lock, root, offline mode, current guard | PlanRef, closure/missing report, required actions |
| `install apply` | PlanRef, InstallKey, root/generation guard | исторический или новый InstallationReceipt |
| `install status` | root/InstallKey | retained state/receipt с областью known/unknown |
| `install recover` | root, current recovery context | восстановленный control-store status либо blocked |
| `install select/deactivate` | exact current generation, target ref или empty | новая generation и receipt |
| `install gc` | root, current GC guard, bounded budget | deleted/pinned/deleting refs с complete flag |
| `project init` | destination, explicit IdentityRoot config, template, exact environment, initial policy, fresh intent | ProjectReceipt и обязательства verification |
| `tools attach` | ProjectRef, current manifest/lock guard, installed EnvironmentRef | association report; unchanged project authority |
| `project recover` | exact backup, current authority evidence, recovery operation | READY нового epoch или QUARANTINED |
| `doctor` | environment/project refs, read scope | metadata diagnostics; source not executed |
| `build` / `run` | exact source/lock/env, semantic limits, LaunchBinding | BuildReceipt / RunReceipt с точной областью |

`project environment apply`, сетевой fetch, создание install root и export reports имеют отдельные полномочия и receipts. Обновление source format/storage schema не выполняется installer hook; требуется migration plan по T18-C01/C02 и отдельная acceptance policy.

Ответ: `schema`, `request_id`, `operation_ref?`, `status=ok|blocked|failed|unknown`, `code`, `result_ref?`, `retry={same_key|new_plan|recover|none}`, `evidence_scope`, `details`, `complete`, `next?`. Нет credentials, host secrets, полного environment dump. Диагностика различает program failure, prelaunch rejection и unknown installation outcome. CLI печатает ровно один JSON document в stdout при `--json`; logs идут в stderr и не меняют результат. Некорректный JSON/arguments: exit2; checked refusal: exit3; implementation/I/O failure: exit4; uncertain commit: exit5; success: exit0. Signal termination не переименовывается в application error или success.

При нескольких отказах порядок: strict shape/resource bounds → current read authorization → retained intent lookup/conflict → mutation authorization → root/store integrity and currentness → identity/generation/epoch guards → platform/trust/closure → capacity → transaction. Read authorization проверяется до раскрытия наличия секретного key. Повтор historical receipt не заявляет current readiness. Полный status в долгом report связан с snapshot; missing pages дают unknown completeness, не отсутствие проблем.

### 11.1. Основные codes

| Code | Значение / следующий шаг |
| --- | --- |
| INVALID_INPUT / LIMIT_REACHED | Отказ формы или объявленного resource bound; без частичной committed mutation |
| UNAUTHORIZED | Нет текущего права; без утечки existence/receipt |
| RELEASE_INCOMPLETE / TEMPLATE_UNVERIFIED | Нельзя объявить usable install; producer дополняет release |
| ENVIRONMENT_UNSUPPORTED / ABI_MISMATCH | Платформа/closure не соответствует profile |
| TRUST_INVALID / TRUST_EXPIRED / TRUST_TIME_UNKNOWN | Не подтверждено допустимое происхождение/срок; без force fallback |
| OFFLINE_MISSING / ARTIFACT_CORRUPT | Exact missing/mismatching refs; не подмена версией |
| PATH_OCCUPIED / PATH_UNSAFE | Destination не подходит; existing bytes не перезаписываются |
| INSTALL_CONFLICT / PROJECT_CONFLICT / LAUNCH_STALE | Guard устарел; нужен новый plan/binding после просмотра |
| IDEMPOTENCY_CONFLICT / KEY_ADMISSION_CLOSED | Нельзя повторно использовать key с новым body или после закрытия |
| PROJECT_EXISTS / PROJECT_RECOVERY_REQUIRED | Новый genesis запрещён; attach/recovery по существующей identity |
| RECOVERY_REQUIRED / QUARANTINED | Недостаточно authority/evidence для mutation |
| ENVIRONMENT_MISSING / ENVIRONMENT_PINNED | Нужный closure отсутствует / удаление нарушит roots |
| IO_FAILED / UNKNOWN_COMMIT | Доказанный отказ I/O / недостаток знания об исходе commit |

## 12. Условия проверки и границы готовности

Реальный clean-install PASS требует чистого host image, exact image/OS/kernel/storage configuration, verified bootstrap tool, release artifact bytes, trust snapshot, trace команд, independent golden, hashes до/после и post-restart observations. Интернет отключён для offline испытания; отсутствующие artifacts действительно отсутствуют. Полнота не выводится из одного happy path.

[Матрица](clean-install-route.md#5-будущая-интеграционная-матрица) содержит future CI-01…CI-24. Для stage3 исходного T18-C04 требуется независимая проверка всего объявленного route/profile, включая реальный source compiler/runtime и storage fault cases, а не только pure transition model. Stage4 дополнительно требует принятия и зависимостей. Нынешний контракт может оцениваться как stage2 при успешном review полноты; его опубликование не увеличивает оценку соседних критериев автоматически.

Открытые межмодульные входы: актуальные T01 platform ledger, T03 source/codec, T12 WorkState/authority operations, T13 release artifacts/locks, T14 CLI/error vocabulary, R15 change/adoption gates. Отсутствующие R15 bytes не восстанавливаются по памяти. До интеграции локальные решения R17 остаются PROPOSED. У install capsule identity, project genesis и key lifecycle есть точные алгоритмы; совпадение имён с будущим upstream contract проверяется отдельным review, а не презюмируется.
