# Inert readable formatting for form4

Format tokens outside string literals using bounded indentation and line breaks
at declarations, braces and expression control words. Never rewrite strings,
identifiers, literals or token order. Require exact decoded graph identity before
returning. The output is canonical for the formatting algorithm and idempotent.
Only form4 is selected; old versions and original source remain unchanged.
Output is <=1MiB and file output is exclusive. No execution or admission.
Freeze small literal formatting/identity cases including punctuation inside
strings, Unicode, nested record and if/let expressions. Use full accepted catalogue
for graph preservation and idempotence, not a new semantic or runtime run.
