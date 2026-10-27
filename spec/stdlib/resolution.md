# STD-RESOLVE-0.1 — замкнутый каталог и двунаправленные зависимости

**R24 · проект алгоритма, production compiler NOT_RUN.** Стабильный API ID отличается от revision exact symbol contract. Display name служит только lookup в зафиксированном ExportCatalog. Runtime не ищет «сегодняшнюю» библиотеку по строке.

## 1. Артефакты и порядок построения

1. TypeDeclarations, ErrorContracts, PureWorkContract и точные service/codec dependency contracts создаются независимо от каталога.
2. SymbolContract содержит stable API ID, public name, monomorphic/generic signature, bounds, closed effects с точными resource binders, behavior/error/work refs, required dependencies и source origin. Он не содержит hash будущего каталога или себя.
3. ExportCatalog содержит отсортированные по ASCII segment sequence records public functions/types и exact SymbolContractRefs, alias table, diagnostic prefix table, known profile capabilities. Unknown semantic fields и duplicate ID/name отвергаются. Сам перечень не содержит собственный hash; external ExactRef вычисляется после canonical encoding.
4. LibraryPackageManifest связывает catalog, provider image/IR modules и их declared dependencies; R20 DependencyLock фиксирует manifest/interface/body closure. MeaningLock отдельно фиксирует semantics/work/errors/codecs; provider implementation не выбирается одним alias.
5. SourceVersionBinding связывает authored source, lock/environment. Resolve выдаёт ResolvedStdUse; type/effect/lower/link проверяют последующие свойства. StageResult и evidence создаются после своих subjects по R21, без hash cycles.

JSON data/stdlib-catalog.json в этом пакете — дизайн-реестр. Его локальные ссылки, signatures и dependency IDs не выдают отсутствующие production ExactRefs. Перед реальной compilation требуются проверенные encoded declarations/registry/manifest; отсутствие этих bytes даёт INPUT_NOT_READY. Catalog shape validation не является complete type checker или verification поставщика.

## 2. Правила lookup и диагностики

Вход: exact catalog+manifest+MeaningLock+DependencyLock, requested qualified symbol, expected kind (function/type), requested profile, source/node ref. Qualified std name состоит из непустых ASCII identifier segments `[A-Za-z_][A-Za-z0-9_]*`, разделённых точкой, первый segment `std`; aliases явно перечисляются, в R24 aliases=[] и implicit_prelude_functions=[]. Это правило имён std export, не новая полная lexer grammar V1. Unicode source identifiers могут ссылаться на std через нормальное явное import binding, но имя remote export остаётся exact ASCII.

Порядок:

1. Проверить request envelope/name, exact hashes/kinds/versions входов и целостность catalog. Источник syntax error не обвиняется за corrupted supplied artifact; R21 phase+blame сохраняется.
2. Exact name lookup среди functions и types. Если отсутствует, выбрать **самый длинный segment-prefix** из diagnostic table. Если нет — UNKNOWN_STDLIB_SYMBOL. `std.gpuX.x` не совпадает с `std.gpu`; `std.result.unwrap_extra` не совпадает с `std.result.unwrap`. Запрещены fuzzy success, fetch-from-network и fallback к host/global namespace.
3. Если exact name существует, но wrong kind — STDLIB_KIND_MISMATCH. Нельзя вызвать type constructor как несуществующую std function или перепутать API function с type declaration.
4. Проверить explicit requested profile и supported target semantics. Известный отдельный/запрещённый feature даёт UNSUPPORTED_PROFILE/UNSUPPORTED_FEATURE; реализация, не имеющая required V1 symbol, не получает права объявить его optional: TARGET_STDLIB_UNSUPPORTED и V1 conformance failure.
5. Разрешить transitive required exact contracts по DependencyLock/MeaningLock: typed version/kind/content equality, uniqueness, поддержка checker/runtime и declared closure. Missing contract → INPUT_NOT_READY со sorted missing IDs; unavailable bytes → INPUT_UNAVAILABLE, corrupted bytes → UNTRUSTED/INPUT_HASH_MISMATCH; declared incompatibility → STDLIB_CONTRACT_MISMATCH. Имена контрактов и bool `available` не являются основанием.
6. Создать ResolvedStdUse с exact SymbolContractRef, binding to source occurrence и полным required semantic read-set. Этот результат — **разрешённая ссылка**, не type check/authority/admission/выполнение функции.

Type затем проверяет generic arity, подстановку/whole-type bounds и exact function signature; effects проверяет static closed bounds, lower сохраняет strict evaluation/work revision, link связывает exact provider implementation, loader проверяет target/runtime closure и launch authority. Каждый service dispatch снова проверяет current rights. Невзятые branches и неиспользуемые declarations проходят статическую проверку; запрещённый std call там не исчезает до проверки.

