# Separate bounded pure record profile 11

The explicit `bagaev-typed-record/11` reference supports named record lists with
capacity 0–16. Earlier profiles 1–10 retain capacity 0–4. The new entrypoint is
`record_wide_main.rs`, using `typed_record::process_v11`; it accepts invocation/11
and returns result/11. It does not auto-detect older schemas.

All other existing limits remain: eight named types, expanded shape budget 4096,
32 functions, 2048 nodes, bounded recursion/work/transport and primitive values.
A capacity 16 declaration can still be refused when its expanded nested shape
exceeds 4096 units. Length, access and immutable append use the declared capacity;
appending to a full list refuses RR_RECORD_LIST_ITEMS with no partial result.
This is a separately versioned pure reference profile, not an expanded native ABI,
component-owned state, durable catalogue or production runtime.

## Readable source

Explicit record-form/5 selects this new schema and allows capacities up to 16:

```bagaev
bagaev record-form/5;
program {
  record Item { n: Int64 };
  list Items of Item capacity 16;
  entry main;
  fn main(xs: Items) -> Int64 =
    fold (16, 0) with (i, sum) in
      sum + record.field(records.at(xs, i), "n");
}
```

This particular function requires 16 actual elements to avoid an index refusal.
For values 0 through 15 it returns 120. For variable lengths, guard each access by
records.len as in earlier batch examples. Choose `record_text.py ... --form 5`
explicitly for decode/encode/prepare/inspect. Preparation writes invocation/11;
it still launches no evaluator. Old forms and fixed form1/4 diagnostics/drafts
remain unchanged and do not silently accept form5.

## Build and evidence boundary

Compile the reviewed `examples/probes/backend/rust/record_wide_main.rs` using a
separately approved local build profile (Rust edition2021, warnings denied).
No toolchain installation, environment authority or execution permission is
provided by this document. Use an explicitly reviewed/hash-identified executable
with the portable `record_wide_checks.py --reference PATH --reference-sha256 HASH
--legacy PATH --legacy-sha256 HASH --output NEW_DIRECTORY` under your execution
profile. The legacy executable must be the profile 10 reference.

Seven new literal cases cover 16-element length/sum/push, full append refusal,
capacity 17, 17 arguments and expansion-budget refusal. These and 99 unchanged
catalogue responses passed through profile 11, plus an old-profile capacity
refusal: 107 reference calls. A readable sum invocation returned 120. The freshly
rebuilt old profile 10 matched its previous executable byte-for-byte on all 99
catalogue result wires, including work/status/refusal fields (198 calls).
These are conformance/regression observations, not performance measurements.

The old catalogue application contract itself still allows four entries. This
profile enables larger pure functions; it does not rewrite that contract or its
frozen 99-case oracle. Native exporters, adapters and execution controls are
unchanged. Independent reproduction and broader acceptance remain open.
