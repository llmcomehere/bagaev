# Explicit form6 semantic diagnostic locations

The default `record_check_location.py` path remains form5 with a retained
source-check/11 refusal. Select `--form 6` for authored form6 and a bound
source-check/12 refusal. The library equivalent is `locate_form6`.

The explicit path returns `bagaev-record-check-location/2`. It requires the same
four lowercase SHA-256 pins as the default: raw authored source, canonical
decoded program, raw checked input and raw retained result. Profiles are not
auto-detected or silently mixed. Invalid profile values fail as TOOL_USAGE before
reading input files. See [the base diagnostic contract](record-check-location.md)
for limits, unmapped locations, precision and exclusive-output semantics.

For example, `json.bool_or(x, 0)` in a Bool-returning function is syntactically
representable but has an invalid fallback type. The supplied /12 RR_TYPE pointer
`/functions/main/body/2` maps to the literal zero. Mapping retained data does not
check types again, authenticate a result or admit execution: all three assurance
flags remain false.

Three new bounded test methods and the unchanged eight default methods passed
after separate review. They cover the retained real /12 refusal, exact expression
precision, cross-profile rejection, four pins, CRLF coordinates, unsupported CLI
selection and preservation of existing output.

A separate-process decode → source-only /12 check → location handoff also passed.
It made one checker call and no submitted-source evaluations. Old and new default
CLI output bytes matched for one retained form5 refusal; this is selected-case
compatibility evidence, not a universal equivalence claim. The retained /12
fixture is [type-refusal12.json](../examples/probes/record-check-location/type-refusal12.json).
