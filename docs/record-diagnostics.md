# Locate pure readable syntax errors

```console
python3 -B tools/record_diagnose.py input.bagaev --output diagnostic.json
```

The input is a regular non-symlink file under the existing 1 MiB bound. The output
must be new. The fixed tool emits `record-form-diagnostic/1` with the source
SHA-256, `form: record-form/1`, `valid_form`, false semantic/admission flags,
and either no error or an error code, phase and optional span.

Header version and lexical failures identify a token. Parser failures identify
nearby context, not necessarily a uniquely guilty token. Spans are half-open
UTF-8 byte offsets and one-based Unicode-scalar line/column positions. Lowering
failures deliberately have no source span. Invalid encoding and oversized input
are transport failures. The original converter and its refusal behavior are
unchanged. A valid-form result does not imply valid argument or return types.

A successfully written diagnostic returns exit 0 even when syntax is invalid;
inspect `valid_form`. File/usage failures return exit 2 with the existing
RECORD_* or TOOL_USAGE refusal and no promised diagnostic output. Existing
outputs are preserved; failed OS writes may leave a partial new output.

The portable `tests/probes/record_diagnostics_checks.py --output NEW_DIRECTORY`
checks seven frozen complete syntax observations through both API and CLI,
including a semantically wrong but syntactically valid program, version/header,
Unicode lexical and missing-semicolon cases, plus four transport controls.
These are source diagnostics only: no reference executable is launched.
