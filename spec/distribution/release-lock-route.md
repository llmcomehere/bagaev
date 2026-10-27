# R20 — маршрут независимой проверки настоящего toolchain и выпуска

Статус: **все перечисленные production integration classes NOT_RUN**. Это implementable verification plan для всего T13-C02 и связанного T18-C05, не отчёт о выполнении. Машинный перечень — [integration-cases.json](../../registry/data/distribution/release-lock-integration-cases.json). Finite model и metadata shape probes имеют отдельные отчёты и не заполняют эту таблицу.

## 1. Готовность входов

Перед первым запуском независимый verifier получает exact source bundle/parser/source-to-IR/type/effect contracts, compiler/reference runtime, package descriptor/lock/materializer codecs, MeaningLock/Environment/source acceptance implementation, OS build sandbox, tested catalog/storage adapters, concrete publication destination и deployment authority. Каждый input имеет bytes/codec/profile/hash, provenance, trust scope и current permissions. Недостающий предмет — INPUT_NOT_READY. Нельзя заменить его toy payload, выдуманной программой или собственным `compatible=true`.

Production permissions не вытекают из этого плана. Реальные test destinations должны быть выделены и разрешены владельцем; документы R20 не осуществляли публикацию/развёртывание. Тестовые adverse endpoints должны принадлежать испытателю и не затрагивать чужую инфраструктуру.

Проверяющий до inspection реализации фиксирует конкретные fixtures, invariants, independent expected outcomes и source pins. Resolver oracle строится отдельно: exhaustive enumeration малых finite domains, затем независимый closure checker и metamorphic transformations больших graphs. Проверяющий сравнивает полные state/receipt/effect traces и exact artifacts, не только `ok=true`. OS/remote observations снимаются независимо от tested process.

## 2. Единый формат CaseResult

`CaseResult = {case_id, subject_refs, prerequisites, request_refs, oracle_ref, runner_ref, environment_ref, exact_observation_refs, actual_status, expected_relation, comparator_ref, outcome, exclusions}`. Outcome∈PASS/FAIL/UNKNOWN/INPUT_NOT_READY/NOT_RUN. UNKNOWN/NOT_RUN не PASS. Для concurrent/crash cases дополнительно scheduler/fault-seed, allowed partial order и durable storage/remote journal refs. Повтор не затирает первый failure: сохраняются invocation IDs и linkage к исправлению.

Сравнение воспроизводимости использует raw artifact bytes либо явно declared normalized artifact и separate transformation ref. Native/compiler/platform exclusions записываются в каждом отчёте. Достаточность всего T13-C02 проверяется против исходного критерия и production profile; одна удачная platform не покрывает все заявленные domains.

## 3. Классы испытаний

