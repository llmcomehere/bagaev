# R22 metadata · форма и граница проверки

Schema: [preservation.schema.json](preservation.schema.json), profile R22-META-0.1. Формат содержит восемь закрытых kinds: ObservationContract, OptimizationRequest, RewriteStep, CheckpointPlan, PreservationCertificate, VerificationReceipt, DeoptDescriptor, OutputMapSet.

Общий shape слой использует JSON Schema 2020-12. Для production exact codec BAG-META-JSON-1 запрещает duplicate keys, nonfinite/float integers, непарные Unicode surrogates, unknown fields и oversized bytes. Все reference hashes — lowercase SHA256 без trailing newline. ObjectRef(bytes,sha256,format) обозначает внешние exact bytes, не semantic truth или author authority.

## Что делает local validator

validate_metadata.py проверяет schema и перечисленные локальные отношения:

- parent обязателен, когда transform input отличается от invariant origin;
- before/after фактического rewrite различны;
- checkpoint count, contiguous positions и уникальность charge dimensions;
- непрерывность before/after цепочки до exact candidate;
- непустое пересечение поддержанных interval/enum/exact-ref constraints;
- отсутствие VALID при incomplete coverage, diagnostic codes или превышенном work limit;
- уникальные budget kinds и operation keys deopt;
- полный упорядоченный map set candidate+reference seed;
- отсутствие floats/surrogates во всём decoded metadata.

Он не загружает ObjectRef preimages, не доказывает WF полного IR, scope/dominance, validity values/states, equality реальных outputs, отсутствие скрытых effects или soundness rule checker. Claimed counts/complete в certificate остаются предложенными данными до семантического протокола [PRESERVE-CHECK](../toolchain/preservation-checking.md). В частности, schema-valid receipt не является настоящим выполненным свидетельством.

Фикстуры намеренно содержат синтетические hashes без файлов-preimages. Итоговые59 probes =12 valid shapes +47 invalid shapes/relationships. Их результат нельзя использовать как исполненный production certificate. Форматы конкретных IR, reconstruction payloads, StageResult-OPT и runtime boundary принадлежат exact отдельным FormatContracts; отсутствие этих реализаций остаётся INPUT_NOT_READY.

## Область проверки

Конструктор и конечный эксперимент R22 в этот исходный пакет не входят. Схема описывает форму метаданных; она сама по себе не доказывает корректность преобразований, свойства runtime или полноту V1. Проверка промышленного исполнения требует отдельной реализации и независимых свидетельств.

Примечание к составу: экспериментальные пакеты R16–R23 не включены; упоминания их проверок описывают границы метода, а не результаты запуска этого пакета.
