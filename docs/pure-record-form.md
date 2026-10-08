# Pure readable typed programs

A pure computation does not need component, owner, revision or receipt metadata.
The separate record-form/1 envelope describes a supported subset of the existing
typed-record/10 program directly:

```text
bagaev record-form/1;
program {
  entry calc;
  fn calc() -> Int64 = text.bytes("é🙂");
}
```

Its pure result is 6. Conversion produces the exact typed-record/10 JSON program;
it neither invokes the reference nor supplies execution admission.

Records, nominal record lists, variants, functions, entry selection and the
[form7 expression vocabulary](component-record-list-form.md) are available.
A program has one entry declaration. Functions remain pure. Existing limits and
refusals are owned by the actual typed core, including references, type checks,
call cycles, arguments, value bounds and work. This readable subset does not yet
represent every typed-record/10 operation, raw JSON view or optional-field form.
It is separate from L2 probe-forms/1 and does not change component forms.

## Data-only file tool

```console
python3 -B tools/record_text.py decode input.bagaev --output program.json
python3 -B tools/record_text.py encode program.json --output canonical.bagaev
```

Both outputs must be new. The fixed tool accepts decode/encode/inspect, input and
--output, with no profile autodetection or source execution. Inputs are regular
non-symlink files, limited to 1 MiB; JSON rejects duplicate keys and unsupported
numeric/structural input. Exclusive creation preserves existing outputs. Expected
refusals report FORM_*, RECORD_* or TOOL_USAGE and exit2; successful conversion
reports bagaev-record-text/1, output identity, semantic_check:false and
execution_admission:false. A well-formed wrong-type program can be converted.
OS write failures can leave a partial new file and do not count as success.

Use a separately reviewed typed-record/10 reference with an explicit invocation
and arguments for actual checking/evaluation. No durable receiver is required
merely to compute a pure value. This does not create a general native ABI or
claim a compiled backend for the whole readable subset.

## Prepare explicit arguments for execution

```console
python3 -B tools/record_text.py prepare ReindexEntry.bagaev --arguments arguments.json --output invocation.json
```

The arguments file is a JSON array, for example:

```json
[{"id":1,"manual":["family"],"indexed":["old"]},["new","new"]]
```

The output contains exactly `schema: bagaev-typed-record-invocation/10`, the decoded
program and supplied argument data. A separately reviewed reference can consume
it using `run --input invocation.json`. Preparation never launches that reference
or accepts a path to an executable. The result continues to state that semantic
checking and execution admission are false; only prepare adds its output schema.

Both inputs obey the same regular-file, strict JSON and size rules. A non-array
arguments file refuses RECORD_ARGUMENTS, invalid JSON/Unicode refuses RECORD_JSON,
and oversized combined output refuses RECORD_BOUNDS before creation. Missing
--arguments or supplying it to decode/encode refuses TOOL_USAGE. Argument types
and arity remain the typed core's responsibility. Existing files are not replaced.

## Evidence

[Five literal valid programs and one wrong-type program](../examples/probes/pure-record-form/CONTRACT.md)
cover arithmetic, record projection, record-list fold, Unicode bytes and variant
match. All six exact graphs/roundtrips and actual reference observations matched;
three syntax refusals passed. The separate CLI check made eleven calls with
seven refusals and preserved original and existing output bytes. Its initial
existing-output error expectation was corrected to the established RECORD_PATH
mapping, without changing the product or frozen program expectations.

Portable `pure_record_form_checks.py` uses explicit reviewed reference/reader
paths and hashes and a new absolute output directory; `pure_record_cli_checks.py`
needs only a new absolute output directory. These are bounded conformance checks,
not independent reproduction, performance measurement or admission.

A complete application-oriented example is [pure entry reindexing](pure-reindex-entry.md).

Use [pure syntax diagnostics](record-diagnostics.md) for source-position context without execution.

For exact-base function-body changes and helper extraction, see [detached pure drafts](pure-record-drafts.md).

For source pins and a connected edit-to-result example, follow [one complete pure change](pure-change-workflow.md).

Optional integer syntax has an explicit separate [record-form/2](pure-option-form.md); select it deliberately. Form1 and its fixed tools remain unchanged.
