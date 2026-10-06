# Equal-output failure-path allocation lifecycle

Frozen before implementation, 2026-10-06 15:09 UTC. Extend the accepted equal-output wrapper's lifecycle coverage, without changing application logic, native admission, storage sizes or existing timing/allocation observations.

Five raw requests are literal boundary failures: empty bytes; opening object brace; truncated object member `{"revision":`; `null trailing`; and 1048577 ASCII spaces exceeding the wrapper's byte bound. They must return Err with a nonempty owned diagnostic in all three modes. Exact diagnostic wording is intentionally not part of this contract. These are malformed or oversized bytes, not valid application refusals.

Each mode uses one Session and one unchanged System counter. Prepare all input bytes and stack observer slots before baseline. Run the prior REV-3 success first, then three cycles through the five failures; after each failure run that identical success again. Retain all sixteen successful output buffers. Each error must leave only its diagnostic String allocated above its pre-call live baseline; dropping the diagnostic restores that baseline. Each success adds exactly its output Vec capacity. Compare complete canonical bytes and input immutability throughout.

Drop Session while sixteen outputs remain retained. Verify all outputs again; live bytes must equal the pre-Session baseline plus their total capacities. Drop outputs and recover the pre-Session baseline. This is 15 error returns and16 success returns per mode, 93 total attempts. First use and every failure remain in the record. No timers or phase attribution on early-return paths, no RSS or universal leak-freedom claim.

A wrong expected success byte must be detected before the success receipt. A normal code control that keeps one extra Vec allocation live across the error restoration assertion must be detected; it may not bypass or alter the allocator. Execute only own reviewed exact kernel and existing bounded serial profile. No new permissions or external dependency is required for these local checks. PR82 contains the preceding allocation study.