| ID | Вход / инъекция | Независимое ожидаемое наблюдение |
| --- | --- | --- |
| IC20-01 | Зафиксировать lock, затем сменить registry aliases/добавить более новые версии; locked offline build | Тот же dependency graph и bytes; нет resolver/network call; отсутствующий blob даёт INPUT_NOT_READY |
| IC20-02 | Diamond graph с противоречащей newest version; перестановки catalog/roots | Детерминированный backtrack к удовлетворяющему решению; одинаковый LockRef и объяснение conflicts |
| IC20-03 | Feature implication cycle, объединение features от двух родителей, exclusion/optional dependency | Наименьшая fixed point; дополнительный edge учтён; конфликт не маскируется отключением feature |
| IC20-04 | Два разных descriptor/source для одного label, mirror подменяет bytes | CATALOG_EQUIVOCATION/HASH_MISMATCH; выбор по имени/hash-порядку не допускается |
| IC20-05 | Exhaustive impossible finite catalog, недостающая metadata, budget ровно на границе | UNSAT_SNAPSHOT только в первом случае; INPUT_NOT_READY/UNKNOWN_LIMIT отдельно; старый lock неизменен |
| IC20-06 | Update одного key требует смены pinned соседнего или нового неразрешённого key | PIN_CONFLICT/OUT_OF_SCOPE_UPDATE; без silent widening; разрешённое удаление dead node отражено в diff |
| IC20-07 | Новая версия образует cycle, старая DAG; затем все версии cyclic | Выбор старого DAG; в полном поиске all-cyclic UNSAT только в DAG scope; locked cyclic graph отвергается |
| IC20-08 | Cross-build: совпадающие имена host/target с разными ABI/effect/nominal refs | Нет подстановки host в target; namespace identity сохраняется; mismatch/unsupported явно отказ |
| IC20-09 | Удалить transitive edge/node, изменить digest либо добавить unreachable node | Independent descriptor-derived closure отвергает все повреждения; cache/latest не восполняет пробел |
| IC20-10 | Archive paths a и a/b, case collision, links, reserved names, traversal, nonASCII profile | До записи вне staging — TREE_INVALID/UNSUPPORTED; повторный tree hash и no unexpected reads |
| IC20-11 | Git moving ref/submodule/LFS mismatch, workspace change во время snapshot, hook | Captured exact tree/objects либо отказ; не запускаются hooks; live path не участвует в build |
| IC20-12 | Generator/FFI/sysroot/compiler пытается читать undeclared file/PATH/network | Реально enforced denial/effect trace; closed input status не выдаётся; exact allowed inputs доступны |
| IC20-13 | Две независимые builds; смена locale/time/random/scheduler/backend | REPRODUCED только в declared comparison domain; nondeterminism выявлен, normalization отдельным artifact |
| IC20-14 | Working source изменён/вернулся к тем же bytes, accepted остаётся историческим | Exact accepted generation/MeaningLock/Environment связаны; old candidate не принимает новый acceptance evidence |
| IC20-15 | Candidate с чужим lock/result/check, stale policy, отсутствующим platform child/index | Seal отвергнут; valid single/multi-platform candidate имеет полное exact inventory без hash cycles |
| IC20-16 | Accept/resolve/materialize/build/check/seal при доступном fake remote logger | Ни publish/deploy/hook, ни registry tag change; OS/network traces подтверждают отсутствие скрытого действия |
| IC20-17 | Делегированная exact release policy; revoke/change scope/candidate/target | Разрешённое действие допускается без нового human prompt; неподходящий scope не расширяется |
| IC20-18 | Crash/lost reply после remote commit; revoke write/action rights, оставить read | Historical receipt/lookup доступен; повтор dispatch отсутствует; persisted reconciliation без текущего grant запрещён |
| IC20-19 | Тот же R16 KeyRef с другим payload; namespace rotation/retirement/UNKNOWN debt | KEY_CONFLICT; key/generation не переиспользованы; pending intent не удалён по TTL и не обходится новым key |
| IC20-20 | Два writers, stale request, A→B→A alias, content-only ETag | Monotonic generation/fence ловит stale/ABA; content CAS не выдаётся за history freshness |
| IC20-21 | OCI без conditional write; HTTP2xx для уже эквивалентного изменения другим writer | UNSUPPORTED/declared narrower profile; CONTENT_OBSERVED не равно атрибуции собственного execution |
| IC20-22 | Authority revoke между preflight и sink commit; старый worker после recovery | Actual commit boundary отказывает старому grant/fence; local mutex/precheck не считается доказательством |
| IC20-23 | Multi-target/rolling deploy частично успешен; commit успешен, health FAIL | Полный vector member outcomes; published/desired/committed/observed/healthy различимы; PARTIAL не SUCCESS |
| IC20-24 | Cancel до/после MAY_HAVE_RUN; proven nonapplication; rollback после data migration | Старый terminal intent не re-executed; компенсация отдельная, current-precondition/migration checks обязательны |
| IC20-25 | Restore/migrate между remote commit и local activation/receipt; отсутствующий journal suffix | UNKNOWN/pins/current authority сохраняются; same-attempt lookup; отсутствующий cut не становится fresh intent |
| IC20-26 | Stored-state/receipt/transport/remote-retention capacities и uint64 exhaustion | Отказ до эффекта либо reserved UNKNOWN record после возможного эффекта; history lookup остаётся возможным |
| IC20-27 | Foreign SLSA/OCI неизвестные fields, incomplete dependencies, signer/builder mismatch | Оригинальные bytes сохранены; foreign parsing не меняет internal unknown semantics; provenance не даёт release grant |
| IC20-28 | Изменить package/source/config; запросить backward explanation от реального deployment | Exact reverse path до clauses/source; affected evidence stale; observations не редактируют acceptance автоматически |
| IC20-29 | Manifest с final MeaningLock→lock cycle; mixed R19 semantic digest и R20 byte hash | INVALID_OBJECT_GRAPH/type/hash mismatch; корректный DAG и native/outer identity проверяются раздельно |

## 4. Порядок реализации

1. **Metadata/closure layer:** serializers, typed refs, independent locked verifier, trees и exact local store. Реализовать IC20-01/04/09/10/29 без реального publish.
2. **Resolver:** immutable snapshot, deterministic DFS/feature propagation, scope updates, bounds и conflict trace; IC20-02/03/05/06/07/08. Сопоставить с independent enumeration.
3. **Build adapter:** capture/mount enforcement, source acceptance binding, exact toolchain/FFI/generator closure, output provenance и independent rebuild; IC20-11..16.
4. **Release adapter:** concrete destination contract, current delegated admission, durable outbox/arm, read-only lookup, authorized reconciliation, mutable-target CAS/actual fence; IC20-17..22/26/27.
5. **Runtime activation and graph:** deployment member outcomes, health observations, compensation, R18/R19 recovery/migration, reverse evidence relation; IC20-23..25/28.

Эти implementation steps конкретизируют уже существующие T13/T18 и их зависимости, не добавляют новые критерии в denominator. Переход stage2→3 для T13-C02 возможен только после evidence по всем обязательным применимым классам и независимого scope review; stage4 требует принятия и закрытых зависимостей. Для T18-C05 весь original acceptance/action boundary должен быть подтверждён production endpoints, не только toy dispatch counter.

## 5. Граница текущего опыта

RELEASE-LOCK-FINITE-0.1 имеет trusted in-memory catalog/context/CAS destination и serial transitions. Его resolver намеренно останавливается на первой constraint assignment с неподдержанным cycle; production solver продолжает backtracking к другому DAG. Модель не реализует feature/domain/ABI/native/source parsing, полный R16 composite KeyRef, metadata profiles, actual durability или output transforms. Lookup модели может сохранять наблюдение при read-only authority; production §5.2 требует separate record grant. Эти различия задокументированы и не позволяют назвать модель implementation полного контракта.

Граничные seed states проверяют структурно допустимые случаи, но не доказывают достижимость/авторизованную историю. Semantic mutants проверяют чувствительность именно finite suite. Shape probes проверяют record construction. Package manifest/ZIP tests проверяют целостность поставленного исследования. Ни один из этих отдельных результатов не заполняет NOT_RUN production class автоматически.
