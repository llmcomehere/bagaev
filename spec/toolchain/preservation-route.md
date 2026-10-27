# R22 · маршрут реализации и приёмки

Это план полного T13-C03, связанный с исходным V1. [34 integration cases](../../registry/data/toolchain/preservation-integration-cases.json) имеют конкретные expected outcomes, независимый метод получения ожидания и blocking inputs. **Все34 NOT_RUN для production.** Пройденный finite register experiment имеет собственную область.

## 1. Закрепить единый эталон

Собрать actual versioned source→typed/effect→reference-lowered IR и полный Form/Primitive/ChargeRegistry. Сверить CORE, DATA и их bridge: common budget, explicit entry/finish, Result semantics, source operand order. Нужен complete list обязательных opcodes, а не только13 semantic families из coverage registry.

Выход: ReferenceExecutionContract + full input/output codec + independent oracle agreement. При недостающей обязательной форме этот gate остаётся INPUT_NOT_READY. Cases IC22-01..03,09..13,24.

## 2. Реализовать logical checkpoint runtime

Хранить explicit control/env/K/captures и shared resource vector. Одна advance публикует один registered transition после terminal/cancel/budget проверки. Source occurrence и origin независимы от physical PC. Initial ReconstructionMap сохраняет все slots/frames, сложное сжатие не требуется.

Проверить stop до/после каждого logical event, terminal tie, cancel+zero tie, local ready value vs program return, repeated call occurrences. Cases IC22-01,04,08,09,18.

## 3. Закрытый scalar optimizer и checker

Реализовать три rule matchers из OPT-RULES, bounded local evaluator, scoped lexical fact derivation и known-arm builder. Producer предлагает immutable candidate; checker независимо от supplied annotations выводит разрешённые replacements. Shared checker counters не сбрасываются при local cap/KEEP.

Первый полезный target уже меняет physical arithmetic/condition work, сохраняя exact source boundaries. Не вводить unregistered optimizations из host optimizer без собственного downstream translation contract. Cases IC22-01..08,18,19,22,34.

## 4. Полная цепочка certificate

Materialize exact references; validate request/source/origin/input/candidate separately; check all chained before/after objects, local maps и untouched contexts. Parent-chain traversal iterative/bounded, no content cycles. Финальный candidate равен computed chain output; no partially validated executable.

При composition пересечь exact supported constraints, сохранить source lineage и previous checkpoint relation. Пригодность finite evidence проверяется по kind; даже1191positive checks не превращают finite subjects в universal admission. Cases IC22-18..21,29,30.

## 5. Новый pipeline target

Ввести exact P5-OPT/P6-LINK-OPT/P7-EMIT-OPT/StageResult-OPT/runtime admissions по [pipeline-bridge](pipeline-bridge.md). Все code-bearing outputs имеют отдельные maps. Loader проверяет реальные bytes; reference certificate IR не разрешает подменённый executable.

BuildPlan только с заранее доступными inputs; generated Request/seed/candidate/certificate/receipt/map output фиксируются в BuildObservations. Cases IC22-25..28.

## 6. Effects, authority, deopt

При наличии actual lifecycle/ABI implementations сохранить current capability check и exact dispatch/reply/settlement. Переключать target→reference на published boundary с прежними input, budgets, journal/keys; поздний settlement не меняет termination.

Initial deopt с identity slots — конкретный безопасный путь. Durable migration/recovery требует собственной атомарности и не получается из локального state mapping. Cases IC22-14..17,33.

## 7. Независимая проверка всего claim

Нужны два слоя: локальные общие preservation/progress lemmas каждой admitted rule/target form и differential executions с независимо полученными state/event observations. Область кванторов, environment strategies и platform capacity публикуются. Для unbounded recursion указать termination/progress мера каждого physical segment; finite cutpoints не являются доказательством всех возможных циклов.

Негативные witness должны портить value, rule/node/occurrence, K, budget, event order, authority, receipt/settlement, subject/version, maps и emitted bytes. Исключения ошибочного harness не считать найденной compiler mutation. Cases IC22-18,19,23,31,32.

## 8. Производительность и нормативная приёмка

После корректности измерить source/reference/optimized variants на одинаковом workload/inputs/runtime. Отдельно учитывать compilation+checking, caches, checkpoints/reconstruction, memory и host execution. Названные finite counters arithmetic/condition/unwrap не являются benchmark.

Для stage3 всему T13-C03 необходимо независимое подтверждение всей принятой области, а не лишь одного scalar kernel. Для stage4 дополнительно: готовые upstream contracts/actual integration, воспроизводимая сборка, неизменные evidence subjects, explicit normative acceptance и корректный общий audit. R22 этих статусов не присваивает.

## Что уже выполнено в R22

Проект отношения, concrete rules/checker algorithms, полный family dispatch, pipeline bridge, metadata construction и независимый finite execution. Finite profile:10 инструкций, forward CFG, Int -16..15, ordinary Result.Err, explicit unwrap/trap, in-memory effects. Его costs не равны CORE: каждая register instruction стоит один шаг. Оно проверяет принцип сохранения checkpoints на ограниченной модели.

Independent suite:23 authored program families;1109 API cases (1060 runs,23 compile,17 plans,9 codecs),69 invalid-input guards,10 executed semantic mutants,3 provenance/contracts. Total1191. Повторения для determinism/nonmutation не добавляют checks. Provider smoke30 и итоговая root metadata59 отдельно; output guards9 отдельно. Superseded54 metadata probes не прибавляются. Полные результаты и ограничения: verification notes (`r22:results/preservation-verification-notes.md`).
