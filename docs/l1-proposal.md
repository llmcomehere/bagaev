# L1 profile proposal: bounded CPython backend

Status: accepted bounded backend contract; selected local evidence is recorded
below. L1 emits self-contained deterministic CPython artifacts for all L0. The
selected local evidence recorded 41 of 41 cases matching, 17 checker tests,
and 10 generator tests with zero failures or skips and exit 0 on observed CPython
3.14.4. This is selected-case evidence only: it is not universal equivalence,
native compilation or a model/cost result. [Issue #11](https://github.com/llmcomehere/bagaev/issues/11)
owns integration status.

This document fixes the backend contract and is not permission to compile, run,
install, fetch, or modify L0. The [L0 contract](l0.md) and frozen P0 inputs and
expectations remain unchanged and outside this profile's execution scope.

Sections 1–4 preserve the original proposal and acceptance contract. Their
future-tense references to generation, execution, and checking describe the
planned gates at that stage, not current implementation status. The status
above records the later selected observations; it does not verify another
machine, a current interpreter installation, or behavior beyond those cases.

## 1. Backend selection

Chosen backend: **CPython 3.14.4 at `/usr/bin/python3`**, used as the
execution engine for a generated deterministic artifact.

Historical read-only discovery and version query (2026-09-23) recorded that
`/usr/bin/python3` resolved to `python3.14`, and its `--version` reported
Python 3.14.4. That query invoked the interpreter only to report its version;
it provided no compilation, candidate-code, test, or generated-artifact result.
The selected execution evidence in the status above is a separate later
observation; a version query alone does not establish runtime behavior.

That discovery did not verify standard-library integrity or generated-artifact
behavior. The later selected results do not establish behavior outside their
checked scope or availability/integrity of runtime and isolation tools on a
future check machine.

Why this backend is useful for a small language prototype:

- The L0 reference interpreter `src/bagaev_l0.py` already runs on CPython
  with standard library only, so the semantic oracle and the backend share
  one runtime family and one JSON library; canonicalization and digest
  behavior can be compared without cross-language ambiguity.
- No installation, dependency, or network access is needed.
- The existing reviewed isolation precedent in `tools/check_l0.py` already
  invokes `/usr/bin/python3 -I -B -S` under sandboxing, so a later execution
  profile has a concrete local template.
- Interpreted execution matches the profile's goal (interpreter-equivalence
  evidence); native performance is explicitly not promised.

## 2. Admitted language and semantics

- **Admitted subset: whole L0**, exactly as defined in [l0.md](l0.md)
  revision pinned by the accepted input revision
  `dd526aa3e5ad3c165948561f33313e99de432ce4`: all ten operations, all four
  types (`int`, `bool`, `string`, `string_list`), and every bound (1–256
  nodes, ≤1048576 JSON bytes, ≤4096 UTF-8 bytes per string, ≤256 list items,
  1–32 concat items, signed 64-bit integers). L0 is already bounded, so no
  further restriction is needed for a first profile.
- **Input/output semantics:** evaluation returns the value of `run_program`;
  the artifact's CLI emits the L0 `run` envelope. It accepts one program
  fixed at generation time and one inputs JSON object, with exact declared
  input keys, types, and bounds. On success it prints exactly one JSON object
  with `schema:"bagaev/l0-result/v1"`, `ok:true`, `command:"run"`,
  `program_digest`, `result_type`, and `result`, then exits 0. A language,
  JSON, bound, or input error prints exactly one object with the same schema,
  `ok:false`, `command:"run"`, and `error:{code,message}`, then exits 2.
  `error.code` is stable; `error.message` must be a short path-free English
  string, but its wording is not an equivalence key.
- **Deterministic artifact form:** a single self-contained UTF-8 Python
  source file, standard-library only, generated from a `CompiledProgram`.
  The artifact embeds the source program digest (`sha256:...` as defined in
  l0.md). The generator records the artifact bytes' SHA-256 and its own
  revision. The later runner pins a private read-only copy, checks its SHA-256
  immediately before execution, and executes that same copy; identical
  canonical programs at one generator revision produce byte-identical artifacts.
- **Unsupported operations and rejection:** within whole L0 there are no
  unsupported operations. Anything outside L0 is rejected before generation
  by the existing `compile_program` validation. Before emission, the
  generator revalidates the canonical program and checks its digest and
  execution plan against the supplied `CompiledProgram`, whose nested fields
  are mutable. It refuses a mismatch or unknown operation without emitting
  code. Runtime overflow and result-size violations reject the run without a
  partial result, as in L0.
