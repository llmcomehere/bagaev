# CODEC-FFI-0.1 — точная машина обхода и стоимости

Этот документ закрывает порядок действий WIRE-FFI-0.1. Все именованные actions стоят ровно один semantic step. Перед каждым action применяется общий порядок: уже terminal → visible cancel → budget → action. SEAL корневого значения только запечатывает private arena. Decoder/encoder subtree готов лишь после отдельного успешного CHECK_EXACT_END/CHECK_EXACT_SIZE; caller при этом не завершается, а следующий PUBLISH принадлежит FFI call. Бюджет один с вызывающей машиной, без сброса между фазами и callback.

Ниже рекурсивная запись определяет последовательность actions; реализация обязана заменить рекурсивный стек явным bounded stack. Вложенные calls псевдокода не являются бесплатным обходом: каждый новый node начинается ENTER, заканчивается SEAL. Выход из одного frame обновляет только непосредственный parent и возвращается к dispatcher. Единица обработки не зависит от host recursion limit.

## 0. Суммарные лимиты значений

LimitsContract обязательно содержит `value_nodes`, `arena_units`, `wire_bytes`, `stack_depth`; baseline соответственно 262 144, 67 108 864, 8 388 608, 1 024. Отдельно ограниченные counts каждой коллекции не заменяют общую сумму. `value_nodes` увеличивается на каждом ENTER_NODE/SIZE_ENTER, включая Unit, empty record и каждый повторный элемент. При входе в следующий node проверяется prospective count до allocation; отказ — ResourceLimit для incoming external value либо ImplementationStop/CapacityExceeded для уже принятого VM input вне опубликованной tool capacity. Отмена/budget имеют прежний приоритет перед этим action.

`arena_units` — детерминированная мера представления, не обещание физического RSS: 32 за value node, 8 за child slot, 1 за хранимый octet и 4 за Unicode scalar. Типизированная replica incoming data и output representation учитываются по фактически требуемым узлам; String учитывает UTF8 bytes плюс scalar vector. Счётчики prospective checked UInt64 до каждого allocation/append. Компоненты, живущие одновременно (input snapshot, candidate output, codec memo), имеют отдельные ledgers и общий per-call cap из LimitsContract; default общий 134 217 728 units. Этим мерам должен соответствовать отдельный физический memory admission implementation с измеренным overhead; нельзя принять 64 MiB semantic units за точный host allocation limit.

У каждой коллекции заранее резервируются child slots, когда count/record arity/tag известны: Seq n, Map 2n, Record field_count, Sum/Some/Result один, None ноль. Checked multiplication и prospective arena cap проверяются до reservation. Строковые bytes резервируются после LENGTH, scalar slots добавляются до append каждого decoded scalar. Node ENTER увеличивает nodes и резервирует32 units; SEAL не увеличивает count повторно. При failure private arena уничтожается без публикации. Encode size pass учитывает такую же logical value representation и отдельный size memo по32 units на node; emit использует прежний memo, не начисляет nodes второй раз, но резервирует точный output byte buffer до emit под общим cap.

## 1. Decoder

Операции `byte()` и `fixed(n)` означают соответственно один READ_BYTE и n последовательных READ_BYTE. EOF на таком действии завершает decoding BoundaryFault после списания этого action. CHECK выполняется после накопления указанного фиксированного header/scalar; failure не читает следующие bytes. SEAL добавляет готовый immutable child в parent arena. Никакие частичные children caller не видит.

```text
decode(T):
  ENTER_NODE(T)
  Unit: ничего
  Bool: fixed(1); CHECK_FIXED_SCALAR(00|01)
  Int64: fixed(8); CHECK_FIXED_SCALAR(two's complement)
  Bytes: fixed(4); CHECK_LENGTH(n, remaining, limits); fixed(n)
  String: fixed(4); CHECK_LENGTH(n, remaining, limits)
          fixed(n) с UTF8 state update на каждом READ_BYTE
          CHECK_UTF8(final state accepting)
  Seq<U>: fixed(4); CHECK_COUNT(n, limits)
          для i=0..n-1: decode(U)
  Record: для field в declaration order: decode(field.type)
  Sum: fixed(4); CHECK_TAG; decode(exact tag payload)
  Option<U>: fixed(1); CHECK_TAG(0|1); при 1 decode(U)
  Result<U,E>: fixed(1); CHECK_TAG(0|1); decode(U либо E)
  Map<K,V>: fixed(4); CHECK_COUNT(n, limits)
            для i=0..n-1:
              decode(K)
              при i>0: compare_K(previous,current); CHECK_ORDER(result=Less)
              decode(V)
  SEAL_NODE(T)
```

CHECK_LENGTH, CHECK_COUNT, CHECK_TAG, CHECK_UTF8, CHECK_ORDER — разные имена одного action класса CHECK, каждое стоит 1. Проверка `remaining` для Seq не предполагает минимальную длину элемента >0: Unit/пустой record допустимы. Для них применяется count/node cap. UTF8 invalid byte вызывает fault на READ_BYTE, не дожидаясь конца строки; CHECK_UTF8 ловит незавершённую sequence. По окончании root SEAL следующий отдельный CHECK_EXACT_END требует полного использования payload и стоит 1. Payload с trailing bytes отвергается до публикации.

## 2. Semantic Key comparator

Не используется сравнение encoded bytes. Все значения одного exact Key type. Result comparator хранится в отдельном register Less/Equal/Greater.

