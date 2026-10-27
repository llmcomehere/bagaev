# CALL-FFI-0.1 — эффекты, вызовы и обратные вызовы

## 1. Состояние и ordering

`CallRecord` содержит immutable CallBinding, phase, request/response arenas, transfer ledger, callback registrations, inbox cursor, exact source occurrence, shared budget ref, authority snapshot-at-admission и отдельные current checks, external intents, termination и release/settlement receipts.

Фазы: NEW → PREPARING → PREPARED → DISPATCH_COMMITTED → WAITING → DECODING → READY_TO_PUBLISH → RETURNED. Ошибка/отмена из нетерминальной фазы фиксирует соответствующий caller termination. Resource/effect ledger продолжает существовать после него. Возврат подвыражения идёт в прежний caller continuation, не завершает всю программу.

На каждой language boundary: уже terminal → visible cancellation → semantic resource limit → проверка условий соответствующего action → один charged transition. CANCELLED выигрывает у budget=0. Подготовленный результат ещё не terminal до PUBLISH. После PUBLISH, завершившего всю программу, поздний cancel не переписывает результат.

FFI transitions PREPARE_BEGIN, RESERVE, DISPATCH, ACCEPT_RESPONSE, PUBLISH, CALLBACK_ADMIT, CALLBACK_RETURN стоят по1 logical step; промежуточный codec — точные actions [codec-machine.md](codec-machine.md). Входные expressions вычислены строго по language order до PREPARE_BEGIN. Ожидание host не сжигает бесконечные logical steps: machine Waiting публикует ожидание, а scheduler возвращает управление при recorded external event/cancel. Wall-clock timeout — отдельный explicit timeout operation либо ImplementationStop, не выдуманный step budget.

## 2. Алгоритм обычного вызова

```text
PREPARE_BEGIN: resolve exact manifest/function/admission and source occurrence
encode every DATA input, in slot order, under shared budget
RESERVE: atomically validate all handle/callback bindings and reserve ledger
DISPATCH:
  under broker authority gate check current permissions and exact request
  commit transfer + effect intent/admission before one permitted transport send
WAITING: keep caller continuation; accept only bound events from this session
ACCEPT_RESPONSE: pin exact candidate bytes/outcome in private arena
  decode all output slots in declaration order with no partial publication
READY_TO_PUBLISH:
  require all admitted callbacks completed
  require resource outputs have valid broker ownership and prior access quiescent
PUBLISH: atomically publish all new immutable values/resource handles
  close callback admission; mark caller return; retain independent obligations
```

DATA-only return может предшествовать worker quiescence и settlement, если нет незавершённых callbacks, а contract допускает отдельную позднюю release. Resource output никогда не становится caller-owned одновременно с прежним active owner/borrow. Если один output slot некорректен либо его ownership не готово, никакой output не публикуется; новые ресурсы переходят в orphan cleanup ledger. При terminal caller поздний valid reply дополняет diagnostic/settlement history и cleanup, но не возвращает значение в VM.

REPLY VALUE может содержать обычный Result.Err. FAULT означает boundary failure, не Err приложения. Неверная схема/identity/tag/lease/дополнительное поле — AdapterContractFault. Malformed reply не даёт ConfirmedNotApplied или quiescence.

## 3. Effect bound и current authority

Каждая FFI функция имеет эффект `HostCall(adapter,function)` независимо от заявления native автора о «чистоте». Сигнатура включает разрешённые broker effects и effects callbacks/cleanup. Это не позволяет оптимизатору удалять FFI вызов, CSE-ить его или предвычислять по старым ответам. Особый pure foreign intrinsic возможен только как другая зарегистрированная semantic primitive с отдельным достаточным основанием; в этом профиле его нет.

Worker не получает authority object и не утверждает свою разрешённость списком `reported_effects`. Broker сам создаёт наблюдения из фактических разрешённых операций. Каждый BROKER_REQUEST проверяется по exact function allowlist, фактическому ResourceRef, lease mode, operation contract, current capability и retained call admission. Он может быть отказан даже после успешного начала функции, если право отозвано.

Revocation и dispatch сериализуются одним authoritative gate данного scope. Если revoke линеаризован раньше dispatch, действие не разрешено; если позже — уже разрешённое действие не объявляется отозванным задним числом. Реальный adapter обязан принимать выданный fence/admission; capability check вне gate не доказывает такой порядок. При невозможности доказать актуальность authority новые эффекты закрываются с AUTHORITY_UNAVAILABLE.

Effectful durable commands используют exact R16 intent/key contract. CallId не заменяет IdempotencyKey. Повтор known receipt требует current read access до раскрытия; stale attempt guard проверяется после authoritative existing receipt lookup. Неидемпотентный внешний API без lookup/reconciliation остаётся MayHaveRun после потери ответа; автоматический retry запрещён.

## 4. Cancellation, cleanup и replay

До DISPATCH_COMMITTED cancellation снимает reservation и не посылает INVOKE. После него caller фиксирует Cancelled, broker закрывает новое callback/effect admission этого call, отправляет CANCEL_NOTICE не более одного раза и сохраняет все уже начатые операции. Отправка notice не является подтверждением остановки.

