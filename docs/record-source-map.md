# Readable form5 expression source map

`src/bagaev_record_wide_spans.py` exposes `source_map(source)` for explicit
record-form/5 text or UTF-8 bytes. It returns data and never evaluates, compiles,
launches a programme, changes a file or grants execution admission. The existing
codec is unchanged. Import it with the repository's `src` directory on the
Python import path.

The `bagaev-record-source-map/1` result contains:

- `source_sha256`: SHA256 of the exact UTF-8 source bytes, without a prefix;
- `program_pin`: `sha256:` plus the canonical decoded programme digest;
- `locations`: entries sorted by invocation-prefixed programme JSON pointer;
- `semantic_check: false` and `execution_admission: false`.

Each entry has its `program_pointer`, source-graph `operation`, `precision`,
`start_byte`/`end_byte` and start/end line and column. Byte ranges are half-open.
Lines and Unicode-scalar columns start at one. LF starts a new line; CR is counted
as an ordinary scalar. Tabs count as one scalar, not a visual tab width.

## Precision and identity

`exact-expression` is a range returned by a parser expression boundary, including
parentheses when present. `enclosing-expression` explicitly marks a coarser
range: an intermediate node in `1 + 2 + 3`, for example, may use the full chain.
Do not display a coarse range as an exact substring for the intermediate node.
Repeated identical literals retain separate locations. Record field order in
the graph is canonical; ranges still point to their original source order.
Metadata such as JSON field keys and match-arm containers are not expressions.

To join with the [checked native source inspector](native-source-locations.md),
first require exact equality between this map's `program_pin` and that report's
`source_pin`, then join by `program_pointer`. Also bind the displayed source to
`source_sha256`. A changed layout can keep the programme pin while changing the
source hash and ranges. Native node numbers must come from the separately checked
report, not from this library's sorted entry order. Neither report authenticates
a native failure record or licenses a pointer dereference or execution.

The normal form5 decoder must produce exactly the same graph as the mapping
reader. Existing input/token/depth bounds remain. The map additionally refuses
more than 2048 expression entries or more than 1 MiB of serialized result.
Malformed input uses the existing form errors. `SPAN_BOUNDS`, `SPAN_TOKENS` and
`SPAN_GRAPH` indicate mapping limits or an internal agreement failure. No partial
map is returned. Syntax acceptance is not semantic acceptance.

## Evidence

Eight [literal expectations](../examples/probes/wide-source-spans/cases.json)
were frozen before implementation: precedence, associativity, repeated literals,
parentheses, UTF-8 text, reordered record fields, field chains and JSON keys.
Six tests passed with warnings treated as errors, including the accepted full
catalogue, sixteen-item sum, layout identity, malformed inputs and the exact
2048-entry boundary. The initial test harness matched the `j` in `json` when
looking for the standalone argument `j`; whole-identifier matching corrected the
harness without changing the frozen expected fragment or production mapper.

Six fresh data-only calls to the accepted checked native inspector joined all
58 expression pointers at matching programme pins. These cover the existing
failure-location fixtures and call ordering. No programme evaluation, native
kernel invocation, model call or performance measurement was performed here.
The [contract](../examples/probes/wide-source-spans/CONTRACT.md) records the scope.