```text
compare(T,a,b):
  COMPARE_ENTER(T)
  Unit: COMPARE_ATOM -> Equal
  Bool/Int64: COMPARE_ATOM -> математический порядок
  Bytes: COMPARE_LENGTH_PAIR
         для i < min(lengths): COMPARE_BYTE(a[i],b[i]); stop на различии
         если prefix equal, COMPARE_PREFIX_LENGTH -> порядок длин
  String: COMPARE_LENGTH_PAIR (число Unicode scalars)
          для i < min(lengths): COMPARE_SCALAR(a[i],b[i]); stop на различии
          если prefix equal, COMPARE_PREFIX_LENGTH -> порядок длин
  Seq<U>: COMPARE_LENGTH_PAIR
          для i < min(lengths): compare(U,a[i],b[i]); stop на различии
          если prefix equal, COMPARE_PREFIX_LENGTH
  Record: compare каждого field в declaration order, stop на различии
          при пустом/полностью равном record result Equal
  Sum/Option/Result: COMPARE_TAG -> порядок declared ordinal
                    только при равном tag compare(payload) если payload существует
  COMPARE_LEAVE -> вернуть result непосредственному parent
```

Каждое указанное имя — отдельный charged action. При раннем различии выполняется COMPARE_LEAVE каждого уже открытого frame, по одному; последующие children не открываются. Даже одинаковая ссылка a==b не разрешает short-cut. String arena после decode содержит immutable scalar vector и byte representation; длина и доступ по scalar index не запускают скрытое декодирование строки. При encode input String runtime обязан иметь ту же admitted representation либо предварительный charged conversion contract; произвольный host string shortcut не допускается.

Map не является Key. Fn/Handle/Capability/Callback не являются Key. Для nominal type подставляются фактические поля, поэтому phantom type argument без field не создаёт скрытого сравнения. Option ordering None<Some; Result Ok<Err; порядок Sum ровно declaration order. Это совпадает с DATA-0.1 §6 по результату, но вводит свой явно опубликованный FFI action schedule. Общая DATA work machine не вызывается скрыто и не выбирает стоимость за нас.

## 3. Encoder: размер и публикация

Вход — уже принятое immutable typed value. Encoder не исполняет getters или пользовательские encoder hooks. Он сначала выполняет `size(T,value)`, затем `emit(T,value)`. Между фазами остаётся тот же value identity; изменение host backing storage — ImplementationStop.

`size`:

1. SIZE_ENTER(T).
2. SIZE_CHECK: проверить scalar value или count/variant/shape по type; fixed-size Unit/Bool/Int64 добавляют 0/1/8; Bytes добавляет 4+known length; Seq/Map добавляет header4; Sum header4; Option/Result header1; Record header0.
3. Для String выполнить по одному SIZE_CHAR на Unicode scalar, прибавляя длину его UTF8 (1..4), начиная с header4. Недопустимый scalar — ImplementationStop принятого VM value. Для Bytes runtime value уже состоит из octets; cached byte length допустим и не требует второго побайтового validation pass.
4. Для Record/Seq/Sum/Option/Result/Map обработать реальные children в том же порядке, что decode. В Map после size текущего key и перед value вызвать точный comparator §2 и CHECK_ORDER. При несовпадении shape/order — ImplementationStop принятого VM value.
5. SIZE_SEAL: проверить cumulative size/cap, сохранить size в приватном node-indexed memo и прибавить его immediate parent. Все additions checked UInt64. Нет перебора всех siblings в одном seal.

`emit`: EMIT_ENTER(T); WRITE_BYTE для каждого scalar/header byte (LE) и payload String/Bytes; рекурсивно emit children в исходном порядке; EMIT_SEAL(T). Для Sum/Option/Result выбранный tag и children известны из prepass. Emit не сортирует Map и не повторяет compare. Для String scalar→UTF8 выдаёт до4 WRITE_BYTE по одному. После root emit выполняется CHECK_EXACT_SIZE (1 step), затем дальнейший FFI PUBLISH/dispatch по call protocol. Encoder failure до dispatch не даёт частичной отправки.

## 4. Контрольные ручные traces

Это выведенные примеры расписания, не исполненная production suite. Decoder totals включают CHECK_EXACT_END, encoder totals включают CHECK_EXACT_SIZE; PUBLISH/RESERVE/DISPATCH отдельно.

| Значение | Decode actions | Encode actions |
| --- | ---: | ---: |
| Unit | ENTER + SEAL + END = 3 | SIZE_ENTER/CHECK/SEAL + EMIT_ENTER/SEAL + SIZE = 6 |
| Bool true | ENTER + BYTE + CHECK + SEAL + END = 5 | 3 size + ENTER/BYTE/SEAL + SIZE = 7 |
| Int64 0 | ENTER + 8 BYTE + CHECK + SEAL + END = 12 | 3 size + ENTER/8 BYTE/SEAL + SIZE = 14 |
| Bytes empty | ENTER + 4 BYTE + LENGTH + SEAL + END = 8 | 3 size + ENTER/4 BYTE/SEAL + SIZE = 10 |
| String empty | ENTER + 4 BYTE + LENGTH + UTF8 + SEAL + END = 9 | 3 size + ENTER/4 BYTE/SEAL + SIZE = 10 |
| Seq<Unit> из2элементов | 1+4+1+2×2+1+1 = 12 | (1+1+2×3+1)+(1+4+2×2+1)+1 = 20 |

Если бюджет заканчивается перед CHECK_EXACT_END, даже полностью построенное приватное значение не публикуется. Внешние frame parsing/hash/schema checks выполняет bounded broker ingress под собственными физическими и ingress quotas; они не становятся бесплатной работой языка и не увеличивают caller step budget. Caller наблюдает только зарегистрированное событие inbox и свои exact codec actions. Нарушение ingress quota — явный protocol/implementation outcome по источнику нарушения, не BudgetExceeded языка.
