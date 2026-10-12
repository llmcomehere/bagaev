# Authored contextual expression layout, pure form6 library

`bagaev_record_json_bool_authored.export_authored` accepts the original source,
an independently supplied focused draft, a replacement fragment, and mandatory
base, target and exact original UTF-8 source hashes. It returns bytes only.

The existing canonical-body exporter first validates the complete draft. The
fragment is then rebuilt using parameter names from the pinned base, without
copying helper bodies, and must reproduce that exact draft. An occurrence-aware
source map selects its expression, preserving internal comments and named
argument spelling/order. Every byte outside the old expression is retained.
The final complete source is decoded and checked against the exact target graph
under the existing source-byte bound. Contradictory fragments refuse even when
they describe another valid change.

This explicit library does not change canonical exports, CLI selectors or
historical discovery snapshots. No file writes, interpreter, compiler or model
calls occur. Draft consistency is not semantic equivalence or execution admission.

Four tests carry the previously frozen literal positive and negative cases:
Unicode/CRLF and misleading comment boundaries, exact authored expression bytes,
unchanged helper, base/target/source pins, valid contradictory change, no-op,
signature/scope changes and duplicate named arguments. These are finite data
checks, not general runtime correctness or performance evidence.
