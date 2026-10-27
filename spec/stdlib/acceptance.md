# Проверка и маршрут реализации стандартной библиотеки

**R24: это план conformance, не выполненные тесты.** Машинная матрица содержит по одному конкретному сценарию для каждой из 57 callable функций и 28 сквозных сценариев; все 85 имеют NOT_RUN. Ожидания написаны автором проекта; независимые executable oracles ещё должны быть реализованы. Structure/hash проверка пакета не переименовывается в conformance.

## 1. Обязательная последовательность

1. Закрепить полный type/primitive/error registry и source→typed IR binding; один ArithmeticError exact type для новой V1, явные translations исторических исследовательских профилей.
2. Реализовать immutable catalog/type declarations, manifest/lock loader и resolver; отдельно независимый export checker. Проверить все неизвестные/запрещённые имена, prefix boundaries и отрицательные lookup dependencies.
3. В reference VM реализовать pure schedules и prepared-closure continuation bridge, без reset бюджета. Для scalar/text/collections — независимые математические oracles; для UTF8 — заранее сформированные валидные/невалидные bytes и offsets; ни один oracle не импортирует provider functions.
4. Для каждого callback/container/Result сценария выполнить budget/cancel cut до каждого объявленного action, включая LIB_RETURN; сравнить полный actual result/trace с independent expected и сохранить оба, а не только hash.
5. Закрыть VALUE-CODEC-V1 как отдельный exact contract; создать межреализационные golden vectors для каждого type, bounds и malformed data. R07 bytes не утверждать production default. После этого допустить std.codec.
6. Замкнуть STORE/EVENTS/APP-IDEMPOTENCY/CAPABILITY/JOURNAL/REGISTERED-SERVICE contracts; проверить атомарность, authority, crash/restart/retention/gap на actual adapter. Успешная pure модель не является этим gate.
7. Прогнать source programs через R21 pipeline/reference loader с exact dependency set и R22 preservation checks; сравнить actual provider exports с catalog и type/effect/work refs. Повторить на каждом заявленном target.
8. Независимое whole-scope review, устранение расхождений, evidence acceptance T16/T18. До этого catalog остаётся WORKING_DESIGN и не даёт готовности языка.

Для каждого actual case сохранить exact inputs, runtime/source/compiler/catalog/dependency versions, intended schedule, expected и полный actual, pass/fail, related Source/IR/StateRefs и scope. Физическая остановка имеет отдельный статус и не выдается за математический отказ. Для destructive/native integration нужен подходящий изолированный fixture, не пользовательский production state.

## 2. Сценарии по API

