# WIRE-FFI-0.1 — переносимые значения и кадры

**Предлагаемый exact codec.** Host layout, pointer width, C padding и platform endian не входят в переносимый ABI. Native shim преобразует wire values в собственный локальный ABI по закреплённому contract. Все нижеописанные размеры беззнаковые; арифметика длины проверяется до сложения/умножения и выделения.

## 1. WireDataCodec

Тип известен из exact ground registry. Payload не может выбрать другой тип. Форматы:

| Тип | Байты |
| --- | --- |
| Unit | 0 байт |
| Bool | 1 байт: 00 или 01; остальные запрещены |
| Int64 | 8 байт, two's complement, little endian |
| String | u32 LE число байтов, затем строгий UTF-8 |
| Bytes | u32 LE число байтов, затем ровно эти байты |
| Seq<T> | u32 LE число элементов, затем T в исходном порядке |
| Map<K,V> | u32 LE число пар, затем K,V; строго возрастающий semantic compare_K |
| Record | Поля по порядку exact declaration; каждый со своим instantiated типом |
| Sum | u32 LE ordinal варианта в exact declaration, затем его payload |
| Option<T> | u8 0=None, 1=Some; при 1 следует T |
| Result<T,E> | u8 0=Ok, 1=Err; затем T или E |

В registry distinguish nominal Sum и built-in Option/Result; одинаковая форма значения не делает их типы взаимозаменяемыми. Nominal id/revision/аргументы ground instantiation входят в type identity. Переупорядочивание полей или вариантов меняет ABI identity.

UTF-8 принимает только Unicode scalar values: запрещены overlong sequences, surrogate кодовые точки, неверные continuation bytes и значения выше U+10FFFF. Нормализация Unicode не выполняется. Нулевой байт в String допустим; C shim с NUL-terminated API обязан явно проверить свою дополнительную предпосылку или вернуть объявленный обычный отказ, а не обрезать строку.

Map не сортируется и не исправляется декодером: дубликат или неверный semantic order отвергается. Bytewise порядок encoded Int64 не заменяет semantic compare. Рекурсивные/неизвестные типы не обходятся через длину 0.

## 2. Incremental decode и encode

Точный порядок actions, comparator, prepass, stop boundaries и ручные traces определяет [codec-machine.md](codec-machine.md). Этот документ является нормативным проектом для CODEC-FFI-0.1; реализация не выбирает свои charges по скорости host parser.

До чтения payload проверяются exact registry/type и предел bytes. Decoder использует явный bounded stack и приватную output arena. Encode/Decode не вызывают adapter, callbacks, getters или пользовательский код. При остановке частичный результат не публикуется; исходные DATA неизменны. Map сравнивается по структурному semantic Key order, не по encoded bytes.

## 3. Transport frame

Между broker и worker используется поток кадров. Поля header в таком порядке:

| Поле | Размер |
| --- | ---: |
| magic ASCII BGVFFI01 | 8 |
| revision u16 LE = 1 | 2 |
| kind u8 | 1 |
| reserved u8 = 0 | 1 |
| session_id | 16 |
| call_id | 16 |
| sequence u64 LE | 8 |
| body_length u32 LE | 4 |
| body_sha256 | 32 |

Header всего 88 байт; затем ровно body_length байтов. У hash нет свойства authentication: полномочия выводятся из broker session/channel и ledger. Transport не является публичным сетевым API. CallId уникален внутри session; session epoch не переиспользуется после рестарта. Counter exhaustion запрещает новый кадр/вызов вместо wrap.

`kind`: 1 READY, 2 INVOKE, 3 REPLY, 4 CALLBACK_REQUEST, 5 CALLBACK_REPLY, 6 BROKER_REQUEST, 7 BROKER_REPLY, 8 CANCEL_NOTICE, 9 QUIESCENT_NOTICE, 10 SHUTDOWN_NOTICE. В каждом направлении отдельная монотонная sequence, начиная с 0; sequence относится к session, не сбрасывается для нового call. READY имеет zero call_id; остальные требуют существующего call, кроме SHUTDOWN_NOTICE с zero call_id. Unknown kind/reserved/version, переполнение или несогласованный call отвергаются до payload processing.

## 4. Тело сообщения и schema binding

Body — канонический JSON `FRAME-BODY-0.1`, содержащий только объекты, массивы, строки, bool и null; чисел JSON нет. UInt64 передаётся строкой `0|[1-9][0-9]*` в диапазоне, Int64 внутри DATA binary payload, hex — только lowercase с чётной длиной. Идентификаторы полей ASCII. Ключи объектов сортируются лексикографически по ASCII; whitespace отсутствует. Строки UTF-8 без нормализации, двойная кавычка и backslash экранируются, U+0000..001F только lowercase `\u00xx`, все остальные scalar values буквально. Surrogates, duplicate keys и другие escape-представления отвергаются проверкой decode→canonical encode exact byte equality.

Все тела содержат `binding` — 64 hex SHA256 CallBinding, кроме READY/SHUTDOWN. CallBinding создаётся broker и закрепляет source/execution/occurrence, exact adapter/function/interface, expected input/output slots, operation intent refs и session. Присланный binding сравнивается с ledger, а не принимается как authority.

