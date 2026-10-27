# P5-OPT-0.1 · точное включение в R21

Это новая предлагаемая версия контрактов, не молчаливое изменение frozen R21. Старая P5 проверяет canonical reference lowering; её checker не обязан принимать иной optimized output. Успех по новому профилю требует новых exact StageContract/FormatContract/TargetContract и admissions.

## 1. Граница стадий

P1–P4 сохраняют R21 contracts. P5-OPT принимает те же verified typed/effect/source/lock inputs плюс ObservationContract, RuleCatalog, checker admission, mode и limits. Их identifiers включены в PipelinePlan и CompileInvocation до исполнения.

Внутри P5:

1. Построить reference_lowered_ir прежним exact reference algorithm.
2. Проверить его полную equivalence/lowering derivation по R21; отсутствие checker → INPUT_NOT_READY.
3. Связать SourceSubject с authored snapshot и исходным IR; origin_ir = exact reference_lowered_ir.
4. Создать OptimizationRequest с input_ir=origin_ir и parent=null. Он является stage-local input после reference lowering, не задним числом входом всего BuildPlan.
5. Построить candidate и проверить PreservationCertificate.
6. При VALID создать stage outputs с primary lowered_ir=candidate; зафиксировать current attempt work и result.

BuildPlan заранее содержит root source/contracts/config, достаточные для детерминированного получения stage-local OptimizationRequest; StageResult хранит фактически использованный Request. Если Request существует до данной сборки, его можно прямо включить в BuildPlan input inventory. Созданные внутри сборки Request/seed/candidate/certificate/receipt остаются её derived outputs/observations. Exact stage-to-stage bindings проверяются при финальной build validation.

## 2. Output roles и origin maps

| Role | Содержимое | Code-bearing | Карта |
| --- | --- | --- | --- |
| lowered_ir | Проверенный optimized candidate | Да | Обязательная primary origin map |
| reference_lowered_ir | Проверенный reference seed, также возможный deopt source | Да | Собственная обязательная origin map |
| optimization_request | Exact stage-local request | Нет | Ссылки на точные IR/контракты |
| preservation_certificate | Цепочка правил и checkpoint/reconstruction refs | Нет | Ссылки на обе карты и regions |
| preservation_receipt | Результат actual semantic checker | Нет | Exact certificate/checker identities |
| origin_map_set | Закрытый список карт обоих code-bearing roles | Нет | Ровно одна карта на role |

StageResult нового metadata profile содержит primary_origin_output_role=lowered_ir и origin_map_set_ref. Старый single-map StageResult не переиспользуется под новым именем. OutputMapSet записи (role,payload_ref,map_ref) уникальны по role; payload_ref exact равен outputs[role], map.output_ref равен payload_ref. Никакая metadata map не заменяет карту кода. Новое executable тело в auxiliary record требует нового объявленного role и map; неизвестное тело отвергается.

## 3. P6/P7 и runtime

P6-LINK-OPT-0.1 знает все target forms REPLAY_REGION/SCALAR_SLOT/KNOWN_ARM по exact revisions и замыкание original regions/checkpoint pools/deopt code. Проверяет каждую embedded CodeRef, scalar pool type, caller context placeholder и continuation binding. Неизвестная форма → UNSUPPORTED; ссылка на отсутствие foreign code → INPUT_NOT_READY.

P7-EMIT-OPT-0.1 выпускает reference-interpreter image с отдельным target profile для этих forms. Loader декодирует реальные emitted bytes и независимо проверяет linked/candidate closure, map set и preservation receipt admission. Текстовое поле mode=optimized не включает поддержку runtime. Старый loader обязан отвергать новый target profile.

Dispatch target forms реализует exactly-one-logical-event advance, сохраняя source rule identity. Replay region имеет индекс и symbolic context instantiation; scalar slot заменяет только физическое чтение; known arm заменяет физический выбор уже известного continuation. Нативный backend, который исполняет иной code, должен иметь собственный checked translation от linked optimized IR. Сертификат IR не покрывает произвольные emitted bytes.

## 4. Build/release и отсутствие циклов

Derived output inventory перечисляет Request, seed, candidate, certificate, receipt, maps и emitted artifact. Compilation receipt не равен accepted source, нормативной приёмке, release approval или authority runtime.

Certificate ссылается на candidate/seed/request/maps, но candidate/seed не ссылаются на будущий certificate/receipt. Maps ссылаются на payload bytes, не на enclosing StageResult. Receipt ссылается на certificate; StageResult ссылается на outputs. BuildObservations завершает DAG. Никакой back-reference в Manifest/Lock/BuildPlan input inventory этой же попытки.

Executable candidate использует raw checkpoint/reconstruction payloads без candidate/self/map/certificate refs. Объект CheckpointPlan с candidate_ir_ref создаётся позже как metadata и не становится input reference исполняемого candidate. Certificate закрепляет exact OutputMapSet; checker проверяет обе maps до VALID. Это устраняет также цикл candidate→plan metadata→candidate.

Последующая сборка может использовать существующий exact verified candidate как вход нового плана. Это отдельный declared input с current checker/trust compatibility; нельзя выдать его за artifact, заранее существовавший в предыдущем плане.

## 5. Проверка и статус

Необходимы положительные/отрицательные integration cases: новый P5 target принят новым loader, отвергнут старым; wrong primary map; missing seed map; foreign candidate with good receipt; generated Request incorrectly inserted in predeclared inputs; omitted embedded CodeRef; source/target checkpoint mismatch. Статус всех реальных случаев в data/integration-cases.json — NOT_RUN. Эта глава задаёт implementable interface bridge, не подтверждает готовый compiler.