- **Oracle:** the reference interpreter `src/bagaev_l0.py` remains the
  semantic oracle. Artifact output is correct only insofar as it matches
  `run_program` (value, error code, exit behavior) on the same inputs.
  Generation never redefines semantics; any disagreement is an artifact
  defect.

## 3. Generation and execution boundary

- **Artifact owner:** the generator is trusted project tooling (a future,
  separately reviewed change); the emitted artifact is candidate-controlled
  output and is treated as untrusted data until it passes the equivalence
  check in section 4. A structural change first passes L0 `apply_patch`:
  its `base` must equal the old program digest, and the complete new program
  must validate. Stale or invalid patches leave the original untouched and
  produce no new artifact. Only the accepted new program revision is compiled;
  the old and new digests are recorded separately. The artifact never modifies
  the source program, L0 contract, or any project file.
- **Input validation:** performed twice by design — the generator validates
  the program through `compile_program`; the artifact re-validates the
  supplied inputs object at run time against the embedded input
  declarations, with the same error codes as the reference interpreter.
- **Permitted effects:** L0 operations are pure. The artifact may read exactly
  one inputs file named on the command line and write one JSON result to
  standard output; it may not use network, filesystem writes, dynamic
  evaluation, subprocesses, clocks, or randomness. The future generator must
  use independently reviewed, fixed source templates and encode programs as
  inert data, never interpolated executable text or dynamic evaluation. The
  later runner verifies reviewed generator and template source SHA-256 before
  generation and artifact SHA-256 before execution. Independent acceptance must
  check that they cannot emit clock, randomness, or other forbidden calls;
  their absence is a generator/template property, not a conclusion from
  matching JSON outputs or bubblewrap alone. The trusted runner may use
  scratch space outside the artifact guest namespace; that scratch is not
  an artifact effect.
- **Resource needs:** L0 input and graph bounds apply, plus unmeasured CPython
  overhead. The later profile may provision the 512 MB aggregate memory cap
  used by `tools/check_l0.py`, with preflight and a BLOCKED result if the
  profile cannot be enforced. Actual memory use remains unverified.
- **Failure states:** structured refusal (`ok:false`, stable `error.code`,
  exit 2) for every L0-domain rejection; any other artifact exception is a
  defect surfacing as a non-zero, non-2 exit and counts as an
  equivalence-check failure, never as a silent success.
- **Isolation (later, separately reviewed execution profile):** candidate
  artifacts run only under a profile modeled on `tools/check_l0.py`:
  bubblewrap namespace isolation with cleared environment and no network,
  read-only candidate mount, no writable guest mounts (including `/tmp`),
  `/usr/bin/python3 -I -B -S`, and aggregate resource limits (memory, tasks,
  CPU, runtime) with preflight. Before any artifact execution, a trusted
  write-denial probe in that exact guest namespace must confirm that guest
  writes are refused; inability to establish this blocks the check, with no
  unsandboxed fallback. A separately reviewed restriction must also deny
  process creation after interpreter startup, including by the artifact;
  an in-guest fork/exec negative probe must run under the same post-start
  restriction before candidate execution. A tasks limit alone does not deny
  subprocesses. If the restriction or probe cannot be enforced, report
  BLOCKED. This profile does not claim OS-level denial of clocks or
  randomness; those require the generator/template check above. The
  existing L0 checker is an isolation precedent, not a ready-made profile:
  its writable guest /tmp must not be copied. This proposal does not
  authorize execution; it fixes the boundary for a later reviewed profile.
- **Explicit assumption:** a CPython 3.14.x interpreter at
  `/usr/bin/python3` remains available on the check machine; if it is
  absent, the equivalence check reports BLOCKED rather than substituting
  another interpreter.

## 4. Later interpreter-equivalence acceptance check

A future, separately authorized check uses **41 selected cases**: the 20
fixed L0 acceptance cases in `tools/check_l0.py` at input revision
`dd526aa3e5ad3c165948561f33313e99de432ce4`, plus 21 L1 cases below.
The source at that revision fixes the fixtures and exact input construction
for `patch-atomic`; `list-preserves`, `empty`, `duplicates`, `reversed`,
`distinct`; `composed`; and `wrong-type`, `duplicate-key`, `duplicate-node`,
`missing-reference`, `cycle`, `unknown-operation`, `integer-overflow`,
`stale-patch`, `invalid-replacement`, `large-integer`, `deep-malformed`,
`deep-malformed-patch`, `eager-unreachable-overflow`. Each named observation
checks both the original and patched programs on its fixed `tags` input;
the `composed` case checks the standalone example. Pre-generation `check` or
`patch` refusals test the generator gate and emit no artifact; runtime `run`
refusals compare reference and artifact on identical input bytes.