Cleanup/reconciliation исполняются supervisor/broker под отдельной узкой authority и своими limits, а не за счёт сброшенного бюджета terminated caller. Это управление существующими обязательствами, не разрешение новых business effects. Failed cleanup остаётся pending и ограничивает admission новых calls. Удаление heap объекта caller не удаляет ledger.

Replay использует exact recorded input binding, response/event order, logical visibility, adapter/interface revision и resource lifecycle events. Replay не запускает native worker, не выдаёт реальные host handles и не отправляет повторные effects. Resource values представлены replay-only tokens в отдельном namespace, который broker никогда не принимает для live operation. Missing/corrupt/mismatched journal даёт ReplayInputMissing/ReplayBindingMismatch. Reconciliation неизвестного live intent — отдельная операция, а не дополнение replay обращением к миру.

## 5. Callbacks без чужого стека VM

Callback slot связывает exact Fn signature/closure, effect bound, allowed resource leases, parent CallId, generation и ограничение invocation count. Closure/captures остаются в VM registry. Worker передаёт только token и типизированные значения. Нативный trampoline worker преобразует callback в frame и ожидает либо возвращает объявленный async result; VM никогда не исполняется на чужом native thread.

Broker принимает CALLBACK_REQUEST в монотонном callback_sequence, проверяет lifetime, exact signature, parent Waiting/Decoding state, admission и caps. Уже terminal caller → CallbackExpired. Запрос с тем же sequence и теми же bytes получает stored callback outcome без повторного исполнения, если receipt сохранилась; conflicting duplicate → fault. Session frame sequence при этом всегда новый. Callback receipts удерживаются до quiescence call; нельзя удалить их и снова исполнить тот же sequence.

При CALLBACK_ADMIT child continuation ставится в ту же single-thread VM scheduling queue. Родитель ждёт; child использует тот же остаток semantic budgets и authority intersection: исходная caller authority ∩ current authority ∩ callback bound ∩ parent admitted resource scope. Контракт не создаёт полномочия из type/effect declaration. Callback effects включаются в function effect bound статически; actual resource checks выполняются снова при dispatch.

Child closure вычисляется по обычной семантике языка, включая recursion и ordinary Result. После успешного вычисления child value charged CALLBACK_RETURN публикует его в callback receipt и frame. Ordinary Result.Err — такое же value. Если shared budget уже исчерпан или видима cancellation до CALLBACK_RETURN, значение не публикуется: parent execution и active callback фиксируют тот же SemanticStop на этой boundary.

Boundary/semantic/implementation stop child переводит parent call в соответствующий terminal failure, закрывает admission новых callbacks/effects этого call и оставляет outstanding obligations. Для сообщения об этом native wrapper используется отдельный supervisor control-plane `CALLBACK_FAULT_DELIVERY` под maintenance quota. Он записывает/передаёт typed FAULT и release/cleanup bookkeeping; не является language transition CALLBACK_RETURN, не списывает и не пополняет exhausted caller budget, не запускает пользовательский код или новые business effects и не возобновляет parent. Если control-plane delivery тоже не может завершиться, call остаётся pending в ledger до fencing/reconciliation. Native wrapper обязан иметь объявленный способ получить failure, не прячет его в случайное success value. Исключение/abort worker не пересекает стек VM.

### Reentrancy и deadlock

Broker ведёт граф ожидания: call→worker-slot, worker-slot→callback, callback→nested-call. Перед новым nested dispatch добавление ребра проверяется bounded DFS на цикл. Появление цикла даёт ReentrantCallDenied до отправки. Вызов того же занятого worker обычно образует цикл; свободный другой worker разрешён при доступной квоте и отсутствии цикла. Проверка включает slots и outstanding exclusive leases; попытка захватить ресурс, удерживаемый ancestor, отклоняется как ResourceBusy/ReentrantCallDenied, а не ждёт бесконечно.

В пределах V1 callback admission/execution сериализован. Для внешних thread callbacks ingress присваивает order в broker journal; replay читает этот order. Это не обещание одинакового wall-clock порядка разных live запусков. Default max callback depth32, max invocations/call1024, queue1024; overflow закрывает новый admission и выдаёт определённый fault, не уничтожая уже принятые obligations.

Scoped callbacks действуют только до quiescence parent. Долгоживущая подписка — explicit Subscription resource с close/unregister/quiescence contract и отдельными effect/budget policies; без такого зарегистрированного resource использование scoped token после return запрещено.

## 6. Диагностическая запись

Каждый boundary fault содержит stable code, phase, source/occurrence, exact adapter/function/interface, slot/path, expected/actual category и отдельное external knowledge. Credentials и сырые адреса не пишутся. Wire fault value — record FFIBoundaryFault(code:String, detail:String, relatedSlot:Option<Int64>), где code принадлежит закрытому реестру diagnostics, detail≤4096 UTF8 bytes, relatedSlot отсутствует либо 0..255. Его exact nominal schema входит в registry и CallBinding; String code не даёт открытый extension namespace.

Unknown external data преобразуются в domain Err только через объявленный adapter decoder. Internal decoder invariant violation — ImplementationStop; decoder rejection malformed worker payload — AdapterContractFault. После обоих release/effect knowledge остаются самостоятельными.
