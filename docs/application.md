# Synthetic catalog application contract

Contract: `catalog-application/2`. Oracle: `catalog-cases/2.0.0`.
This application contract does not change frozen P0, L0 or L1.
These are application requirements, not implemented language features
or evidence of model, cost, performance or adoption benefit. The language remains
the product; the later ordinary Python reference is a comparison tool.

## One workload and four selected behaviors

The workload refreshes a small synthetic metadata catalog: optionally replace
one entry's automatically indexed tags, then return the catalog and an ordered
view of its entry IDs. The same state shape, operation and callable serve all
four behavior revisions. Revision selection is explicit, never inferred from
data. The revisions are cumulative:

| behavior_revision | Tag semantics | Reindexing selected entry | Missing dates |
| --- | --- | --- | --- |
| 0 (baseline) | Ordered lists; duplicates matter. | Replace indexed tags; clear manual tags. | Before dated entries. |
| 1 | Canonical sets in both tag origins. | Same clearing behavior as 0. | Same as 0. |
| 2 | Same as 1. | Preserve manual tags; reject a conflicting indexed tag. | Same as 1. |
| 3 | Same as 2. | Same as 2. | After dated entries. |

Clearing manual tags in 0/1 is the deliberately specified predecessor behavior.
Each later revision changes only its indicated obligation. No new user action,
state migration or provenance guess is needed to select the next behavior.
Every successful output state is valid input to every revision. Selecting an
older behavior does not recover duplicates/order or manual tags already lost
by an earlier transformation. Keeping snapshots is the caller's responsibility.

## Callable boundary and types

The later reference exports `evaluate(request) -> response` from
`src/catalog_reference.py`. It accepts one finite JSON data value, represented
by ordinary Python dict/list/str/int/float/bool/None values. Object keys are
strings; floats are finite. Cycles, custom objects, tuples, NaN and infinity
are outside this value-level interface. JSON text parsing, duplicate serialized
keys, CLI, persistence, network and LLM calls are outside this contract.

A valid request has exactly these keys:

- `interface`: exactly `"catalog-application/2"`.
- `behavior_revision`: integer 0, 1, 2 or 3.
- `state`: exactly `{"entries": [Entry, ...]}`.
- `reindex`: null, or exactly `{"entry_id": Identifier, "tags": [Tag, ...]}`.

An Entry has exactly `id`, `title`, `manual_tags`, `indexed_tags`, and optional
`date`. Every required field must be present; every unknown field is rejected,
at every object level. The entries, manual_tags, indexed_tags and reindex.tags
arrays contain 0 through 4 elements, independently.
Entry IDs and tags are 1 through 8 ASCII bytes matching
`[a-z][a-z0-9-]{0,7}`; comparison is byte-for-byte. Titles are 1 through 16
printable ASCII bytes (U+0020 through U+007E). No normalization or case folding
is performed.

A present date is an integer from 0 through 31: an ordinal day in a synthetic
32-day timeline. Day 0 is a known date, not missing. This deliberately avoids
calendar/timezone parsing: only equality, order and missingness are needed for
this workload. An absent key is the sole missing-date representation; null,
strings, booleans, fractional numbers, negative numbers and values above 31
are invalid dates. Everywhere in this contract Boolean values and floats,
including 1.0, are not integers.

Entries must be unique and strictly increasing by ID. Input tag arrays are
lists in every revision; unsorted/repeated tags are valid. A tag may occur
repeatedly within one origin but must not occur in both stored origins of the
same entry. The same tag may occur in different entries. The list input
representation permits replay across revisions; revisions 1–3 interpret each
origin as a set and return its unique members in ascending ASCII order. This
normalization applies to every entry, even when reindex is null or targets
another entry. There is no persisted data revision counter or overflow rule:
`behavior_revision` selects semantics, not mutable-state history.

## Transformation and exact responses

After complete validation, construct a separate result state from the input.
If reindex is present, locate its entry by exact ID:

- In revisions 0/1, set that entry's manual_tags to [] and replace indexed_tags
  with the supplied tags. A supplied tag formerly manual is allowed because
  the old manual origin is explicitly removed.
- In revisions 2/3, retain manual_tags and replace only indexed_tags. If any
  supplied tag is manual in that entry, refuse with origin-collision. Do not
  silently drop the conflicting tag, merge origins, or retain old indexed tags.

Then, for revisions 1–3, canonicalize both tag arrays in every entry. Revision
0 preserves the input order and multiplicity of arrays not explicitly replaced.
Reindexing does not change other fields or other entries except the canonical
presentation required by revision 1. In revisions 2/3, preservation of manual
tags means identical membership; noncanonical input presentation is normalized.
Repeating a successful transformation with its returned state and the same
reindex value is idempotent for that selected behavior.

