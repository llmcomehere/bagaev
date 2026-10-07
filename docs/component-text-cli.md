# Readable component files: data-only conversion

The explicit Linux/CPython tool converts the existing component-form/2 notation
and its component-source/2 JSON representation. It does not check types, run an
application, select an executable, access a Store or grant admission.

After source review and selection of an authorized local execution profile:

```console
python3 -B tools/component_text.py decode examples/probes/component-outcomes/form/StockOutcome.bagaev --output stock-source.json
python3 -B tools/component_text.py encode stock-source.json --output stock-canonical.bagaev
```

Both output files must be new. The first contains compact source JSON, the second
canonical readable notation. The stdout observation is metadata, not a source
file. It uses bagaev-component-text/1, reports output bytes and SHA-256, and
explicitly returns semantic_check:false and execution_admission:false.
Continue with the separately configured [typed source/policy checker](probe-component-outcomes.md)
when semantic checking is needed. A syntactically convertible component may
still have invalid types or references.

The tool has only decode and encode, a positional input and required --output.
The optional --form selector is 2 by default; explicit --form 3 chooses the
[arithmetic/local representation](component-arithmetic-form.md). Neither mode
autodetects or upgrades another form. Both produce component-source/2 data.
Inputs and outputs are bounded to 1 MiB. Inputs must be regular non-symlink files.
JSON input rejects duplicate keys, floating/nonfinite numbers, out-of-Int64
integers and excessive structural nesting. Existing codec version/syntax/profile
refusals are preserved. Old component/1 is not silently upgraded.

Conversion completes before output creation. Exclusive creation preserves an
existing file, including when input and output name the same file. Expected
refusals produce one JSON observation with ok:false/error.code and exit 2;
successful conversion exits 0. Original FORM_* errors remain visible. Transport
codes are TOOL_USAGE, COMPONENT_PATH, COMPONENT_IO, COMPONENT_BOUNDS and
COMPONENT_JSON. OS failures while writing may leave a partial new file; no
successful result is claimed in that case. Source/output parents are trusted
local filesystem inputs; hostile concurrent filesystem mutation is outside
this bounded profile. No settings or permissions are changed.

```console
python3 -B tests/probes/component_text_cli_checks.py --output "$PWD/component-text-checks"
```

The portable check uses the pre-existing frozen form cases and exact compatibility
bytes for encoding. It makes 32 CLI calls with 27 expected refusals, preserves input
and existing output bytes, and invokes no semantic checker or application.
Its two boundary observations accepted a valid 1 MiB input and refused
canonical-output expansion beyond 1 MiB before creating output. These are transport
checks, not new language semantics or execution acceptance.
