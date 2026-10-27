# CACHE-PIPE-0.1 и ORIGIN-PIPE-0.1

**R21 · WORKING_DESIGN.** Повторное использование вычислений и обратная связь source↔IR↔artifact. Эта глава не обещает обратимость произвольного преобразования или ускорение finite эксперимента.

## 1. Две связанные identity

`SemanticPayload` хранит normalized semantic data под exact format/semantic contract. `StageResult` привязывает его к конкретному PipelinePlan/source/MeaningLock/inputs. `OriginMap` отдельно связывает local nodes payload с input nodes/source ranges/rules. Payload может совпасть у двух разных исходников, но StageResult и OriginMap для них различны. Evidence acceptance и current authority не являются частью semantic equality.

**Первая версия использует EXACT_INPUTS cache policy.** Query key включает stage ID/StageContractRef, exact CompilerBuild/provider/checker refs, весь PipelinePlan semantic context, SourceBundleRef, MeaningLockRef, EnvironmentRef, DependencyLockRef, PackageInterfaceClosureRef, TargetProfileRef, all declared input-role refs, complete ScopeInventory/interface lists, limits/work schedule и requested mode. Ordered arrays сохраняют order, unordered sets canonically sorted and unique. Key — domain-separated hash `BAG-PIPE-QUERY-0.1 || 0x00 || canonical(QueryBody)`; saved body сравнивается по exact bytes после hash lookup.

Context означает данные, влияющие на результат: tool/config/semantic policies точны, runtime current authority не кэшируется. Authorization на чтение и использование cache проверяется заново по current host. Если policy управляет допустимостью compiler/provider/checker, её current решение обязателено и при hit; старый policy decision не является разрешением. `PlanRef` можно включить целиком как консервативное superset; исключать поля ради hit без explicit new query contract нельзя.

R20 связывает SourceBundle→Manifest→Lock→PackageInterfaceClosure→MeaningLock. Даже комментарий может изменить exact chain. R21 не переписывает её, не заменяет lock на список похожих packages и не переносит old source evidence. При любой такой разнице baseline cache miss и recompute. Dual payload/origin design оставляет возможность будущему checked projection profile, но в PIPELINE-0.1 **нет автоматического cross-source transfer**.

Будущий profile обязан иметь exact ProjectionContract, доказанный complete read footprint, exact transfer checker, domain, ID remapping и fresh OriginMap/diagnostics/StageResult. До появления этих bytes `REUSE_ACROSS_SOURCE` возвращает UNSUPPORTED, а не successful memo hit. Этот запрет сохраняет весь V1 semantics; он не требует пересоздавать общедоступные immutable package blobs, совпавшие по exact ref.

## 2. Что находится в cache entry

CacheEntry: query body/ref, exact successful StageResultRef, read-set ref, producer/checker evidence refs, payload refs, format/profile, byte counts. Entry не содержит принимаемых на веру `trusted=true`, `complete=true` или supplied authority. Cache key не служит operation key R16 и не выдаёт право внешнего действия.

Cache may be corrupt or adversarial. Два пути допускаются явной policy:

1. **RECOMPUTE_CHECK:** выполнить exact provider и boundary checker заново на current verified inputs и сравнить full output/result semantic body; old diagnostics rebind только при exact source identity. Это доказывает соответствие текущей реализации, не ускорение.
2. **ADMITTED_PRODUCER_CHECK:** evidence связывает exact query, provider/checker builds, enforcement domain и complete outputs; evidence подлинно, current policy доверяет этому producer/checker и допустимости их methods, поддерживается full format; независимый invariant checker повторно проверяет loadable bytes. Источник claim не может сам себя включить в trust roots.

Ни hash, ни подпись, ни успешный loader typecheck сами по себе не доказывают source→output правильность. Другой well-typed linked program с теми же signatures может пройти structural loader. При отсутствии admitted derivation/recomputation cache entry MISS/UNTRUSTED, source claim не выдаётся. Semantic preserving proof для optimizer — отдельное основание T13-C03.

## 3. Проверка и восстановление кэша

```text
lookup(query):
  check current cancellation, budget and read/use policy
  canonicalize query using exact query contract
  fetch only by exact key; if absent -> MISS
  verify saved QueryBody exact equality, not hash alone
  verify entry schema, all refs, complete status and limits
  verify every read-set dependency including negative lookup scope inventories
  verify current producer/checker admission or recompute exact result
  load output with its explicit codec; recheck boundary invariants
  reject diagnostics/maps for a different source/subject
  check current cancellation and remaining validation/publication budget
  return HIT only with the same complete StageResult identity
```

Historical `StageResult.work_units` описывает intrinsic work исходной стадии, а текущие cache/recompute/check costs идут в отдельный CompileAttempt. Hit сохраняет StageResult identity, но не получает нулевой work charge или освобождение от current cancellation. Измерения wall time не участвуют в semantic hash результата; они могут храниться только отдельными observations.

Corrupt derived cache entry is quarantined and recomputed under the same plan; it does not become source-error. Corrupt required source/lock/contract is UNTRUSTED and blocks operation, not recoverable by fetching «latest». Provider/checker unavailability даёт INPUT_NOT_READY; нельзя подменить implementation по same version label. Untrusted well-formed entry does not overwrite a trusted one by last-writer-wins.

Cache write uses fresh staging objects, complete validation and atomic pointer insert conditioned on exact key/query identity. Interrupted/provider-fault/canceled/limited results are not successful entries. PIPELINE-0.1 does not cache failures: this avoids accidentally treating transient missing input or incomplete diagnostic result as a deterministic negative proof. Unknown cache metadata fields are not stripped silently. GC may drop reconstructable cache after honoring active reader pins; canonical source/evidence/receipts are outside this cache lifecycle.

