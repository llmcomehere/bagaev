# Bounded native-runtime and source-byte observations

On October 4, 2026, one frozen, serial collection completed 936 observations:
36 case/backend/mode variants, five fresh-process observations and 21 direct-ABI
batches per variant. The four selected workloads were add, call, maximal loop
and exact work boundary. All measured executions retained their fixed result
and input bytes. This is a small experiment on synthetic kernels, not evidence
of general language, application, model or total-cost superiority.

## Method and retained evidence

- [Raw timing rows](../examples/probes/native-runtime-samples.csv) retain every sample.
- [Summary and pre-collection freeze](../examples/probes/native-runtime-summary.json) retain exact identities, sample sizes, ordering, thresholds and limitations.
- [C observer](../examples/comparison/pure/native/observe_batches.c) times only the direct call loop using CLOCK_MONOTONIC. Loop and clock overhead are not subtracted.
- Every variant passed a preflight and a deliberately wrong expected-result control before collection. One preflight call precedes each timed batch; results and unchanged inputs are checked after the batch.
- Fresh-process timing includes launcher startup, input/expected-file I/O and the first verified result. OS caches were not reset, so this is not a cold-disk measurement.
- Linked application and object sizes include metadata. These are full artifacts, not isolated machine-code section sizes.
- Cranelift objects use PIC; C11/LLVM objects and all linked executables use the declared non-PIE profile. The bagaev objects retain canonical-program metadata. This compares the recorded implementations as configured, not isolated optimizer quality under identical relocation/metadata choices.
- The environment was shared Linux x86-64, with no CPU isolation. Observed ranges, not population confidence intervals, are reported. A batch below 1 ms is marked resolution-limited; samples were not increased after viewing results.

## Selected optimized-mode medians

This table shows LLVM/C11 O2 and Cranelift speed. Mode names are declared
settings, not a claim of identical optimization algorithms. See the full summary
for O0/none and Os/speed_and_size and every observed range.

| Case | Backend | Direct call median (ns) | Fresh process median (µs) | Linked bytes | Resolution-limited batch |
| --- | --- | ---: | ---: | ---: | --- |
| K-ADD | c11 | 7.45 | 1059 | 16584 | no |
| K-ADD | llvm | 8.10 | 930 | 16720 | no |
| K-ADD | cranelift | 4.93 | 1176 | 16672 | no |
| K-CALL | c11 | 7.40 | 1157 | 16584 | yes |
| K-CALL | llvm | 6.38 | 1073 | 16720 | yes |
| K-CALL | cranelift | 7.11 | 1383 | 16712 | yes |
| K-LOOP-MAX | c11 | 7099.25 | 1167 | 16584 | no |
| K-LOOP-MAX | llvm | 6415.21 | 1131 | 16720 | no |
| K-LOOP-MAX | cranelift | 2575.88 | 1138 | 16672 | yes |
| K-WORK-EXACT | c11 | 158860.25 | 1254 | 16592 | no |
| K-WORK-EXACT | llvm | 181937.44 | 1284 | 16720 | no |
| K-WORK-EXACT | cranelift | 94824.62 | 1179 | 16672 | yes |

Cranelift had lower observed direct-call medians in several optimized examples,
but none of these optimized-mode comparisons met the complete predeclared
dominance criterion. Ranges overlap and several batches are resolution-limited.
Only the add case in the none/O0 and size/Os pairings met that narrow descriptive
criterion. This does not select an overall backend winner.

## Unavailable or unmeasured terms

An optimized Cranelift compiler-tool build failed with an out-of-memory error
under the retained 2 GiB address-space cap, at both 16 and 256 codegen units.
The functional dev-profile compiler remained available and produced the
already-conformant objects used here. Its compilation latency was not substituted
for an optimized-tool comparison. Dependency acquisition/setup cost, optimized
compiler latency, trustworthy application-memory ranking and aggregate process
memory are therefore not established by this report. The runtime measurements
above concern emitted native applications, not the speed of the compiler tool.

## Exact source bytes

The [separate byte observations](../examples/probes/form-byte-observations.json)
cover all 42 non-edit fixtures in three forms and all 17 specified edit stages
in three forms. The scope and identities were fixed before collection.

| Encoding | Sum of 42 program sources | Value-case sources | Refusal-case sources |
| --- | ---: | ---: | ---: |
| json | 8552 | 6792 | 1760 |
| sexpr | 9892 | 7833 | 2059 |
| familiar | 8176 | 6500 | 1676 |

On this unweighted fixture set, familiar constructors used 4.40% fewer source
bytes than JSON, while S-expressions used 15.67% more. Borrowed arguments were
excluded. Oversized negative witnesses dominate edit-frame totals, so those
totals should not be interpreted as ordinary editing cost. No tokenizer, model
call, encoding-time or total development-cost saving follows from byte counts.

All review was a separate same-maintainer pass, not independent review. Full
production acceptance and the remaining PB0 decisions stay open.
