# Pure record diagnostic contract

Provide a separate data-only record-form/1 syntax diagnostic with exact source
SHA256 and half-open UTF-8 byte spans plus one-based Unicode-scalar line/column.
Version and lexical errors identify a token. Parser errors identify context,
not unique blame. Lowering errors have no invented span. Preserve the original
codec's refusal and bounds, and never claim semantic validity or admission.
Expose a standalone regular-file CLI writing an exclusive JSON output.
