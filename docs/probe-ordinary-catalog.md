# Direct ordinary Rust catalogue comparison

This direct safe Rust application implements [catalog-application/2](application.md)
without interpreting bagaev source or calling its generated application kernel.
It supplies an ordinary native comparison path for the same frozen workload.
It does not add a language feature or establish a performance winner.

## Boundary and common dependency

[The application source](../examples/probes/ordinary-catalog/catalog.rs) uses owned
Entry, State and Response data, ordinary Vec operations and the seven ordered
validation gates. Complete request shape precedes date validation; transformations
start only after all refusal gates. Revisions, missing dates, numeric ordering,
manual-origin preservation and list/set behavior follow the unchanged contract.
The ID view does not reorder the returned state.

The existing flat-arena JSON transport parser is shared. This is a declared common
dependency, not independent parsing. Application logic does not use typed_record,
the source evaluator or the LLVM catalogue kernel. Serialized input remains
bounded by that parser and the 1 MiB adapter. Malformed/duplicate-key/oversized
transport is separate from an application refusal and produces no application
response. This adapter does not claim all unbounded finite Python inputs.

The function borrows parsed input immutably and returns owned Strings/Vecs.
Encoding returns complete application JSON, with no bagaev work counter or result
wrapper. Equality follows the application contract: object key order irrelevant,
array order and scalar types significant. Different transport/output boundaries
must be reconciled before any timing or memory comparison.

## Portable source and data

- [Main template](../tests/probes/backend/ordinary_catalog_main.rs.in): substitute
  {{TRANSPORT}} with the reviewed transport.rs path and {{CATALOG}} with the
  application path. Compile with Rust edition2021 and warnings denied in an
  admitted bounded environment. Supply one request file. Input owners are dropped
  before encoding; the response owner is dropped before output bytes are written.
- [Data helper](../tests/probes/ordinary_catalog_wire.py): list; request CASE;
  check CASE --output FILE; mutant MUTANT_ID. It uses the existing
  [99-case oracle](../examples/beta/catalog-cases.json), rejects duplicate output
  keys and compares the complete response, preserving Boolean/integer/float
  distinctions. It emits source/data only and never launches code.
- [Mutation data](../examples/probes/ordinary-catalog/mutations.json) fixes 20
  concrete safe source faults, exact source hashes and 44 oracle witnesses.
  A build failure, crash or transport error is not a detected semantic mutation;
  the compiled candidate must return normal JSON that violates the full oracle.
- [Ownership runtime template](../tests/probes/backend/ordinary_catalog_owned.rs.in)
  evaluates each request three times, snapshots immutable parsed input, mutates
  and drops the first output, and checks independent later outputs after input
  destruction. Use the same substitutions as the main template.
- [Compile-only ownership template](../tests/probes/backend/ordinary_catalog_ownership.rs.in):
  use --emit=metadata and one --cfg: immutable_input requires E0596;
  borrowed_not_owned requires E0308; drop_input compiles. Do not execute these
  compile fixtures or count an unrelated compiler error as the expected refusal.

These templates do not grant execution authority, change workflows or add a
background service. Native compilation/execution retain their own admission.

## Finite qualification

The 99 literal cases matched at O0/O2 (198 ordinary native observations), with
60 idempotent reapplications. Eight actual chain steps used six actual predecessor
feeds across both builds. Another 103 inherited typed-catalogue payloads matched;
these overlap the literal corpus and are not 103 new independent cases. The typed
Result payload was compared without dropping application refusal fields or
silently accepting a language failure. Three transport controls produced no
application output.

Twenty safe application faults produced 44 normal incorrect responses on frozen
witnesses. Ownership checks covered 99 cases and 297 evaluations; two exact
compiler refusals and one positive lifetime control matched. All observations
are same-maintainer checks. No bagaev native kernels were newly executed here,
and no time, RSS, allocation or model-cost measurement was collected.

An initial qualification driver guessed the typed refusal tag as Err; the pinned
fixtures use Error. That driver stopped before a full pass, was corrected, and
the complete qualification was repeated. Neither application source nor oracle
expectations changed. Exact-head CI validates documentation, not native execution.

The exact portable packet repeated 99 ordinary calls and 99 ownership cases,
the two exact compiler refusals/one positive control, and all 44 wrong outcomes
from its 20 emitted mutant sources. Four helper controls reject an extra output
field, duplicate output key, nonfinite output and unknown mutant. These are
replays of fixed expectations, not new independent semantic cases.
