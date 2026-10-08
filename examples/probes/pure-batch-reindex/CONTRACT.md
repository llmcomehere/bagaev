# Pure bounded batch reindex

Process a named Entry list of capacity four in input order using existing fold,
records.at and records.push. Each result keeps id and manual sequence exactly,
replacing indexed tags with sorted unique supplied tags. Empty input returns
empty; no persistence/owner/update is performed. The fixed four-iteration fold
guards every access with actual length. Source and arguments stay unchanged.
Five literal complete results and one existing RR_WORK refusal are frozen.
No runtime cap expansion, optimization/performance or general catalogue claim.
