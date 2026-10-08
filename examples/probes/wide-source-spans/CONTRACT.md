# Readable form5 source map, data-only revision 1

Scope: map decoded programme expression JSON pointers to source ranges, without
changing form5 parsing, lowering, formatting, runtime or execution admission.
Pointers are invocation-prefixed /program/functions/NAME/body/... and can be
joined with the separately checked native location report only after verifying
its programme pin against this map. A raw source SHA256 binds the exact layout.

Ranges use half-open UTF-8 byte offsets and one-based line/Unicode-scalar column
positions. LF starts a new line; CR is an ordinary scalar for column counting.
Whitespace outside the expression is excluded. Parentheses are included when
returned as the expression by the grammar. Each parser-return expression has
precision exact-expression. Intermediate nodes created inside an operator chain
or field chain without their own parser return use the nearest containing
returned expression and precision enclosing-expression. This is a documented
coarse range, never a claim that the substring is that intermediate expression.

Every lowered expression gets one entry, sorted by programme JSON pointer.
Metadata strings such as field names and match-arm containers are not nodes.
Repeated equal literals at different positions must retain different ranges.
Record fields map in canonical graph order but retain their original source
positions. The decoded graph must equal unmodified form5.decode(source).

Limits: unchanged input/token/depth limits; at most 2048 expression entries;
at most 1 MiB serialized output. This is a Python data library, no process
launch, file transport, model calls or native code execution. Output explicitly
states semantic_check=false and execution_admission=false. Syntax errors keep
existing form errors; new bounds/identity failures are explicit. No partial map.

Frozen expected source fragments and pointers are recorded before implementation.
Checks also cover graph preservation for the accepted full catalogue and the
sixteen-item sum. No runtime results or performance claim arise from this map.
