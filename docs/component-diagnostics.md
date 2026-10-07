# Optional source diagnostic context

The separate component-form/3 diagnostic API helps locate a refused readable
source without changing the existing codec or converter. It never evaluates a
component, invokes a semantic checker or grants execution admission.

After review and selection of an authorized local profile:

```console
python3 -B tools/component_diagnose.py examples/probes/component-arithmetic/StockAdjustment.bagaev
```

The command reads one bounded regular non-symlink file and prints a
component-form-diagnostic/1 JSON observation. valid_form only describes the
readable representation. semantic_check and execution_admission are always false.
A valid form exits 0; a refusal exits 2. No source text or local path is echoed.

## Read a span correctly

- Header version and lexical spans identify the version token or rejected
  character/token.
- Parsing spans are labelled context: they cover the previous consumed token
  through the current lookahead, or EOF. They are nearby parser context, not a
  claim that exactly one highlighted token caused the error.
- Lowering-reference errors and locations unavailable before parsing have null
  spans. The tool does not invent a source location for a semantic-core failure.

Byte offsets are zero-based and half-open. Line and column are one-based;
columns count Unicode codepoints, including one position per tab. Lines split
at LF. The bounded raw input hash binds a span to the exact input; locations require
valid UTF-8. The hash is
null when input bytes are unavailable or over the bound.

The diagnostic API reuses the actual form/3 parser. Its lexical pass uses the
same token pattern and limits. Original refusal codes are preserved, including
encoding-before-size ordering; oversized encoding is checked without allocating
a complete decoded copy. File transport may refuse earlier with the existing
COMPONENT_* or TOOL_USAGE codes. Neither result establishes type correctness.

The [frozen fixtures](../examples/probes/component-diagnostics/manifest.json)
include 15 exact observations, with non-ASCII offsets, parser lookahead, EOF,
literal overflow, unavailable lowering spans and token bounds. Two supplemental
oversized-encoding cases retain the original refusal priority. The portable
component_diagnostic_checks.py driver also exercises the file command and
transport refusals. Original source and converter bytes remain unchanged.

## Explicit match-form diagnostics

The command's default remains form 3. Explicit `--form 4` selects the fixed
bagaev_component_match_diagnostics API for match-bearing component-form/4.
It returns the same diagnostic schema with form:component-form/4. There is no
header autodetection and the form/3 API remains unchanged.

Fifteen earlier cases were adapted only for the version header and source hash.
Five match-specific observations cover valid matching, missing colon/binder,
duplicate alternatives and an incomplete but syntactically valid match. The
last case still requires the real core checker. All twenty observations passed,
along with the original fifteen default-form cases and encoding/transport checks.
One initial expected binder span selected the preceding arm's identical token
sequence. Its coordinate was corrected to the intended Propose arm; the original
failed expectation is retained in development evidence. No product behavior or
acceptance scope was changed to pass that case.

The portable component_match_diagnostic_checks.py driver records these bounded
observations. They do not establish semantic conformance, execution admission,
independent reproduction or an efficiency result.
