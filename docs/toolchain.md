# L2 local toolchain

This contract covers `bagaev-toolchain/1`, the standard-library-only Linux/CPython
CLI and independent CPython lowering of [L2](l2.md). It does not change L0, L1,
L2 or the [catalog contract](application.md). These are implementation and usage
contracts, not execution evidence. Review source and [execution rules](../AGENTS.md)
before running candidate code. Checking or compiling grants no execution authority.

## Commands and observations

From the repository root, use `python3 -B -m src.bagaev`:

```text
--help
--version
check PROGRAM
run PROGRAM --input INPUT [--artifact ARTIFACT]
patch PROGRAM PATCH --output NEW_PROGRAM
compile PROGRAM --output NEW_ARTIFACT
inspect PROGRAM
diff BEFORE AFTER
```

The supported profile is L2 only. No profile is inferred or silently converted.
The existing `src.bagaev_l0` CLI and `src.bagaev_l1` library remain separate,
unchanged interfaces. All paths are explicit regular-file inputs; stdin is not
a transport. The supported invocation requires `-B` to suppress interpreter
bytecode writes, including loading the CLI module itself. With this invocation,
no command implicitly writes a cache, store, revision or admission. Omitting
`-B` uses CPython's normal bytecode-cache policy and is outside this file-effects
contract.

The six commands emit exactly one JSON line on stdout. Success is
`{"schema":"bagaev-toolchain/1","command":COMMAND,"ok":true,"result":RESULT}`
and exit 0. Expected refusal is
`{"schema":"bagaev-toolchain/1","command":COMMAND,"ok":false,"error":{"code":CODE,"message":TEXT,"location":LOCATION}}`
and exit 2. Invalid invocation uses command `null`. Help/version use ordinary
text and exit 0. Unexpected environment/programming failures are not converted
to language refusals or success: the CLI emits a path-free host-failure message
on stderr and exits 1, with no success/refusal envelope.

| Command | Result fields |
| --- | --- |
| check | `source` (checked program digest), `entry`, `definitions` (count) |
| run | `source`, `engine` (`reference` or `cpython`), `value` (the exact L2 result) |
| patch | `source` (new digest), `base` (original digest), `bytes` (written canonical bytes) |
| compile | `source`, `generator`, `artifact` (digests), `bytes` (written bundle bytes) |
| inspect | `source`, `entry`, `definitions` (sorted list of `{id,pin,params,dependencies}`; dependencies are sorted `{id,pin}`) |
| diff | `before`, `after`, `entry_changed`, `added`, `removed`, `changed` (sorted IDs whose actual definition differs), `pins_changed` (sorted IDs present in both snapshots whose pin differs) |

Diff compares actual structural definitions, including parameter names and order;
it separately reports transitively changed pins and does not fabricate a patch.
Patch returns the transactional L2 result before attempting output creation.
Neither patch nor compile executes the program.

Language refusals retain their `L2_*` code. CLI codes are `TOOL_USAGE`,
`TOOL_INPUT` (unavailable/unsuitable file), `TOOL_TRANSPORT` (bounded argument or
artifact transport), `TOOL_OUTPUT` (existing/unusable output), and
`TOOL_ARTIFACT` (any artifact mismatch). Backend runtime location is
`{"definition":ID,"pin":PIN,"expression":POINTER}` where POINTER is a JSON
Pointer relative to the definition (starting `/body`); object keys use JSON
Pointer escaping. Locations use source identities, never generated line numbers
or host paths. A successful export-boundary failure points to entry `/body`.
Reference/checking/transport refusals have location `null`: the frozen reference
API supplies codes only. Code is the L2 conformance key; location is supplemental.
Messages are short fixed English diagnostics and contain no supplied paths/data.

## Transport and file effects

Programs and patches retain the L2 1,048,576-byte text limit. Argument JSON text
is UTF-8 without BOM or duplicate keys, at most 1,048,576 bytes, at most 128
value levels, at most 65,536 value occurrences, and integer tokens at most
4,096 decimal digits (excluding sign). Floats must be finite. Surrogate escapes
are preserved for L2's reached-operand rules. These are CLI transport bounds;
the L2 and generated `evaluate(argument)` callables retain unbounded borrowed
ingress and never prevalidate/copy/hash it. Artifact text is bounded to
16,777,216 bytes. Oversized source/patch gives `L2_BOUNDS`; oversized argument
or artifact gives `TOOL_TRANSPORT`.