On restart incomplete cache transactions are absent or quarantined. A persisted complete entry is verified afresh under current policy before use. Multiworker identical key must converge to byte-identical complete result under the same deterministic profile; differing successful payloads give NONDETERMINISTIC_PROVIDER and both are excluded from reusable success until resolved. Wall-clock/ordering observations belong outside deterministic query body unless explicitly semantic inputs.

## 4. Dependencies, absence and invalidation

ReadSet stores actual typed dependencies and purpose: SOURCE_BYTES, SCOPE_INVENTORY, PACKAGE_INTERFACE, TYPE_CONTRACT, EFFECT_CONTRACT, TARGET_ABI, TOOL_BUILD, OUTPUT_CODEC, LIMIT_PROFILE. Whole-plan exact key is baseline and protects unspecified fine-grained changes. The read-set supports explanation/auditing and future narrower queries; it does not weaken the key.

For lookup of `foo`, the result depends on the full visible scope chain and explicit import inventories, including scopes in which `foo` was absent. If a nearer scope gains `foo`, the previous outer binding is invalidated even though the previous target remains unchanged. Duplicate/ambiguous exports similarly invalidate prior successes. Record an ordered trace `(ScopeInventoryRef, spelling/namespace, FOUND|ABSENT|AMBIGUOUS, result EntityRef?)`; stage invariants recompute it under exact rules. Negative result is not global proof that `foo` does not exist elsewhere.

Type/effect/lowering/link changes invalidate all dependent complete stage results. The baseline graph conservatively uses complete predecessor output, not selected superficial fields. Discovery of an untracked input gives UNDECLARED_INPUT and invalidates the affected query; no silent edge insertion after claiming success. A future dynamic dependency algorithm must preserve order of earlier reads and branch decisions and construct a fresh read-set after reevaluation, rather than unioning incompatible branches.

## 5. OriginMap без ложной обратимости

OriginMap binds exact **primary output role** из stage registry и его OutputPayloadRef, SourceBundleRef, source contract, transformation rule contract, ordered input PayloadRefs and complete node inventory digest. It does not affect the hash of the output payload to which it refers. Each executable/generated LocalNodeId основного output has one coverage entry; an entry may have many origins. Source nodes removed from semantic projection may have an `ERASED_OR_INERT` reverse annotation; comments/whitespace remain in LosslessCST, not invented runtime nodes.

Entry roles:

- DIRECT: output node derives from named input node and its exact source range.
- GENERATED: rule-generated node; exact rule/input anchor, optional human source anchor and explicit generated marker.
- MERGED: multiple input nodes; all origins retained in prescribed order, no chosen «main» source used as inverse.
- DUPLICATED: one input yields several output nodes, each names the same origin plus transformation slot.
- NO_SOURCE: justified synthetic entry/runtime bridge with rule+reason; source position is null, not zero fabricated as real.

Map verification сначала сверяет OriginMap.output_payload_ref с outputs[StageResult.origin_output_role] и normative primary role, затем enumerates actual output nodes under exact payload decoder; compares full covered ID set with no duplicates/missing entries; checks every input node exists in a declared InputPayloadRef, every range belongs to exact source bytes, generated slots/rule IDs match derivation and graph is acyclic across immutable stage order. It validates provenance consistency, not semantic correctness of the lowering rule. Source range for a multi-origin node can be a list; scalar range API must return AMBIGUOUS_ORIGIN or explicitly labelled primary display anchor.

Reverse index is derived from this canonical map plus stage lineage; it can be rebuilt and cannot authorize mutation. Query `explain(output node)` follows emit→link→lower→effect/type/resolve→parse/source and returns exact identities, transformation rules, package clauses and evidence statuses. Query `affected(source node)` walks forward dependencies to stale checks/builds/evidence. Unknown mapping/evidence remains UNKNOWN, not empty affected set.

Structural edit starts from an explicit authored SourceBundle/version, selected EntityId and desired change. It creates a candidate patch with exact guard, reruns pipeline and impact checking, then uses ordinary acceptance workflow. Runtime observation can motivate such a proposal but never rewrites accepted source. No total `uncompile(binary)->original source` is claimed: generated/merged/erased forms, comments and original names require preserved source/CST/map, not inference from machine code.

## 6. Cost/effect preservation and debugging

Origin links do not establish equivalent execution. A transformed program may return the same Int64 yet spend fewer logical steps, observe cancellation at a different point or perform another effect prefix. Executable equivalence must bind the observation domain including result/errors, logical charges, cancellation boundaries, effect requests/replies and required state outcomes. R21 first target preserves reference lowering without optional optimization; finite compiler model is not a proof of runtime simulation.

Debugger obtains a recorded exact ExecutableRef/ProgramRef/StateRef/frame LocalNodeId, then follows matching OriginMap. Missing source or map yields unavailable/stale explanation. Inspecting trace does not rerun a program or host effect. Replaying a different compiler build, current source head or default MeaningLock cannot stand in for the recorded execution. Full debugger operations remain T14; this contract supplies the binding it must consume.

## 7. Проверяемые отличия от предыдущего проекта

1. Stage identity, source origin и semantic payload разделены, каждый имеет точные проверяемые зависимости.
2. Кэш учитывает отсутствие имени в просмотренном scope; наличие старого target не оправдывает reuse.
3. Истинность source→output claim не выводится из hash/typecheck/producer-supplied PASS.
4. Source-only edit может менять MeaningLock через R20; baseline reuse запрещён без exact equality.
5. Обратный путь даёт explanation/candidate edit, сохраняя ambiguity и guards.

Все пять правил имеют independent finite witnesses там, где модель это представляет, и отдельные real integration classes. Наличие модели не переводит непроверенные production claims в PASS.
