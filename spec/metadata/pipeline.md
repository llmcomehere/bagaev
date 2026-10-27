# R21 metadata — внешние контракты compiler pipeline

`pipeline.schema.json` — Draft 2020-12 shape schema для 12 закрытых kinds. `tools/validate_metadata.py` добавляет только локальные cross-field rules: stage role/status matrices, stage-prefix order, counter sums, diagnostic truncation/causal DAG, spans within declared sizes, origin input inventories, source path collisions и disjoint fixes. Это construction validator, не настоящий compiler, runtime loader, trust checker или foreign codec verifier.

| Kind | Назначение |
|---|---|
| SourceBundle | Authored file inventory и source identity attachment |
| PipelinePlan | Exact source/meaning/lock/tool/target/stage contracts and mode |
| CompileInvocation | Post-resolution связь независимого BuildRecipe с PipelinePlan |
| CompileAttempt | Текущий invocation outcome и actual disjoint work counters |
| StageContract | Versioned provider/checker/rules/input/output/diagnostic/cache boundaries |
| StageResult | Exact stage inputs/outputs/status/blame/intrinsic work and origin/read-set |
| DiagnosticBatch | Current immutable subject, typed locations/params and error summary outside truncatable entries |
| OriginMap | Exact output-to-input/source relation с generated/merged/no-source cases |
| ReadSet | Actual dependency/lookup trace, including absence and enforcement scope |
| CacheEntry | Exact query/result/evidence, без self-declared trusted bit |
| PipelineResult | Contiguous successful stage prefix, separate failed result, emitted artifact only on full success |
| FixCandidate | Exact source base/generation/slices and non-overlapping candidate edits |

Body transport profile `format=R21-META-0.1`. Names such as SOURCE-BUNDLE-0.1, PIPELINE-0.1 и DIAGNOSTIC-PIPE-0.1 обозначают semantic contracts; каждый production FormatContract связывает точную schema и semantics. Outer `ObjectRef.format` задаётся этим exact enclosing contract, а не выводится из произвольного body string. Existing foreign objects retain their own format/codec/native identity under R19/R20.

Новые metadata bodies используют BAG-META-JSON-1: UTF-8, sorted object keys, no whitespace, no NaN/Infinity/floats, decimal U64 counters as canonical strings, bool distinct from integer, no Unicode normalization, no duplicate member keys, strict scalar text. Codec не изменяет bytes чужого payload. ObjectRef hashes actual bytes (SHA-256) и содержит checked decimal byte length; native domain-separated identity сверяется дополнительно. Любой reader bound к другой версии не допускается по одному совпадению label.

Schema не может доказать, что ref имеет preimage bytes, file действительно содержит UTF-8, source coordinate лежит на scalar boundary, NodeId существует, MeaningLock соответствует lock, stage output реализует source, provider trusted, actual work enforcement был включён или signature подлинна. Эти обязательства заданы в spec/toolchain и требуют реальных exact objects/checkers. Source/source-map/ABI payload formats остаются upstream T03–T06/T13 dependencies; root metadata shapes не заменяют их.

Fixtures — **synthetic shape cases**. Their hashes are deterministic placeholders without corresponding production preimages. They intentionally cannot be submitted as a successful real build. Report counts не объединяются с independent model suite. Старые draft reports при расширении schema не суммируются с финальным report.

Повторять generation разрешено только в unsealed disposable draft; builders отказываются при MANIFEST.sha256. Validator отказывается перезаписывать input/report, включая symlink/hardlink aliases; после seal новый report должен лежать вне package. Dependencies pinned в tools/schema-validation-requirements.txt. Actual semantic suite не запускается metadata validator.
