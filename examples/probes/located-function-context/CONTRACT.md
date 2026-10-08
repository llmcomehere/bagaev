# Optional layout-bound focused function context

Close the gap between direct-call context and the accepted readable source map:
an explicit --locations flag on record_function.py context --form5 returns
bagaev-function-context/3. Default context/2, extract and replacement stay
byte-identical and unchanged. Other operations/forms with --locations refuse.

The new context keeps the original fragment, direct caller/callee declarations,
scope and false semantic/admission flags. Add source_sha256 for exact raw layout,
program_pin equal to sha256: plus fragment.base, and locations containing exactly
the selected function's expression pointers from the accepted map. These ranges
refer to the original full source, not to the canonical fragment.source text.
That distinction must be explicit in the packet. Coarse precision is preserved.
No native node IDs inferred, no source modification, programme call or new
execution helper. Existing file transport, 1 MiB bound and no-overwrite apply.

Freeze tests before code: unchanged default and explicit no-flag context bytes,
selected function only (not a similarly prefixed function), original-source
UTF8/line coordinates, program pin/fragment base agreement, caller/callee
preservation, multiline layout change preserving programme pin but changing
source hash/locations, invalid name, invalid form/operation flag combination,
existing output and original source unchanged. Test accepted batch_apply context
for a useful multi-call example; no runtime evidence follows from extraction.