| ID / symbol | Вход | Ожидаемый исход |
| --- | --- | --- |
| SA-001 `std.bool.not` | true | false |
| SA-002 `std.i64.eq` | MIN,MAX | false |
| SA-003 `std.i64.lt` | MIN,MAX | true |
| SA-004 `std.i64.add` | MAX,1 | Err(Overflow) |
| SA-005 `std.i64.sub` | MIN,1 | Err(Overflow) |
| SA-006 `std.i64.mul` | MIN,-1 | Err(Overflow) |
| SA-007 `std.i64.div` | MIN,-1 | Err(Overflow) |
| SA-008 `std.i64.rem` | MIN,-1 | Ok(0) |
| SA-009 `std.i64.neg` | MIN | Err(Overflow) |
| SA-010 `std.i64.parse_decimal` | "99999999999999999999x" | Err(InvalidSyntax(index=20,reason=InvalidDigit)) |
| SA-011 `std.i64.format_decimal` | MIN | "-9223372036854775808" |
| SA-012 `std.value.equal` | Map<Int64,Option<Int64>>{1:None}, same map | true |
| SA-013 `std.value.compare` | Int64(-1),Int64(0) | -1 |
| SA-014 `std.option.is_some` | None<Int64> | false |
| SA-015 `std.option.value_or` | Some(5), ready default9 | 5; default expression was already evaluated |
| SA-016 `std.option.map_pure` | None<Int64>, Fn Int64→Int64 divergent body with {} | None<Int64>; callback body calls0 |
| SA-017 `std.result.is_ok` | Err<String,Int64>(7) | false |
| SA-018 `std.result.map_pure` | Err<Int64,String>("e"), f(x)=x+1 returning Int64 via explicit Match | Err("e"); calls0 |
| SA-019 `std.result.map_error_pure` | Ok<Int64,String>(8), f(e)=scalar_length(e) | Ok(8); calls0 |
| SA-020 `std.seq.length` | Seq<Int64>[] | 0 |
| SA-021 `std.seq.get` | [10,20], -1 | None |
| SA-022 `std.seq.append` | [10],20 | [10,20]; old=[10] |
| SA-023 `std.seq.concat` | [1,2],[3] | [1,2,3] |
| SA-024 `std.seq.slice` | [1,2],2,2 | Ok([]) |
| SA-025 `std.seq.map_pure` | [1,2], f(x)=x | [1,2]; call order[1,2] |
| SA-026 `std.seq.fold_pure` | [1,2], initial10, f(acc,x)=10*acc+x with explicit checked-error handling | 1012 |
| SA-027 `std.map.build` | [Entry(2,"a"),Entry(1,"b"),Entry(2,"c")] | Err(DataError{DuplicateKey,first=0,second=2}) |
| SA-028 `std.map.get` | {1:"a",3:"c"},2 | None |
| SA-029 `std.map.length` | Map<Int64,Int64>{} | 0 |
| SA-030 `std.map.entries` | {3:"c",1:"a"} | [Entry(1,"a"),Entry(3,"c")] |
| SA-031 `std.map.put` | {1:"a",3:"c"},1,"new" | {1:"new",3:"c"}; old map unchanged |
| SA-032 `std.map.remove` | {1:"a",3:"c"},2 | map semantically equal to original |
| SA-033 `std.string.scalar_length` | "😀" | 1 |
| SA-034 `std.string.scalar_get` | "A😀",1 | Some(128512) |
| SA-035 `std.string.slice` | "A😀B",1,2 | Ok("😀") |
| SA-036 `std.string.concat` | "e","́" | two scalars U+0065 U+0301; no normalization |
| SA-037 `std.string.from_scalars` | [65,55296,66] | Err(ScalarError{index=1,value=55296}) |
| SA-038 `std.string.to_scalars` | "😀" | [128512] |
| SA-039 `std.bytes.length` | Bytes[F0,9F,98,80] | 4 |
| SA-040 `std.bytes.get` | Bytes[FF],0 | Some(255) |
| SA-041 `std.bytes.slice` | Bytes[F0,9F,98,80],0,1 | Ok(Bytes[F0]); no UTF8 validation |
| SA-042 `std.bytes.concat` | Bytes[00],Bytes[FF] | Bytes[00,FF] |
| SA-043 `std.bytes.from_octets` | [0,256,1] | Err(OctetError{index=1,value=256}) |
| SA-044 `std.bytes.to_octets` | Bytes[00,FF] | [0,255] |
| SA-045 `std.utf8.encode` | "﻿" | Bytes[EF,BB,BF] exactly |
| SA-046 `std.utf8.decode` | Bytes[C0,80] | Err(DataError{Utf8Leading,first=0,second=-1}) |
| SA-047 `std.codec.encode` | Int64(-1), exact admitted VALUE-CODEC-V1 | exact independent golden bytes of this codec; fixture blocked until contract exists |
| SA-048 `std.codec.decode` | exact encoded Int64(7), matching VALUE-CODEC-V1 | Ok(7); foreign context must Err according to locked codec |
| SA-049 `std.test.check` | "c1",false | Fail(TestFailure{case_id="c1",code=ConditionFalse(Unit)}) |
| SA-050 `std.test.check_equal` | "c2",Int64(1),Int64(2) | Fail(TestFailure{case_id="c2",code=ValueMismatch(Unit)}) |
| SA-051 `std.test.all` | [Pass("x"),Fail(TestFailure{case_id="x",code=ConditionFalse(Unit)})] | {total=2,passed=1,failed=1,failures=[{index=1,failure:TestFailure{case_id="x",code=ConditionFalse(Unit)}}]} |
| SA-052 `std.store.snapshot` | authorized root S=7 at ActiveRef generation4; concurrent change to generation5 | one coherent {active4,7} or {active5,newS}, never mixed |
| SA-053 `std.store.commit` | same admitted KeyRef with same semantic request; head changed after first Applied | same historical Applied receipt; no second root/outbox commit |
| SA-054 `std.store.status` | retired KeyRef, historical receipt payload deleted | ClosedWithoutPayload if retained intent ID; otherwise AdmissionClosed; never KnownNotAdmitted from missing payload |
| SA-055 `std.events.read` | cursor position2, pinned frontier5, limit2, complete log | positions3,4; next4; frontier5 |
| SA-056 `std.events.apply` | same consumer/event payload, already Applied; changed new root proposal and current head | historical Applied receipt; no new root/outbox/frontier change |
| SA-057 `std.events.status` | ConsumerCap without status/read permission | PermissionDenied; no receipt disclosure, no new apply |

## 3. Сквозные отказы и наблюдения