Input open uses nonblocking/no-follow flags, then verifies the opened descriptor
is a regular file before a bounded read. Symlinks, FIFOs, devices, directories
and stdin are refused. Reads capture bytes once; later path changes cannot
substitute artifact bytes. File growth is limited by the bounded read.
Outputs are exclusively created new regular files, never overwrite a file or
symlink, and contain canonical UTF-8 bytes without a trailing newline. A failed
write closes and removes that invocation's partial creation when it still owns
the directory entry; cleanup failure is a host failure. No inputs are mutated.
Concurrent external mutation of files/directories is not an atomic persistence
or durability contract. A later store profile must supply admission/CAS/recovery.

## Independent lowering and artifacts

`src.bagaev_l2_backend.compile_program(program) -> bytes` rechecks L2 and returns
a deterministic canonical JSON bundle with exactly `schema`, `source`,
`generator`, `definitions`, `python`, `artifact`. Schema is
`bagaev-l2-cpython/1`; `definitions` is the complete ID-to-pin map. `source` is
the canonical checked program digest. `generator` hashes the generator and fixed
runtime source bytes with an explicit version label. `artifact` hashes canonical
JSON of all other bundle fields. `python` is self-contained CPython source.

All L2 expressions are lowered to Python control flow. Fixed helpers implement
primitive validation, work accounting and detached export; there is no embedded
reference evaluator, expression interpreter, application intrinsic or fixture
switch. Source IDs, keys and strings enter generated code only as escaped data;
generated identifiers are numeric. Generated evaluation has no reference-library
import, filesystem write, subprocess, network, clock or random operation.
It exposes `evaluate(argument)` and `L2RuntimeError` with `code` and `location`.
Each invocation owns its work counter and explicit definition-call stack.

`verify_artifact(artifact_bytes, expected_program) -> bytes` regenerates from the
expected checked source and compares the entire canonical bundle bytes, then
returns the captured verified Python bytes. CLI artifact run requires PROGRAM,
performs this verification, and executes only those returned bytes. A forged
hash, wrong generator, extra/missing field, changed Python, stale source, altered
formatting or appended newline is refused before execution. User hash fields
are never authority. This is content binding, not trust or runtime admission.

## Clean-checkout walkthrough

After independent source review and authorization in an appropriate execution
environment, no package installation or model account is needed. From a clean
checkout, choose fresh output names (these commands deliberately refuse reuse):

```sh
python3 -B -m src.bagaev --help
python3 -B -m src.bagaev --version
python3 -B -m src.bagaev check examples/l2/catalog.json
python3 -B -m src.bagaev inspect examples/l2/catalog.json
python3 -B -m src.bagaev run examples/l2/catalog.json --input examples/l2/catalog-input.json
python3 -B -m src.bagaev patch examples/l2/catalog.json examples/l2/catalog-01.patch --output catalog-a1.json
python3 -B -m src.bagaev patch catalog-a1.json examples/l2/catalog-12.patch --output catalog-a2.json
python3 -B -m src.bagaev patch catalog-a2.json examples/l2/catalog-23.patch --output catalog-a3.json
python3 -B -m src.bagaev diff examples/l2/catalog.json catalog-a3.json
python3 -B -m src.bagaev compile catalog-a3.json --output catalog-a3.cpython.json
python3 -B -m src.bagaev run catalog-a3.json --input examples/l2/catalog-input.json --artifact catalog-a3.cpython.json
```

The input selects revision 0 with empty entries; both runs specify
`{"kind":"success","state":{"entries":[]},"entry_ids":[]}`. To observe
refusal, apply the 01 patch again to A1 (`L2_STALE`), or run the A3 artifact
against A0 (`TOOL_ARTIFACT`). The commands illustrate behavior; they do not
claim a completed run. [Tests](../tests/test_toolchain.py) cover bounded parity,
transport/output effects and the walkthrough. Current acceptance belongs to
[README](../README.md#what-exists-today) and [Issue #16](https://github.com/llmcomehere/bagaev/issues/16).
