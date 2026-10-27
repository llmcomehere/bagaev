# ADAPTER-FFI-0.1 — native shim и допуск платформы

## 1. Объявление и enforcement

Типизированная декларация эффектов сама по себе не ограничивает произвольную native библиотеку. Поэтому профиль требует broker-mediated execution и actual PlatformAdmission. Отдельный процесс защищает адресное пространство VM при выполнении условий платформы, но не доказывает запрет filesystem/network/time/random или сохранность ресурсов.

Trusted computing base: VM, exact decoder/loader, broker и его authority/storage adapters, supervisor/SandboxFactory, ядро и выбранные платформенные механизмы. Native worker рассматривается как потенциально ошибочный и, для enforcement ресурсов/операций, недоверенный. Даже confinement не доказывает функциональную правильность библиотечного алгоритма.

## 2. Обязательный SandboxFactory contract

Перед исполнением любого untrusted initializer/constructor/library code factory обязан:

1. Проверить exact image/dependency closure, platform revision и policy; открыть только закреплённые image bytes. Запретить изменяемый loader search path, env injection и произвольную dynamic loading.
2. Создать изолированное address space без VM/shared mutable mappings и secrets. У worker нет capability objects, inherited business file descriptors, внешних сокетов или произвольного cwd/env доступа.
3. Установить ограничения до первого untrusted instruction, включая native constructors. Trusted launcher может работать раньше, но не выполняет библиотечный init с широкими правами.
4. Разрешить transport только к своему broker session; block direct business IO и распространение handles в другие процессы. Broker resources доступны только через checked protocol operations.
5. Ограничить память, CPU/physical time, число threads/processes/FDs и ingress/output volume; закрепить kill/fence всей worker group, а не только одного PID.
6. Получить supervisor evidence о действующих ограничениях и immutable identity; self-reported worker READY не выдаёт admission.

Один boolean `sandboxed=true`, запущенный контейнер или список syscalls без учёта открытых дескрипторов не удовлетворяет contract. Нет гарантированного mechanical enforcement на платформе — UNSUPPORTED_PLATFORM до внешнего исполнения, а не запуск с предупреждением.

Portable FFI не фиксирует конкретный ABI ядра. Каждая platform implementation обязана предоставить exact executable policy artifact, список разрешённых системных действий и порядок trusted bootstrap, корректный API для их проверки, patch/version closure и независимые negative tests. Выбор конкретных kernel APIs — обязанность PlatformAdapter implementation; требуемое наблюдаемое поведение здесь не оставлено на его усмотрение. Реальный такой adapter в R23 не создан и не принят.

## 3. Пределы effect guarantee

В основной registry любой FFI вызов имеет HostCall effect; недетерминированность native compute не объявляется чистотой. Confinement закрывает наблюдаемые business resources/IO по policy, а не обещает отсутствие всех физических side channels, CPU timing или микропроцессорных каналов. Эти свойства требуют отдельной модели угроз и не следуют из FFI types.

Worker получает данные, которые caller явно передал; конфиденциальность результатов определяется разрешёнными outputs/operations и внешней policy. Echo переданных данных в разрешённый output является объявленным каналом. Broker не принимает произвольный URL/path из adapter как полномочие; runtime capability проверяется на фактический resource selector.

## 4. Native memory внутри worker

Native shim является частью exact image и владеет своим allocator contract. Любой pointer, length, alignment, mutability, retention и deallocator описаны в его generated binding. Эти pointers остаются внутри worker. Возвращённый buffer копируется в bounded wire frame до освобождения по правильному allocator; VM никогда не вызывает foreign free по пришедшему адресу.

Wrapper проверяет size conversions до cast (size_t/u32/Int64), alignment, nullable/optional, null+length combinations, signedness и host-endian conversion. Struct layout и calling convention вычисляются только по exact native header/ABI/target triple; изменение compiler ABI/library требует новой image и interface compatibility check. Varargs, union с неопределённым active tag и direct function pointer не попадают в переносимый ABI: нужен отдельный фиксированный typed wrapper с описанным преобразованием.

Для retained pointer wrapper держит собственную allocation до native completion/quiescence. Отмена VM не освобождает этот buffer. Если библиотека не позволяет подтвердить прекращение callbacks/access, используется fencing worker group и отдельный broker ledger; поддержка такого binding не обещает cooperative completion.

## 5. Exceptions, panic, threads

C++ exception перехватывается на стороне C++ shim до пересечения несовместимой ABI boundary. Rust unwind/abort и longjmp требуют точного native wrapper policy. Нельзя объявить catch-all универсальной защитой чужого unwinding. Неперехваченный crash/abort завершается worker fault и возможной quiescence памяти процесса после supervisor confirmation; внешний effect outcome остаётся неизвестным.

Native thread может обращаться только к worker-owned памяти и передавать callback через queue. Он не получает VM stack/heap pointer. Deduced thread-safety библиотеки не берётся из const qualifier; shared borrow mode разрешается resource type contract только при достаточном основании implementation admission.

## 6. Admission и обновление

PlatformAdmission закрепляет exact factory/broker/image policy, platform identity/capacity и evidence. Loader проверяет schema/bytes и действительность конкретной runtime policy; исторический успешный тест не заменяет current capability/authority checks. Unsupported native symbol, bad version или missing owned cleanup отклоняется до начала call.

Новая image не подменяет worker существующего call. Старые calls/leases/callbacks удерживают прежнюю exact closure до завершения либо fencing. Новая session имеет новый epoch. Обновление не переносит raw resources/closures между address spaces. Durable reconstruction выполняется зарегистрированным reopen operation с current authority, не десериализацией token.
