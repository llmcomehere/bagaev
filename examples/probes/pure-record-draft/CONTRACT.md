# Detached pure-program function draft

Data-only API consumes two readable record-form/1 sources and independently
supplied exact canonical typed-program SHA256 base/target pins. Decode both,
require exact base and target, unchanged schema/records/lists/variants/entry,
no removed functions, and unchanged parameters/result types for existing
functions. Allow added helper functions and replaced bodies; reject no-op.
Return detached deep-owned candidate, sorted add/replace delta and false
semantic_check/execution_admission. No storage, evaluator, receipt or automatic
application. Exact base is a stale-edit guard, not authentication.

Freeze successful helper extraction and function-body replacement, stale base,
wrong target, no-op, changed entry/type/signature and removal refusals. An
incorrect but structurally compatible body must still be a draft; a separately
selected reference/expected-result test catches its business error.