The result state's entries remain in ID order. The separate entry_ids view
contains every ID exactly once. Dated entries sort by ascending date, then ID.
Missing-date entries sort by ID, before all dated entries in revisions 0–2,
and after all dated entries in revision 3. The view never reorders state.entries.

Success has exactly `{"kind":"success","state":State,"entry_ids":[Identifier,...]}`.
Refusal has exactly `{"kind":"refusal","reason":Reason}`, with no state, value,
partial result or success fields. Equality is recursive JSON-value equality:
object key order is irrelevant, array order and scalar types are significant.
Response value comparison does not compare encoded bytes or object identities;
input/output container disjointness is a separate obligation below.

The evaluator must leave the supplied request and all nested values unchanged
on success and refusal. Returned mutable containers must not alias the request.
It has no external effects. Every finite input in the callable domain terminates
with exactly one response, including malformed requests; invalid input does not
raise a domain exception instead of returning refusal. This does not claim a
wall-clock deadline, persistence, cancellation, concurrent mutation of arguments
or availability of an external service.

## Deterministic validation and refusal priority

Apply the following gates in order, stopping at the first failed gate. Do not
perform reindexing or normalization until all gates pass.

1. **invalid-request**: validate all exact object shapes, required/unknown keys,
   array and element types, array bounds, interface, behavior revision, ID/tag
   grammar and title bounds across the entire request. Check reindex shapes and
   tag grammar here even if its target does not exist. A date field's value is
   deliberately deferred to gate 2; its containing Entry shape is checked here.
2. **invalid-date**: any present date is not an integer in 0..31.
3. **duplicate-entry-id**: any repeated entry ID, whether adjacent or not.
4. **entry-order**: entries are not strictly increasing by ID.
5. **origin-collision**: any stored entry has a tag in both origin arrays.
6. **entry-not-found**: reindex is present and its entry_id is absent.
7. **origin-collision**: in revision 2/3, any supplied reindex tag occurs in the
   selected entry's manual_tags.

These are the complete reasons. Checks within a gate all yield the same reason,
so no traversal-order rule is needed there. Even an operation that would clear
bad stored data refuses first. Neither lack of a target nor an earlier valid
entry masks a later invalid one.

## Oracle, revisions and independent acceptance

[The oracle](../examples/beta/catalog-cases.json) owns exact input and expected
response values; prose owns semantics. Fixture references in its cases are
literal reuse of named request/response data, not transformations or executable
templates. Each case selects a complete request and response by key. The runner
must deep-copy a request before evaluation, compare the complete returned value
to the named expectation, and compare the original request to its pre-call copy.
For success it must also establish that result containers do not alias input
containers. A copied request is reusable input, not authority to run anything.

All cases are mandatory for a conforming reference, including earlier revisions.
Changing a selected revision to 3 is not a substitute for evaluating a revision-0
case. Chain declarations additionally require the named predecessor expected
state to equal the next request state exactly. Later reference checking must
perform each chain using actual successful predecessor state as the next input;
literal fixtures also keep each step independently checkable.

Mutation witnesses describe independently derived wrong behaviors and exact
cases that discriminate them. Expectations were derived from these rules before
a reference implementation. Parsing fixtures is not runtime verification.
Before implementation, independently review and freeze the exact contract/oracle
bytes. A semantic correction then requires a new contract/oracle revision and
retention of earlier bytes, inputs, criteria and observations. Never rewrite an
earlier revision's expectation to fit a later result.

## Actual L0 capabilities and minimal gaps

| Work needed here | Existing L0 or concrete gap |
| --- | --- |
| Scalars, bounded pure evaluation, explicit refusal without partial result | Existing int/bool/string/string_list values and deterministic evaluation provide a base. Application-specific refusal envelopes still need application definitions. |
| Unique ASCII tag members in sorted order | Existing list.unique followed by list.sort; Unicode code-point and byte order coincide on admitted ASCII tags. No new canonicalization primitive is needed. |
| Dates 0..31 and behavior selectors 0..3 | Fit signed 64-bit L0 int; absent dates still need an option/record-field representation. No unsigned-integer expansion is required. |
| IDs/titles/tags and bounds | String values exist; application grammar/ASCII/length predicates and bound checks are missing. |
| Entries, two origins, request/response variants and optional reindex/date | Structured records, bounded lists of records, optional values and tagged alternatives are missing. |
| Reindex, preservation and validation | Bounded traversal, field access/update, exact string equality, membership/intersection, lookup and conditional selection/refusal composition are missing. |
| Date ordering with ID ties and missingness | Scalar comparisons and bounded ordering of records by explicit keys are missing; list.sort only sorts strings. |
| Returning state plus an ID view | Record construction and projection from a record collection are missing. |

These are workload demands for a later language design, not prescribed new
opcodes. Reusable bounded definitions may compose them; an opaque host
`catalog.refresh` primitive must not hide the application's behavior.
LANG-1 implementation and any runtime execution need their own assignment.
