# FFI-TOOLCHAIN-0.1 — связь с компилятором и загрузчиком

Предлагаемые новые admissions: P2-FFI-RESOLVE-0.1, P4-FFI-EFFECT-0.1, P5-FFI-LOWER-0.1, P6-FFI-LINK-0.1, P7-FFI-EMIT-0.1, TARGET-FFI-0.1. Они дополняют, а не молча переписывают exact R21/R22 profiles. Loader прежнего профиля отвергает новые обязательные формы. Конкретный executable указывает весь согласованный stage registry.

## 1. Resolve/type/effect

P2 разрешает имя extern только в pinned adapter/interface registry из exact lock closure. Никакого скачивания или поиска по current host library path. P3/type проверяет все ground slots и Fn/resource/callback signatures, включая phantom parameter metadata и все payload branches. P4 включает HostCall и транзитивные callback/cleanup effect bounds; authority object не создаётся из успешного анализа.

Заявление «pure» во внешнем манифесте не разрешает removal/reorder. Неизвестная форма ABI, missing type/codec/admission или несовместимая функция дают явный prelaunch diagnostic. Valid signature не заменяет valid ownership/native/platform implementation.

## 2. Lower/link/emit

P5 понижает extern call в REGISTERED_FFI_CALL с exact function/interface/source occurrence, ordered slot descriptors и references на call/codec/charge contract. Callback создаётся отдельной CALLBACK_REGISTER с exact lexical capture, lifetime и signature; resource operations — RESOURCE_BORROW/MOVE/CLOSE по зарегистрированному typed contract. Runtime effect/resource type registry обязателен; формы не реализуются fallback к обычному const или неизвестному host symbol.

P6 проверяет совместимость type/ABI/profile/target и точные callable exports всех adapter artifacts. Формы связываются с index в immutable binding table. P7 emits reference executable плюс FFIBindingTable, AdapterClosure, requiredPlatformPolicies, origin map и соответствующие StageResults. Основной executable содержит ссылки на уже сформированные raw binding payloads, а не на будущий StageResult/receipt с ссылкой на него. Финальные attestations создаются после bytes.

BuildPlan inputs заранее содержат source, lock, registries, stage contracts и tool/platform declarations. Результаты связывания/проверок/emit не добавляются задним числом во входы той же сборки. BuildObservations закрепляет реальные outputs. Родительские R21/R22 артефакты не изменяются.

## 3. Loader и запуск

Loader проверяет exact executable, binding table, closure и origin map; допускает только supported full profile set. Он не принимает одни хеши без соответствующих bytes/schema проверки. До worker start выполняется PlatformAdmission и SandboxFactory. Current application authority проверяется при каждом реальном dispatch, а не только загрузке.

FunctionId неизменяемо относится к одному interface revision; совпадение имён не даёт binary/source compatibility. Даже косметическое изменение bytes меняет exact artifact identity; отдельное доказанное compatibility relation может разрешить новую сборку, но не подменить pinned worker уже выполняющегося call.

## 4. Оптимизация, диагностика и reverse origin

R22 initial optimizer оставляет REGISTERED_FFI_CALL/CALLBACK/RESOURCE формы по exact reference semantics и сохраняет logical charges/occurrences. Ни result-only equivalence, ни доверие хешу не разрешает слияние effects, удаление callback или изменение lease lifetime. Deoptimization сохраняет call/lease/operation identities и не повторяет dispatch.

Origin map связывает runtime fault/callback/lease transition с точным source node и invocation occurrence; line number — дополнительная подсказка. Native stack trace доступен как diagnostic дополнительного artifact и не заменяет source origin. Внешний путь не предоставляет edit authority исходнику.

## 5. Обязательные реальные зависимости

Требуются actual complete form/charge/type registry, compiler effect analysis, runtime callback scheduler, broker authority/storage, native shim generator и PlatformAdapter. Отсутствие реализации отражается NOT_RUN/INPUT_NOT_READY, а не скрытой передачей решения разработчику. Этот модуль не заявляет готовность соседних T05/T06/T13-C01/C03 критериев и не начисляет им повторные баллы.

## 6. Ациклическое построение идентичностей

Порядок materialization обязателен: (1) raw InterfaceDeclaration/ResourceDeclaration/CallbackSignature/ground type/effect/ownership policy, (2) FunctionContract/ResourceTypeContract/CallbackContract, (3) worker image с этими уже существующими interfaces и exact dependencies, (4) AdapterManifest, (5) compiled FFIBindingTable/executable, (6) StageResults/build observations. Stable AdapterId является именем namespace, не hash будущего manifest. FunctionContract ссылается на AdapterId и preexisting InterfaceDeclarationRef; обратная ссылка на будущий AdapterManifestRef запрещена. RESOURCE и CALLBACK slots ссылаются на предварительные ResourceDeclarationRef и CallbackSignatureRef, а не на будущие ResourceTypeContract/CallbackContract, которые могли бы сослаться обратно на FunctionContract. Контракты ресурсов и callback ссылаются на те же предварительные declarations/signatures и OperationContract; это направленный ациклический граф. Manifest перечисляет exact contract refs и image closure.

PlatformAdmission — заранее существующий exact контракт допуска конкретной factory/policy/capacity с evidence, а не квитанция запуска будущего worker. Он не содержит hash того AdapterManifest, который на него ссылается. Текущая проверка factory формирует отдельный LaunchReceipt после существования manifest и установки actual controls. LaunchReceipt закрепляет manifest, policy, session epoch и наблюдения supervisor; он не встраивается обратно в immutable manifest. READY только сравнивается с этим trusted ledger.

Для вызова broker сначала выделяет call/lease/callback IDs, формирует raw prepared input vector и его digest без transport header/binding fields. Затем создаёт CallBinding с exact manifest/function/request digest и session/execution/occurrence. INVOKE body/header ссылаются на готовый CallBinding. CallBinding не ссылается на будущие INVOKE/REPLY bytes, receipt или release. Mutable broker ledger привязывает tokens к готовому binding; это state transition, не циклический content-addressed artifact.
