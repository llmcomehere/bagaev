# Integrated beta candidate guide

This guide connects the existing language, CLI, local Store and continuation
contracts in one standalone workflow. Bounded integrated execution is recorded
below. See [current status](../README.md#what-exists-today) and
[Issue #18](https://github.com/llmcomehere/bagaev/issues/18) for independent
candidate acceptance and integration status. Commands below
describe how to reproduce the scenario; the measured run used a separately
reviewed execution profile.

## Profile and preparation

The supported implementation profile is local Linux, CPython and CPU, using
only the Python standard library, including SQLite. The integrated run used
CPython 3.14.4 on Linux x86_64 and SQLite 3.46.1; it does not establish
compatibility with every Python, SQLite or OS version.
Windows, macOS, native/GPU, mobile and distributed profiles have no acceptance
claim here. No package installation, provider account or private workspace is
needed.

Start at the root of a clean standalone checkout. Read [AGENTS](../AGENTS.md)
and the selected source before execution. Use an independently reviewed,
authorized local execution profile with synthetic data, owned temporary/output
storage, resource limits and no credentials. These instructions do not supply
isolation or authorize running an untrusted change. Record the exact checkout,
interpreter and SQLite versions with any result.

## Recorded integrated result

Runtime source revision `a29b62b45408db28fb81eea2bb83db860a86aa32` passed the
second complete M6 run: 88 selected, started and successful product methods,
with zero failures, errors, skips, expected failures or unexpected successes.
This covers L0, L1, catalog reference, L2, toolchain, Store, model library and
the beta scenario. The 17 L1-checker and eight candidate-checker methods were
not selected or run; this is not the full 113-method suite.

Independent comparison matched 792 catalog observations: all 99 frozen cases
on each of four retained snapshots, through reference and CPython engines.
The beta scenario recorded two successful fresh processes and 69 CLI calls
(26 predecessor, 43 successor): 62 successes and seven intentional refusals.
It retained A1 at generation 2, continued to A3 at generation 4 and restored
the exact snapshot. Separate Store methods exercised precommit/postcommit
process interruption. Observer controls rejected 17 malformed frame/test
reports, ten wrong catalog observations and eight wrong beta receipts; three
additional checks distinguished JSON scalar types.

The three execution units (probe, product suite and catalog comparison) exited
0 with complete capture and empty stderr; outer supervision exited 0 and
confirmed cleanup with no remaining owned handles. The reviewed local profile
capped memory at 768 MiB with no swap, tasks at 16, CPU at 50% of one core,
scratch at 128 MiB and individual files at 32 MiB. Deadlines were 480 seconds
overall, 300 seconds for the suite and 120 seconds for catalog comparison
(five seconds for the probe). These are bounds, not performance measurements.

The first run exposed a test-observer UTF-8 serialization error before a frozen
surrogate input reached evaluation. The observer was corrected without changing
language behavior or frozen expectations, and the complete second run passed.
No speed, reliability-rate or cost benefit is inferred from these local results.

## Run the integrated scenario

The [selected test](../tests/test_beta.py) invokes the actual public CLI in
subprocesses. It copies public source and examples into a fresh temporary
directory, then starts a predecessor and a separate successor interpreter.
From the repository root, after the preparation above:

```sh
python3 -B -S -m src.bagaev --version
BAGAEV_BETA_RECEIPT="$PWD/beta-primary.json" python3 -B -S tests/test_beta.py BetaTests.test_cli_persisted_continuation_and_restore -v
```

Choose a new receipt filename: it must not already exist. The optional
`BAGAEV_BETA_RECEIPT` asks the test parent to retain a JSON report of at most
2 MiB after temporary files are removed. The parent directory must exist.
Without it the test still runs, but its temporary Store and detailed capture
are removed. Keep raw reports local; they can contain local paths and process
IDs. The test starts processes and writes temporary programs, artifacts,
SQLite state and backups; it is not a static check.

An expected successful result is exactly one selected test, `OK`, exit 0,
no skips, and report `schema: "bagaev-beta-primary/1"`, `status: "PASSED"`.
The report retains both phase exits and each CLI call's arguments, timeout
flag and base64-encoded stdout/stderr. Expected phase exits are both 0, with
26 predecessor and 43 successor CLI calls; seven deliberate CLI refusals
exit 2. A failed assertion, timeout or missing capture is not acceptance.
This command does not select the other product or specialized checker tests;
do not describe it as a full-suite run.

| Phase | Expected behavior and retained observation |
| --- | --- |
| Create and change | Check and inspect catalog A0, run its frozen `REV-0` case through reference and verified CPython paths, then admit it. Apply the 01 patch, check `REV-1` on both paths, and admit A1. |
| Persist unfinished work | Retain immutable A0/A1, patch objects, receipts and an unfinished continuation. Its attempted admission refuses. Persist the remaining A2/A3 work, head and snapshot; predecessor ends with head generation 2. |
| Continue in a fresh process | Read retained files and Store facts, verify their identities, reconcile the A1 receipt, then apply patches 12 and 23. Check frozen `REV-2` and `REV-3` expectations on both engines before each admission; finish at A3, generation 4. |
| Refuse stale or altered inputs | Reject stale patch/admission, conflicting operation reuse and altered or wrong-source artifacts. Same-operation, same-request replay returns the original receipt. Refusals leave admitted state unchanged. |
| Back up and restore | Retain the expected full snapshot separately before export. Wrong-snapshot restore creates no destination. Restore into a new directory, compare the exact snapshot, reconcile all four receipts and require byte-identical re-export. Earlier sources and patches remain unchanged. |

The development interruption is an ordinary process ending after persisted A1
and unfinished work. It demonstrates a fresh-process handoff without live
in-memory state; it is not a crash injection or an LLM session. Separate
[Store tests](../tests/test_store.py) contain precommit/postcommit interruption
checks. Neither establishes physical power-loss durability.

The fixed Store policy selects seven frozen revision-0 cases, including
positive and refusal outcomes, that all four checkpoints must preserve.
Checkpoint-specific `REV-0` through `REV-3` checks happen separately before
admission. Passing that policy does not prove the entire application contract:
the [99-case oracle](../examples/beta/catalog-cases.json), chain behavior,
nonmutation and container independence have their own obligations in the
[application contract](application.md). Selected integration observations do
not replace complete language/application acceptance or general backend parity.

For individual commands and a manual A0-to-A3 walkthrough, use the
[toolchain guide](toolchain.md#clean-checkout-walkthrough). The
[Store walkthrough](store.md#cli-and-library-walkthrough) defines policy,
continuation, admission and portable backup inputs. Both work from public
files without the integrated test's temporary state.

## Compatibility, refusals and recovery

These versioned interfaces remain separate; no implicit profile conversion or
Store schema migration is provided:

| Boundary | Version and authoritative contract |
| --- | --- |
| Language and structural changes | `bagaev-l2/1`, `bagaev-l2-patch/1`; [L2](l2.md). L0/L1 retain their separate interfaces. |
| Catalog requests and expectations | `catalog-application/2`, `catalog-cases/2.0.0`; [application](application.md). Behavior selection is explicit. |
| CLI and generated bundle | `bagaev-toolchain/1`, `bagaev-l2-cpython/1`; [toolchain](toolchain.md). A bundle must match the checked source and current generator exactly before execution. |
| Durable state and handoff | `bagaev-store/1` and its version-1 policy, continuation, evidence and package schemas; [Store](store.md). Unsupported schemas refuse intact. |
| Model proposals | `bagaev-model-task/1`, `bagaev-model-response/1`; [model](model.md). Pure proposal data grants no execution or admission authority. |

CLI success is one JSON line with `ok: true`, exit 0. A language/tool/Store
refusal is one line with `ok: false` and a stable error code, exit 2. Host
failure uses stderr and exit 1; help/version are text. An application-level
`kind: "refusal"` is a successfully evaluated value inside a CLI success
envelope, not a CLI error.

Expect `L2_STALE` for a patch against the wrong base, `TOOL_ARTIFACT` for a
changed or mismatched bundle, `STORE_STALE` for an outdated admission base,
`STORE_CHECK` for incomplete obligations/unresolved work, `STORE_OPERATION`
for conflicting operation reuse, and `STORE_CORRUPT` for a mismatched restore
snapshot. Full code/transport/file-effect rules live in the contracts above.
CLI output files and restore destinations must be new; existing data is never
an overwrite target. Use `-B` to suppress bytecode-cache writes.

Candidate puts and checks do not advance head. Admission rechecks the fixed
receiver policy and exact base/generation. If an admission response is lost,
reconcile with `store inspect DIRECTORY --operation ID` before retrying;
use the same ID and request to recover its original receipt. Store access may
recover a SQLite journal and write even during inspection/export. Use owned,
trusted local storage; hashes are content identities, not authentication.

Export is portable canonical JSON, not a copy of a live SQLite database.
Restore requires the matching policy and an independently retained expected
snapshot, preserving head and receipts. Import instead creates an empty active
head under the receiving policy and requires fresh admission. A changed checker
requires import and new admission rather than silent migration. Neither path
reverses or repeats external effects. Preserve an incomplete directory left by
a creation-time crash for inspection before manual cleanup or retry.

## Evidence, contribution and distribution

The [measured model results](model.md#measured-m5-results) include actual model
changes and four fresh successors. This integration scenario makes no new
model calls. Full lifecycle cost remains **indeterminate**, and observed
completion does not prove savings or broad reliability.

Use [CONTRIBUTING](../CONTRIBUTING.md) for a focused fork/branch/PR, exact
base/head, actual checks, skips and limits. Keep a candidate stable for
independent review and serial integration. The
[documentation workflow](../.github/workflows/docs.yml) performs static
documentation/data checks with a trusted-base validator for pull requests;
it does not run the language, product suite, integration scenario or benchmarks.
A green docs check is not runtime acceptance. Sensitive reports follow
[SECURITY](../SECURITY.md); if confidential reporting is unavailable, request
instructions publicly without disclosing details.

A local contribution rehearsal combined two isolated checkout candidates and
one independently based local clone contribution through serial integration,
followed by the combined product run above. This exercised a local fork-style
workflow, not a real external GitHub account, fork or outside-contributor run.

The [roadmap's exit gates](roadmap.md#beta-exit-checklist) also require relevant
combined checks, contribution rehearsal and independent candidate acceptance.
Technical distribution readiness is distinct from publication: a successful
local run does not authorize a release, package upload, visibility/access change
or broader platform claims.