Закрытые поля тел (никаких дополнительных):

| Kind | Поля |
| --- | --- |
| READY | adapter_manifest, platform_admission, session_epoch |
| INVOKE | binding, inputs, callbacks |
| REPLY | binding, outcome, outputs |
| CALLBACK_REQUEST | binding, callback_token, callback_sequence, inputs |
| CALLBACK_REPLY | binding, callback_token, callback_sequence, outcome, outputs |
| BROKER_REQUEST | binding, operation, operation_sequence, inputs |
| BROKER_REPLY | binding, operation_sequence, outcome, outputs, receipt |
| CANCEL_NOTICE | binding, reason |
| QUIESCENT_NOTICE | binding, released_leases, closed_callbacks |
| SHUTDOWN_NOTICE | reason |

adapter_manifest, platform_admission, operation, signature_ref, type_ref, resource_type и ненулевой receipt — 64 lowercase hex дайджест уже закреплённого объекта; длина/schema/kind берутся из session registry. outcome ровно VALUE либо FAULT. FAULT outputs содержит один DATA boundary-fault record по exact registry, VALUE — объявленные output slots (включая обычный Result.Err). reason — один из CANCELLED, BUDGET_EXCEEDED, CONTRACT_FAULT, IMPLEMENTATION_STOP, NORMAL_SHUTDOWN; применимость проверяется по state/kind. session_epoch, callback_sequence и operation_sequence — строки UInt64; callback_token — 32 lowercase hex. operation обязан присутствовать в exact function broker-operation allowlist. sequence начинаются с0 в своей call области, не оборачиваются; повтор semantic sequence обрабатывается по сохранённой receipt, transport sequence при этом новый. receipt — null либо exact ref доверенной broker receipt; payload worker не создаёт receipt сам.

`inputs`/`outputs` — упорядоченный массив slots. Slot DATA: {kind:"DATA",type_ref,payload_hex}. Slot RESOURCE: {kind:"RESOURCE",resource_type,token,generation,lease,mode}; generation UInt64, token/lease 32 lowercase hex (16 bytes), mode OWN/BORROW_SHARED/BORROW_EXCLUSIVE. Slot CALLBACK: {kind:"CALLBACK",signature_ref,token,generation}; callback slots в outputs запрещены в первом scoped-callback profile. callbacks в INVOKE — массив именно callback slots, соответствующий CALLBACK параметрам, inputs содержит DATA/RESOURCE slots в порядке остальных параметров. Все поля schema/context проверяются, включая одинаковые количества и порядок.

released_leases — массив LeaseId, closed_callbacks — массив CallbackToken; оба элемента имеют 32 lowercase hex, sorted ASCII без дублей. Несколько shared borrows одного ResourceToken имеют разные LeaseId; принимается точное множество выданного call ledger. Само QUIESCENT_NOTICE — заявление worker, не доверенное освобождение. Broker проверяет закрытие собственных outstanding operations/callbacks и fencing согласно ownership contract; до этого release остаётся pending.

### Направления и доверие

Broker→worker: INVOKE, CALLBACK_REPLY, BROKER_REPLY, CANCEL_NOTICE, SHUTDOWN_NOTICE. Worker→broker: READY, REPLY, CALLBACK_REQUEST, BROKER_REQUEST, QUIESCENT_NOTICE, SHUTDOWN_NOTICE. Неверное направление — fault до body semantic dispatch. READY допустим один раз после supervisor-created session и до INVOKE; worker не может выдать PlatformAdmission собственным READY. SHUTDOWN_NOTICE лишь просьба/уведомление: подтверждение завершения создаёт supervisor, а не отправитель.

FAULT outputs — ровно один DATA<FFIBoundaryFault> по [calls-effects-callbacks.md](calls-effects-callbacks.md) и [закрытому реестру кодов](../../registry/data/ffi/ffi-diagnostics.json); resource/callback slots в fault запрещены. VALUE outputs соответствуют exact function/callback/broker return signature. Ошибка типа самим worker не может создать обычный Result.Err, если такой Err не объявлен.

## 5. Приём, потоки и пределы

Receiver сначала читает ровно header, проверяет state/direction/sequence и body_length до выделения. Затем bounded body, hash, строгий canonical JSON и closed kind schema; после этого semantic bindings и typed payload. Частичный EOF — transport fault; выход за лимит не разрешает дочитать бесконечный поток. Повторный frame sequence не выполняется снова, conflicting duplicate изолирует session. Replay работает с журналом и не посылает кадры worker.

Baseline tool defaults: frame body 16 MiB; DATA payload 8 MiB; один String/Bytes 4 MiB; collection entries 65 536; type nodes 65 536; explicit codec stack 1 024; slots 256; ресурсы на call 256; callbacks на call 64; session calls 4 096; pending ingress frames 1 024. Exact LimitsContract может быть строже и входит в admission. Суммарный value_nodes cap 262 144 и arena accounting/caps заданы codec-machine.md; ни малый payload, ни per-collection cap их не заменяют. Эти границы — область данной реализации, не произвольное изменение семантики V1. Все лимиты проверяются также транзитивно: сумма вложенных данных ограничена frame/value cap.

Это проект полного wire protocol. Конечная Python-модель R23 не исполняет этот codec или реальные потоки.
