# A typed tag collection with retained results

The [TagBox source](../examples/probes/tag-box/TagBox.bagaev) uses form/5 Text and
TextList calls in an actual component operation. It shows how pure collection
rules become typed outcomes and then retained receiver results under the
existing serial SQLite bridge. The programme source stays fixed throughout.

## Rules in the language

The add_sorted_tag operation checks in this order:

1. An empty tag declines with empty-tag.
2. An exact existing tag declines with already-present.
3. With fewer than 64 current entries, append the tag and produce ascending
   unique values using list.unique(list.push(...)).
4. Otherwise decline with tag-capacity.

The source preserves the nominal collection key and replaces only tags. Exact
comparison does not trim, case-fold or Unicode-normalize text. Sorting/uniqueness
is an explicit operation, not a property of every TextList value.

## A small complete trace

Start at revision 1 with tags red, blue, red. The fixture's exact expectations are:

| Request | Tag | Business result | Current revision and tags |
| --- | --- | --- | --- |
| A | empty | Declined: empty-tag | 1: red, blue, red |
| B | red | Declined: already-present | 1: red, blue, red |
| C | green | Applied | 2: blue, green, red |
| D | é | Applied retained, response OutcomeUnknown | 3: blue, green, red, é |

Four terminal operations yield storage generation 4 and two state mutations.
The fixture disables observation for D; this is observation gating, not a
network-loss experiment. A reconstructed bridge cannot read D while observation
is disabled. After current observation is enabled, it reads D and the earlier A
receipt without another business evaluation or changing the image. A new E
request is denied when current submit/write conditions are false.

The unchanged note about [stock receipts](stock-adjustment.md) applies here too:
current state and an old receipt's revision answer different questions.

## Business refusal and computation failure differ

A separate 64-entry fixture declines tag-capacity without mutating the collection.
A separate fixture has sixteen 256-byte strings, already totaling 4096 UTF-8
bytes. Adding one byte reaches the existing list.push aggregate bound. The actual
core returns RR_LIST_BYTES; the receiver reports OWNER_EVALUATION, and no state,
terminal receipt or whole-image CAS change is committed.

This example deliberately appends before deduplicating. An intermediate list can
therefore exceed the byte bound even when a hypothetical final unique list
would fit. The count guard also examines current entries before normalization.
This is not a total add-tag service for every admitted state; the example makes
that computation-failure boundary visible instead of calling it an ordinary
business decline or a successful update.

## Reproduction and evidence

The [fixture manifest](../examples/probes/tag-box/manifest.json) binds the readable
source, exact decoded graph, receiving policy, full receipts and boundary states.
After review and selection of the authorized bounded local profile:

```console
python3 -B tests/probes/tag_box_checks.py --reader /absolute/reviewed/reader --reader-sha256 READER_SHA256 --reference /absolute/reviewed/record-reference10 --reference-sha256 REFERENCE_SHA256 --output /absolute/new-output-directory
```

Supply actual separately reviewed build paths/hashes. The driver creates only
its own new output and SQLite files and retains raw native observations. It does
not install, download or compile executables. The passing run made 82 native
calls in the main trace, eight in the count-bound case and seven in the byte-bound
case. The main trace evaluated the business operation four times; reconstruction
added none. The two boundary cases each attempted one business evaluation, with
the byte-bound attempt failing as specified. Portable repetition reused these
cases, not new independent coverage.

The existing fixed-source, trusted callbacks/filesystem and single-writer SQLite
assumptions remain. This does not test process or power-loss recovery, perform
new-source admission, implement production authentication or measure cost/speed.
The original TextList/typed-core/owner implementations are unchanged.
