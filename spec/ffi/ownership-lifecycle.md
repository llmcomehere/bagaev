# OWN-FFI-0.1 — владение и прекращение доступа

Ресурсный token — ссылка на запись broker, не адрес и не переносимое полномочие. Полный ключ: (AuthorityDomain, SessionEpoch, ResourceType, SlotId, Generation). Worker token связывается также с CallId, LeaseId и mode. Caller не создаёт записи registry через DATA decoder. Псевдослучайный token скрывает выбор записи, но безопасность требует проверки ledger и channel, а не только трудности угадывания.

## 1. Виды владения

| Mode | До dispatch | После dispatch | Когда снова доступен caller |
| --- | --- | --- | --- |
| COPY DATA | Неизменяемый input и приватная snapshot copy | Worker получает только собственную копию | Исходное значение доступно всегда; output появляется отдельным значением |
| BORROW_SHARED | Счётчик reservation, owner сохраняется | Одновременные shared leases; запрещены mutate/move/close | Каждый lease снимается после проверенной quiescence; owner и shared reads допустимы согласно типу |
| BORROW_EXCLUSIVE | Эксклюзивная reservation | Owner не использует ресурс; другие borrows/move/close запрещены | После quiescence и снятия единственного lease |
| OWN / move | Ресурс reserved; caller пока не может конкурирующе использовать | Владение передано call; старый caller token недоступен | Только через отдельный объявленный return-resource transfer с новым token/lease, либо никогда при consume |

Каждый resource type объявляет read/mutate/close operations и допустимые modes. Shared borrow не даёт права mutate через alias. Изменение фактического external resource возможно только broker operation с совместимым lease и текущим capability; сам token не разрешает эффект.

## 2. Проверка alias и атомарное reserve

VM статически отслеживает линейное использование OWN там, где это выражается типами; broker повторяет runtime проверку независимо от типов. На prepare ресурсы нормализуются по полному key, не по разным текстовым token. Повторные shared borrows допускаются как отдельные leases с точным multiplicity; любой OWN или EXCLUSIVE вместе с другим slot того же key запрещён до dispatch. Shared aliases в callback проверяются тем же правилом.

Broker сериализует ledger transitions. Алгоритм reserve: проверить все keys/types/generations/owners/modes; вычислить полный план; проверить total caps; только затем атомарно записать все reservations. Отказ одного slot не оставляет частичную reservation. Каждый reservation привязан к одной exact request binding.

До DISPATCH_COMMITTED отмена/отказ освобождает reservations и приватные копии. Никакого OWN transfer ещё не было. Начало записи transport bytes запрещено до DISPATCH_COMMITTED. Сама запись не может быть атомарной с удалённым эффектом; protocol не обещает обратного.

## 3. Dispatch и окно неопределённости

На DISPATCH_COMMITTED broker под одним authority/ledger gate проверяет актуальные права, все reservations и call binding, записывает transfer ledger и durable MayHaveRun для effectful intent, переводит OWN и leases, затем разрешает одну отправку INVOKE. Crash после записи, но до отправки остаётся консервативно MayHaveRun. Transport failure не возвращает переданный ресурс caller автоматически.

Возврат ресурса после такого окна требует отдельного доказательства, что старый worker и все его операции fenced и больше не могут получить доступ, плюс разрешения судьбы ресурса согласно type contract. Для внешнего ресурса это может оставаться ReleasePending/Unknown. No retry не превращается в потерю ledger.

Внутри session ID и поколения не оборачиваются. При UInt64 exhaustion слот навсегда retired; новый admission получает новый slot/session. Restart меняет SessionEpoch; старые tokens не оживают. Recovered durable data не восстанавливает live host handles из сериализованных чисел.

## 4. Quiescence и два подтверждения

Результат REPLY не является release. Worker может уже вернуть значение, пока его внутренний callback или broker operation ещё обращается к ресурсу.

Для release broker требует:

