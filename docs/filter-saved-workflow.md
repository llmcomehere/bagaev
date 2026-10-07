# Explicit saved workflow for pure L2/2

Use this opt-in profile when a [pure filtering](pure-filter.md) program also needs
local saved revisions, checked admission and a later process continuing the work.
The old `/1` receiver does not accept these programs. Nothing migrates an old
store, reinterprets its receipts or changes the original CLI.

| Interface | Existing route | Explicit filtering route |
| --- | --- | --- |
| Program / patch | `bagaev-l2/1`, `bagaev-l2-patch/1` | `bagaev-l2/2`, `bagaev-l2-patch/2` |
| Receiver module | `src.bagaev_store` | `src.bagaev_filter_store` |
| Store / package | `bagaev-store/1`, `bagaev-store-package/1` | `bagaev-filter-store/1`, `bagaev-filter-store-package/1` |
| Workflow CLI | `src.bagaev` | `src.bagaev_filter_workflow` |
| Observation | `bagaev-toolchain/1` | `bagaev-filter-workflow/1` |

Policy, contract, continuation, evidence and checker schemas use the corresponding
`bagaev-filter-store-…/1` names. All receiver schemas are distinct from the old
family. They are also unrelated to the separate typed native component probes.
The pure `src.bagaev_filter` CLI remains pure and has no `store` subcommand.

## Meaning and authority

The [existing Store contract](store.md) supplies the transaction, object, receipt,
policy, continuation, import and restore algorithms and capacities. This explicit
family binds those algorithms to `/2` source/patch checking under the schema names
above. It retains 32 policy cases, 512 stored objects, 128 ledger entries and the
same transport, filesystem and SQLite boundaries. The separate implementation
preserves old source bytes but has an explicit maintenance/duplication cost.

- `put` stores a validated immutable candidate; it does not evaluate the source.
- `check` evaluates the receiver-selected finite cases and records source/contract/
  input/checker-bound observations. It does not advance the head.
- `admit` requires the current base, matching immutable policy, complete successful
  evidence and local replay. It commits a new generation and operation receipt
  atomically. Unresolved obligations or unknown effects still refuse.
- Repeating the exact operation returns its original receipt without changing the
  head. That receipt may name an older generation: inspect the current head rather
  than mistaking replay for a new commit. Conflicting operation reuse refuses.
- `import` keeps incoming admissions as history and starts with an inactive head.
  `restore` requires the receiver's explicit policy and an externally retained
  exact snapshot pin, then replays admitted checks before installing a new store.
  A hash copied from an untrusted package is not recovery authorization.

The checker identity binds the exact new receiver and `/2` checker source files.
Labels or captured observations never authorize execution. Only reviewed source
and a separately authorized bounded execution profile permit actual checks or
runs. These are local finite guarantees, not external exactly-once effects,
physical power-loss proof, independent reproduction or production acceptance.

## Complete bounded walkthrough

After source review and selection of your authorized local execution profile:

```console
python3 -B tests/probes/filter_workflow_checks.py --output "$PWD/filter-workflow-demo"
```

The output directory must be new and absolute. The driver uses the 31 existing
public open-queue cases as the receiver policy. It stores the accepted queue,
admits it, then applies a behavior-preserving `let` refactor and admits the second
source. It checks missing evidence, stale base, operation conflicts, old receipt
replay, no-overwrite export, fresh-command inspection, inactive import, exact
restore and foreign-profile refusal. The refactor changes source identity, not
business behavior. No queue job or external effect is executed.

The script makes 29 actual CLI calls, including six intentional refusals. Successful
completion reports generation 2. Captures contain caller-local paths and should
remain private. `-B` prevents Python cache writes; it is not isolation. The
[driver source](../tests/probes/filter_workflow_checks.py) shows the complete
continuation construction from actual returned identities, rather than hard-coded
receipts that could be stale under another checker.

Individual commands use the separate entry point, for example:

```console
python3 -B -S -m src.bagaev_filter_workflow store init new-filter-store --policy examples/l2-filter/store/policy.json
python3 -B -S -m src.bagaev_filter_workflow store put new-filter-store source examples/l2-filter/queue.json
python3 -B -S -m src.bagaev_filter_workflow store inspect new-filter-store
```

Creation requires a fresh owned directory. `put` returns the source object identity;
use that actual value for `store check`. Construct a continuation with the actual
base, target, change, policy and evidence identities before `store admit`.
The complete executable walkthrough above performs those steps explicitly.
Draft authoring still uses `src.bagaev_filter prepare`; there is no implicit
preparation, version conversion or admission fallback.

## Evidence and limits

Two separate Python command phases checked 31 policy cases, two admissions,
old-receipt replay, reopen, inactive import and exact restore, with nine first-phase
and two second-phase refusals. An initial harness incorrectly assumed distinct
numeric PIDs across execution namespaces and stopped before second-phase work;
that setup failure was retained and the process invocation check corrected.
Numeric PID inequality is not claimed as freshness evidence.

The unchanged old receiver suite and the explicitly rebound suite each passed
16 methods. Two inherited adversarial fixtures initially failed their hash-order
setup condition after schema rebinding. Synthetic version strings were selected
to retain the same evidence-before-malformed-referent condition; refusal codes,
no-creation expectations and receiver code were not weakened. Those setup failures
were not counted as successful negatives. Reused tests are not new independent
semantic cases. The public CLI walkthrough repeated the complete path above.

No model was asked to use this receiver, and no speed, whole-development cost or
adoption improvement is established by these source/runtime observations.
