# Locate a retained failure in readable source

`tools/record_failure_location.py` joins an existing scalar capture envelope
to record-form/5 source. It does not run the program. Supply explicit canonical
program and positional-argument SHA256 pins plus the exact raw source SHA256:

```sh
python tools/record_failure_location.py source.bagaev capture.json --form 5 \
  --program-sha256 PROGRAM_SHA --arguments-sha256 ARGUMENTS_SHA \
  --source-sha256 SOURCE_SHA --output new-location.json
```

All pins are 64 lowercase hexadecimal characters without a prefix. The capture
has exactly `program_sha256`, `arguments_sha256`, and `result`, as in the
[capture comparator](record-work-walkthrough.md). This first slice accepts its
four typed-record-result/11 failure families: integer overflow, list index,
work limit and record-list capacity. Successful or other result types refuse.

The command validates the supplied envelope and identities, decodes the source,
checks its canonical program identity and exact layout, and selects the failure
JSON pointer in the regenerated [source map](record-source-map.md). It never
searches by expression text, so repeated identical expressions stay distinct.
Changed comments or layout require a new raw source pin even if the graph is
unchanged. A failure pointer without a mapped expression refuses.

The output preserves the original failure, source range, exact/enclosing
precision, program/argument/raw-source/canonical-capture/result hashes, and an
excerpt of at most 256 Unicode scalars. Full half-open byte ranges remain intact
when `excerpt_truncated` is true. Line and column rules are those of the source
map; an enclosing expression is not relabeled as exact. The CLI additionally
records the raw capture-file hash, distinct from the canonical capture hash.

These are consistency checks on supplied data. They do not authenticate a run,
prove that a stated failure can occur at that operation, validate argument types,
or establish source semantics. `semantic_check`, `capture_authentication` and
`execution_admission` are always false. No evaluator, compiler or subprocess is
invoked. This is not a general static or native diagnostic system.

The pure API is `bagaev_record_failure_location.locate_failure(source, capture,
program_sha256=..., arguments_sha256=..., source_sha256=...)`. The file command
reuses bounded regular-file reads, strict JSON and exclusive output creation.
Existing output is never replaced. Validation failures occur before output
creation; device failures during writing retain the existing writer's limits.

Refusals preserve `CAPTURE_*` and source-form errors. `DIAGNOSTIC_STATUS` rejects
success; `DIAGNOSTIC_PROGRAM`, `DIAGNOSTIC_LAYOUT`, and `DIAGNOSTIC_POINTER`
identify graph, layout, and selection mismatches. CLI refusals print a receipt
with `ok: false` and exit2. Successful output prints its byte count and SHA256.

The tests use synthetic retained-data fixtures, not new runtime observations.
They cover the four accepted failure labels, repeated expressions, Unicode,
coarse ranges, bounded excerpts, stale pins, missing pointers and the actual
CLI main path with file preservation. Passing these tests would not establish
runtime or model benefit.

## Try a retained overflow example

From the repository root, choose a new output path:

```sh
python tools/record_failure_location.py \
  examples/probes/record-branch-edit/Before.bagaev \
  examples/probes/record-failure-location/overflow-capture.json --form 5 \
  --program-sha256 790c5e3bc358c16e9f831ce79dfa82d0f8013b469a059413fd6079c0e9e8f314 \
  --arguments-sha256 c3f7c8546d7d1d31d48314475042deacca64377481791bd7d983514abebf5b07 \
  --source-sha256 44aa09a9c7f6d15e6f50aee101a77f666f0bb38f1fa65eda5818bb9d7f103608 \
  --output overflow-location.json
```

The selected expression is `x + 1`, exact-expression, bytes104..109, line1
columns105..110. The retained error is `RR_OVERFLOW` at work5 for positional
arguments `[9223372036854775807,true]`. The sample capture is byte-identical
to the existing capture-comparison overflow `before_file` fixture. Its envelope
was matched in the earlier reference observations described in the
[branch-edit walkthrough](record-work-walkthrough.md#equal-cost-can-hide-a-changed-branch).
This command only reuses that retained data through the new diagnostic path;
it does not reproduce or authenticate the historical run. A separate CLI-main
test pins the sample bytes and asserts the literal source range above.