Ненайденный symbol и недоступный bytes — разные вопросы. Diagnostic-prefix для pending Float/BigInt/recursive_data обозначает INPUT_NOT_READY и сохраняет V1 decision, не притворяется отвергнутой программой. Известный отсутствующий regex/unwrap — UNSUPPORTED_STDLIB_API. Ввод/вывод, сеть, часы и случайность используют explicit registered typed adapter exports из собственного exact package interface, а не неограниченный `std.host.call(String,Any)`.

## 3. Dependency facts, обратный индекс и invalidation

Проверенное использование std порождает прямые typed facts; их полнота нарастает по фазам R21, без обратной записи в прежний immutable stage payload:

- `UsesStdSymbol` — stable ID и exact symbol revision;
- `RequiresType/Predicate` — реально подставленные nominal/type/bound refs;
- `RequiresErrorContract`, `RequiresWorkContract`, `RequiresCodecContract` — отдельно от body implementation;
- `MayPerformEffect` — exact declared effect и bound resource scope; dynamic resource остаётся множеством кандидатов либо unknown;
- `ResolvedByCatalog` — exact catalog/name binding, required для проверки lookup;
- `RequiredAdapter` — service/native/provider contract, без выдачи capability.

**Владельцы facts:** P2 resolve выдаёт UsesStdSymbol/ResolvedByCatalog, declared Error/Work/Codec dependency refs и отрицательные lookup facts. Эти записи ещё не утверждают successful generic instantiation или effect checking. P3 type создаёт отдельные instantiated RequiresType/Predicate facts по фактической подстановке и validation; P4 effect — отдельные MayPerformEffect/resource scope facts с exact candidates/UNKNOWN. Они ссылаются на прежний resolved use/source occurrence через новый immutable StageResult, а не дописывают P2 payload. RequiredAdapter декларация доступна из exact interface; проверенный provider binding появляется после link/loader gates. Graph provider объединяет только согласованный subject/stage chain и сохраняет coverage gaps для недошедших до соответствующей фазы входов. Неполный P2 graph не объявляется полным typed/effect graph.

Неуспешный lookup тоже имеет read dependency: `AbsentStdSymbol(name,CatalogRef)` либо `DeniedByStdRule(name,ruleRef,CatalogRef)`. Если следующая версия добавит symbol или изменит диагностическое правило, прежний «имя отсутствует» результат становится stale. Отсутствие ребра к symbol не означает отсутствия зависимости на каталог.

Reverse index строится из этих facts по обычным LNK правилам, не отдельными пользовательскими редактируемыми обратными ссылками. При смене библиотечного контракта old/new union выявляет consumers прежней revision. В текущем R24, согласованно с R21 EXACT_INPUTS, **любое изменение catalog/source/lock input даёт cache MISS и новое вычисление**; даже равный name binding не разрешает перенести старый StageResult/origin. Точечная reuse остаётся будущим отдельным профилем: exact ProjectionContract, полный проверенный read footprint, независимый transfer checker, новые subject/result/origin и предписанная R21 validation. R24 такого профиля не создаёт. Знание о точных зависимостях полезно для отчёта impact и планирования проверок, но само по себе не даёт разрешения пропустить compute/check.

**Пример:** `std.map.build` сохранил параметры/return type, но DuplicateKey сменился на last-write-wins. Signature-only ABI check этого не обнаружит. Изменится behavior/error SymbolContractRef; UsesStdSymbol/RequiresErrorContract помечают consumers и их tests устаревшими, preservation/compatibility gate запрещает незаметную замену. Если изменилось лишь описание для человека вне semantic contract, identity вычисляется по установленной projection; нельзя выкинуть effect/error/work поля как «текст» без правила канонизации.

Второй пример: добавление `std.string.normalize` не меняет семантику существующего `concat`, но отменяет прежний negative lookup по новому имени. В текущем exact-input режиме новый каталог требует recompute обоих resolve результатов; будущий профиль может разрешить более узкий перенос только с воротами предыдущего абзаца. Это прямое продолжение механизма двунаправленной связи: граф хранит не только вызов функции, но и точные предпосылки допустимости/отказа.

## 4. Независимые проверки и release gate

Checker independently enumerates provider exports и сравнивает множества с catalog: missing/extra public symbol, duplicate name/ID, wrong kind, mismatched instantiated signature/effects/error/work/codec или mutable alias → reject. Наличие файла manifest не доказывает actual exports. Для type declarations нужны exact arity/layout/tags, не только именованный список. Runtime catalog support сверяется с pinned target, а не принимается из untrusted producer flag.

Release V1 требует замкнутого каталога, всех required contracts, implementation support, conformance cases каждого public API/type и явных диагностик всех catalog exclusions; gate T16/T18 остаётся. Данный проект не разрешает выпустить «V1», где std.store/* постоянно возвращает INPUT_NOT_READY. В dev build такой ответ честно показывает незавершённость обязательного контракта.

Проверка структуры/ссылок этого R24 пакета не выполняет настоящий source resolve, type checking, native linking, durable storage или whole V1 conformance. Будущий checker получает отдельные test vectors и differential oracle по acceptance.md.
