# Readable counted fold

Explicit `component-form/6` extends the readable text/list form with the existing
bounded typed-record/10 loop. It produces unchanged component-source/2.

```text
fold (64, 0) with (index, total) in
  if index < list.len(tags)
  then total + text.bytes(list.at(tags, index))
  else total
```

COUNT is a literal from 0 through 1024. The initial value is evaluated once;
the body sees index 0 through COUNT-1 and the previous accumulator. Zero returns
the initial value, but the body still must typecheck. Both binders must be fresh;
the core checks scope and the invariant accumulator type. Integer overflow and
work limits are unchanged. This is not a dynamic loop or a new runtime operator.

The example totals bytes including duplicate entries. Its lazy guard prevents
out-of-range list access. It does not modify the accepted TagBox source or make
its append-before-dedup path total for all admitted states.

Use `python tools/component_text.py decode INPUT --form 6 --output OUTPUT`.
Encoding uses the same explicit selector. Default form2 and forms3–5 are
unchanged. The existing diagnostic, edit and location APIs remain version-bound.
Conversion is data-only and does not supply semantic admission or execution.

The [contract and frozen cases](../examples/probes/component-fold/CONTRACT.md)
cover five exact graphs and values, including zero, 1024 and a Unicode byte
budget, plus four syntax refusals. Portable checks are
`tests/probes/component_fold_checks.py --output NEW_ABSOLUTE_DIRECTORY` and
`component_fold_core_checks.py` with the existing explicit reader/reference
hash-pinned host arguments. Runtime observations are selected conformance
checks, not measurement of performance, model usefulness or adoption.

The new form reserves `fold` and `with`; earlier form readers retain their
original identifier rules. Supplemental checks cover four core refusals,
fourteen existing form5 graphs, version gates and six file-CLI operations.