For L1-01 through L1-02, use one program with `x: int` input, an `int` literal
1, `int.equal(x, 1)`, then `bool.not` as result. For L1-03 through L1-04 and L1-17,
use a one-node `x: int` input program with that node as result. L1-05 and
L1-10 use the analogous `x: string` program; L1-06 and L1-11 use
`x: string_list`. L1-18 uses the same `x: string` program. All other program
and input recipes are fixed here:

| ID | Program and exact input or check | Expected boundary |
| --- | --- | --- |
| L1-01, L1-02 | Boolean program; `{"x":1}`, then `{"x":2}` | `false`, then `true` |
| L1-03, L1-04 | Integer program; `{"x":-9223372036854775808}`, then `{"x":9223372036854775807}` | Both accepted unchanged |
| L1-05 | String program; `x` is `"a"` repeated 4096 times | Accepted unchanged |
| L1-06 | List program; `x` is a list of 256 `"a"` strings | Accepted unchanged |
| L1-07 | One `string_list` literal `[]` and one `list.concat` node referring to it 32 times; `{}` | Empty list, 32-reference limit accepted |
| L1-08 | `n000` is `x: int`; `n001` through `n255` are successive `identity` nodes; result `n255`; `{"x":0}` | 256 nodes accepted; result 0 |
| L1-09 | One integer literal 0; inputs bytes are `{}` followed by 1048574 ASCII spaces | 1048576-byte JSON accepted; result 0 |
| L1-10 | String program; `x` is `"a"` repeated 4097 times | `limit.string`, exit 2 |
| L1-11 | List program; `x` is a list of 257 `"a"` strings | `limit.list`, exit 2 |
| L1-12, L1-13 | `tag_list.json`; `{}`, then `{"tags":[],"extra":0}` | `input.missing`, then `input.unexpected`; exit 2 |
| L1-14 | Generate `composed.json` twice at one generator revision | Identical bytes and SHA-256 |
| L1-15 | Append one newline to a copy of the generated `composed` artifact after hashing | Hash mismatch; refuse before execution |
| L1-16 | Offer the original `tag_list` artifact under the accepted patched program's digest | Revision mismatch; refuse before execution |
| L1-17 | Integer program; input JSON bytes `{"x":true}` | `value.type` refusal, exit 2; Boolean is not an integer |
| L1-18 | String program; exact UTF-8 input JSON bytes `{"x":"` followed by 2049 U+00E9 characters, then `"}` | `limit.string`, exit 2: 4098 UTF-8 bytes in `x` |
| L1-19 | One `int` literal 0 as result; input JSON bytes are `{}` followed by 1048575 ASCII spaces | `limit.json_bytes`, exit 2: 1048577 input bytes |
| L1-20 | Generate from `composed.json` and from a second program with its `nodes` array reversed and every object key order reversed recursively; preserve every other array order | Same L0 program digest and byte-identical artifacts at one generator revision |
| L1-21 | Two `string_list` input nodes, IDs and names `a` and `b`; `joined` is `list.concat` with items [`a`,`b`] and is the result. Input is compact JSON with keys `a`, then `b`, each containing 256 copies of `"a"` | Both inputs valid; 512-item result refused with `limit.list`, exit 2 |

Expected values and stable refusal codes come from the pinned reference
interpreter before any artifact runs. For each executable case, compare the
success envelope's exact key set and values (`schema`, `ok`, `command`,
`program_digest`, `result_type`, `result` with deep JSON value equality) or
the refusal envelope's key set, `error.code`, and path-free string
`error.message` shape; do not require identical message wording. Deep
equality requires the same value and exact parsed type recursively, including
Boolean distinct from integer; Python `==` alone is insufficient. Compare
process exit codes and reject extra output, invalid JSON, or partial results.
The patch cases compare old and new digests, original bytes before and after,
and absence of a new artifact on stale or invalid changes.

The runner binds each case to the reference program digest, generator revision,
recorded artifact SHA-256, and embedded digest. It verifies the artifact hash
and embedded digest against the selected program immediately before isolated
execution; any mismatch or tampering fails without executing the artifact.
The report records these identities, the interpreter version actually invoked,
the enforced sandbox limits, `cases_selected:41`, `cases_run`, failures, skips,
and terminal exit status. Exit 0 requires all 41 selected cases to run and
match, with zero failures and skips; zero selected or run cases, any mismatch,
skip, invalid output, or failed binding yields nonzero status.

An ordinary-language functional comparison and any model or cost claim are
separate later tracks (foundation items #4 and #5) and are not measured or
claimed by this profile.
