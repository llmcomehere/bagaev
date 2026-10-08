# Form5 record-list literal boundary correction
Inspection found that form5 inherits the older reader's hard four-element
records.list parse limit despite its separate capacity16 profile. Preserve all
old codecs and correct only the explicit form5 constructor to at most16 syntax
items; declared list capacity remains a separate lowering check. Freeze literal
positive counts0/4/5/16 and negative17/declared-capacity overflow before changing
the reader. Programme graphs, declarations, runtime work and typed/native
semantics remain unchanged. In particular the accepted sixteen-item sum source
must encode/decode to its existing exact graph and still return120/work610 in
a fresh reference call. Existing native results for that same graph are prior
evidence, not new execution. No spans feature is implemented in this slice.
