# Explicit form5 source-map file interface

Expose the accepted data-only source-map library through a separate CLI using
the accepted bounded file reader and exclusive-create output writer. Require
--form 5, --program-pin and --output. Optionally require --source-sha256 to bind
layout, and select exactly one existing --pointer. Pins must match before any
output is written. Missing, malformed or stale pins and absent pointers refuse.
No node-ID inference, invocation execution, subprocess, native pointer handling,
semantic check or modification of existing transport. Successful output contains
the complete map or its selected location and the same source/programme pins.
A small stdout receipt carries identity, selected count and explicit false
semantic/admission flags. Failures carry one structured error, with no promised
transactionality beyond the existing writer's exclusive-create semantics.

Freeze test obligations before implementation: complete map, selected repeated
literal, matching layout, changed layout with equal programme pin, stale layout,
stale programme, malformed pin, missing pointer, missing explicit form, wrong
form, existing output, symlink input, invalid UTF8 and oversized input. Existing
output and input bytes remain unchanged after refusal. Output is not created on
pre-write refusal. Programme evaluation and native calls remain zero.