1. Exact call/session/generation и полное множество ожидаемых leases.
2. Закрытие admission новых callback/broker requests данного call.
3. Завершение или отдельно fenced состояние всех уже принятых callback и broker operations, которые могут обращаться к ресурсу.
4. Основание quiescence worker: cooperative notice при допущенном adapter contract либо проверенное завершение всех процессов/threads этой worker session.
5. Атомарную запись ReleaseReceipt и обновление ledger.

Cooperative notice допустим только для adapter implementation, чья quiescence guarantee входит в проверенный admission; непроверенное поле `released=true` недостаточно. Для потенциально враждебного native worker release memory scope подтверждает supervisor process-tree death; broker отдельно закрывает доступ к собственным ресурсам и ожидает admitted operations. Не все такие operations прерываемы.

После release shared/exclusive leases снимаются. OWN судьба задана function/resource contract: CONSUME закрывает/retire ресурс после обязательного cleanup; RETURN передаёт новое caller ownership через отдельную проверенную выдачу broker. OWN не превращается в borrow при отмене. Нормальный поздний output с ресурсом после termination caller не публикуется: broker получает обязанность cleanup такого orphan resource, сохраняя её до CloseReceipt.

ReleaseReceipt не означает effect settlement. Для факта Committed/ConfirmedNotApplied требуется отдельная авторитетная receipt/evidence. Termination caller также не меняется.

## 5. Close, GC и ошибки cleanup

`close(handle)` — явная зарегистрированная операция; эффект и authority заданы ResourceTypeContract. Close линеаризуется только при отсутствии active/reserved leases и наличии current close authority; иначе Busy либо точный boundary fault. Во время close ресурс находится Closing, новые borrows/moves запрещены.

Повтор close того же полного исторического key возвращает stored CloseReceipt после текущей проверки права видеть receipt. Он не обращается к новому поколению того же slot. Use после close даёт ClosedHandle; use после move — MovedHandle; чужой type/session/generation — InvalidHandle/StaleHandle. Close receipts/tombstones удерживаются до retirement session/authority namespace, исключающего приём старых keys.

GC не выполняет произвольный внешний destructor на стеке VM. Он передаёт broker обязанность cleanup. Эта обязанность имеет исходное scope, exact operation и узкую cleanup authority: она может прекратить доступ/закрыть собственный ресурс, но не совершить новое бизнес-действие. Отозванное право на бизнес-операцию не заставляет навсегда удерживать память; если обязательный внешний cleanup требует иного права, состояние остаётся CleanupPending до authority resolution.

Неуспешный native destructor, panic, timeout или неизвестный remote close outcome не отмечается Closed. Блокируется повторное использование; retained ledger/backpressure сохраняет обязательство. Нельзя вытеснить pending resources по TTL только ради освобождения квоты. ResourceLimit запрещает новые вызовы, не стирая старые pending obligations.

## 6. Callback lifetime

Closure capture остаётся сильной ссылкой в VM callback registry. Token связан с call, signature, generation и max invocation count. После caller termination admission callback закрывается, уже принятые исполнения завершаются/останавливаются по общему runtime policy; capture освобождается только после их завершения и quiescence producer.

Deregister request лишь закрывает новый admission; acknowledgement без доказательства прекращения доступа не освобождает target. Поздний callback получает CallbackExpired и не разыменовывает старую closure. Callback tokens нельзя вернуть из scoped call, сохранить через WireData, перенести в другую session или использовать с другой сигнатурой. Долгоживущая подписка требует отдельного зарегистрированного Subscription resource с собственным lifetime и close contract; она не получается автоматически из scoped token.

## 7. Что нельзя выводить из модели

Finite R23 model проверяет bounded reservations, transfer consume handles, atomic output slot и доверенное входное ack. Она не подтверждает настоящую quiescence ОС, remote cleanup, сохранность при power loss или невозможность подделки токенов внешним атакующим. Для этих свойств нужны actual adapters/platform tests и отдельные evidence refs.
