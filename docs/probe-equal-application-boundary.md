# Equal application-output call boundary

This compares three already qualified catalogue paths at one explicit boundary:
owned raw request JSON to identical complete canonical application JSON bytes.
The paths are [ordinary direct Rust](probe-ordinary-catalog.md), prepared /10
reference evaluation and prepared /10 native evaluation with retained scratch.
It is a finite call-only comparison, not a kernel-only or full lifecycle claim.

## Projection and calling contract

[Native projection](../examples/probes/ordinary-catalog/native_projection.rs)
strictly decodes BCMPRES3 against the exact catalogue graph and supplied binding,
then copies every application field into owned Response data. [Reference projection](../examples/probes/ordinary-catalog/reference_projection.rs)
checks exact /10 result metadata, Result variant and record/value shapes. It
refuses language failures instead of silently treating them as application
refusals. Both preserve order, duplicates, optional date0 and refusal fields;
neither sorts, repairs or normalizes application data. Both use the ordinary
encoder for identical output bytes. Detached JSON has no source identity, and
matching binary binding is not truthful execution or permission evidence.
A well-formed forged reference result is intentionally accepted as data only.

[The call boundary](../examples/probes/ordinary-catalog/call_boundary.rs) retains
one admitted source handle for reference/native and one fixed native scratch
allocation. It checks the exact canonical catalogue source at preparation.
Raw wrapping/parsing, evaluation, output checking, projection/copy/encoding and
output ownership are in each call. Its unsafe native call still requires the
separately admitted exact linked kernel, valid disjoint storage, immutable input,
no retained pointers and no unwinding. The source digest does not grant admission.
Ordinary application logic shares the parser/encoder, not the language evaluator.

## Reproduction surfaces

[The data helper](../tests/probes/catalog_equal_wire.py) supports list, request
CASE, expected CASE, native-wire CASE, reference-wire CASE, and check CASE
--output FILE. It emits prior data or checks the exact selected canonical byte
surface, without invoking compilers or programs. Extra whitespace may preserve
application-value semantics yet fail this deliberately fixed byte boundary.

[The driver template](../tests/probes/backend/catalog_equal_driver.rs.in) requires
{{BACKEND}}, {{CATALOG_DIR}} and {{SOURCE}} substitutions. Link only the admitted
exact O2 catalogue kernel and compile its Rust caller at O2. Arguments are mode
ordinary|reference|native, action qualify|measure, request file, expected file.
Qualify invokes the same checked call used by timed loops but records no timing.
Measure performs8checked warmups then512checked calls. All compiler/native use
requires separate bounded admission; no workflow or service is enabled here.

[The frozen plan](../examples/probes/ordinary-catalog/equal-plan.json) fixes four
previous study cases,12balanced blocks and the rotation schedule. Preparation,
scratch allocation, process/file I/O and final report are outside the interval.
Request/output black_box, complete expected-byte checking and output destruction
are included. No answer cache, dropped outputs, outlier deletion or post-observation
batch tuning is allowed. A batch below1ms is retained but ineligible for ratios.

## Qualification before collection

Each output projection matched103prior captures at O0/O2. Native projection had
seven exact wire/shape refusals and a normal wrong result when Some0 became None.
Reference projection had14exact refusals plus the explicit forged-data limitation.
Actual call adapters then matched618complete byte observations:103cases across
three paths and two caller builds; the native kernel was O2 in both caller builds.
Twelve additional chain calls used nine actual predecessor feeds, with a fresh
session per step. Retained-session reuse was separately checked by103-case batches
and success/error/success sequences. No claim merges those two lifetime scenarios.
The eventual O2 collector passed309qualification calls and12wrong-expected controls
before its measure action was used.

## Observed call-only intervals

The [complete raw rows](../examples/probes/ordinary-catalog/equal-results.json)
record144batches,73,728timed calls and1,152warmups on October6,2026. All complete
outputs matched; no rows were discarded. Units below are microseconds per call,
median followed by observed min–max across12batches.

| Case | Ordinary Rust | Prepared reference | Prepared native |
| --- | ---: | ---: | ---: |
| REQUEST-TYPE | 0.142 (0.139–0.214)* | 6.493 (6.177–7.448) | 1.467 (1.404–1.667)* |
| EMPTY-0 | 2.558 (2.443–3.387) | 21.009 (20.487–50.329) | 5.194 (4.954–5.776) |
| REV-0 | 12.792 (12.584–14.713) | 225.120 (212.901–241.732) | 27.538 (26.449–46.786) |
| REV-3 | 14.224 (13.815–16.123) | 224.923 (215.823–339.471) | 27.983 (26.027–43.461) |

*Every ordinary/native REQUEST-TYPE batch was below the predeclared1ms floor;
raw values remain visible, but no ratio conclusion is drawn for that case.

In the three eligible cases, ordinary Rust was faster than the prepared native
path: native/ordinary median factors were2.03,2.15,1.97. Native was faster than
the prepared reference path by median factors4.05,8.17,8.04. Observed
ordinary/native ranges did not overlap in these three cases, which is not a
statistical-significance or universal-speed claim. All high rows remain, with
no invented explanation for variability.

Native retains3,670,016bytes of Text/Value descriptors before calls; that is not
total memory or RSS, nor a free lifecycle resource. Source preparation remains
an excluded, unmeasured upfront cost in this study. Shared dependencies, fixed
warm workload, same-maintainer checks and no CPU-isolation guarantee limit the
inference. This does not prove model-cost savings, production readiness or
language-wide superiority. Exact-head CI checks documentation, not native timing.

A separate [allocation lifecycle study](probe-equal-allocation.md) reports preparation, per-call peaks and stage counts without attributing timing differences to them.