| ID / правило | Воздействие | Ожидание |
| --- | --- | --- |
| SX-001 NEG-LOOKUP | std.seq.mpa_pure | UNKNOWN_STDLIB_SYMBOL; no fuzzy correction into executable |
| SX-002 PREFIX-BOUNDARY | std.gpuX.run | UNKNOWN_STDLIB_SYMBOL; not UNSUPPORTED_PROFILE from std.gpu |
| SX-003 TYPE-KIND | call std.types.BoundsError as function | STDLIB_KIND_MISMATCH; record construction uses language form |
| SX-004 MISSING-SERVICE | std.store.commit with no APP-IDEMPOTENCY-V1 exact artifact | INPUT_NOT_READY; V1 required obligation remains open |
| SX-005 WRONG-BINDING | same name/version label with altered behavior bytes | hash/kind/contract mismatch; never silently use bytes |
| SX-006 NO-NATIVE-SUBSTITUTION | trusted service export replaced by native FFI provider needing HostCall | STDLIB_CONTRACT_MISMATCH until explicit admitted signature/revision |
| SX-007 UNREACHABLE | unknown std API inside dead branch/unused declaration | resolve diagnostic before launch; not optimized away |
| SX-008 EFFECTFUL-FN | map_pure supplied Fn with nonempty effect set | Type/effect diagnostic; no implicit effect-row instantiation |
| SX-009 STRICT-DEFAULT | value_or(Some(5), divergent default expression) | default executes; SemanticStop possible before entering value_or |
| SX-010 WHOLE-EQ | equal(None<Fn>,None<Fn>) | predicate diagnostic even though actual payload empty |
| SX-011 PHANTOM | registered Phantom<Fn>{} with no Fn payload fields | Eq/Persistable follow instantiated fields; descriptor identity preserved |
| SX-012 TYPE-NOMINAL | compare PersonId and ArticleId same physical layout | TypeMismatch, not false or0 |
| SX-013 SLICE-BOUNDS | slice length2 start2 end1 | Err BoundsError{length2,start2,end1}; no clamp |
| SX-014 MAP-OPERANDS | duplicate early map pair then late effect/divergence expression | all source operands processed before duplicate detection; late termination can prevent build |
| SX-015 CANCEL-RETURN | cancel visible before LIB_RETURN after successful inner traversal | Cancelled; no partially published value |
| SX-016 SHARED-BUDGET | map callback exhausted parent remaining budget | BudgetExceeded; no callback budget reset; no returned partial Seq |
| SX-017 ZERO-WIRE | huge count of Unit/empty-record values | prospective nodes/arena bound applies despite tiny payload bytes |
| SX-018 SERVICE-ROLES | consumer with root A, input log B, output log C | three distinct resource dependency bindings; current authorization checked per role |
| SX-019 REVOKED-READ | receipt exists; permission revoked before duplicate/status read | PermissionDenied, no receipt leak/no fresh execution |
| SX-020 KEY-CONFLICT | same user KeyRef but changed expected state or replacement root | KeyConflict, unlike intentional event same-identity dedup rule |
| SX-021 LOST-ACK | crash after durable local commit before returned response | retained intent; lookup returns same Applied when established; no auto new key/retry |
| SX-022 EVENT-GAP | required page range has lost retained entry | JournalGap, not empty success; no advance over gap |
| SX-023 EVENT-ORDER | fresh consumer apply skips next event position | InvalidArgument before commit; duplicate history remains accessible first |
| SX-024 EVENT-PAYLOAD | same event_id with different payload_digest | conflict; no rewrite of old dedup binding |
| SX-025 NEGATIVE-DEPENDENCY | catalog adds formerly absent std symbol | Absence witness invalidated; source can be resolved anew |
| SX-026 ERROR-DEPENDENCY | map.build silently changes duplicate behavior, signature unchanged | Symbol/error contract ref changes; old consumers/evidence stale |
| SX-027 TEST-NO-ACCEPTANCE | all([]) returns summary0/0/0 | does not produce AcceptanceRecord or prove required suite executed |
| SX-028 ACTUAL-EXPORTS | provider exports extra/missing public function vs catalog | independent export set checker rejects; manifest alone insufficient |

## 4. Что даёт независимое ревью этой итерации

Ревью проверяет полноту предлагаемого API, типы/эффекты, алгоритмы и диагностические границы. Оно может обосновать stage2 исходного T13-C05, если весь его предмет покрыт письменным проектом. Stage3 требует actual independent grounds для всего объявленного предмета, stage4 — нормативной приёмки с зависимостями. Число 85 не прибавляется к 96 критериям и не даёт дополнительных баллов.
