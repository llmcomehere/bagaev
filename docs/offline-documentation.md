# Offline documentation preview

The optional entry can be built from the same versioned repository documents,
without maintaining another language contract. This is an offline artifact;
it does not enable GitHub Pages, deploy a service, submit a search index or
establish that an agent will discover or choose bagaev.

After reviewing the builder and choosing your authorized bounded local profile,
from a clean checkout run:

```console
python3 -B tools/build_offline_docs.py --revision "$(git rev-parse HEAD)" --output "$PWD/offline-preview"
```

The output directory must be new and absolute, with an existing parent. Open
its `index.html` in a browser. No local web server or JavaScript is needed.
`-B` suppresses Python cache writes; it is not isolation. The builder itself
neither follows links nor executes examples, source programs or tests.

## Sources and reproducibility

The fixed input list is README, the task chooser, pure filtering guide, queue
change example, integrated beta guide, toolchain contract, L2 contract, explicit
filter saved-workflow guide, shared Store contract, stateful component guide,
typed outcome/composition/persistence contracts and LICENSE. These fourteen sources
produce fifteen HTML pages including the README entry alias, plus the index.
Each source receives an HTML page. The entry aliases the README view;
`index.json` records titles, paths, the supplied revision and actual SHA-256
hashes of source bytes. The license is displayed as escaped plain text.

The revision is a caller-supplied source reference, not an attestation that an
arbitrary working tree matches a commit. Use a clean, reviewed checkout and
compare its source state before sharing. Per-file hashes identify what was
actually rendered. There is no build timestamp; identical input and revision
produce identical output bytes.

Selected document links point to local HTML. Other repository links point to
that exact revision on GitHub. Ordinary external HTTP(S) references remain
clickable links; nothing fetches them during building or automatically embeds
remote assets. Navigation does not copy linked files outside the allowlist.

## Rendering and limits

This small renderer supports headings, paragraphs, inline code, direct links,
bold text, lists including nested items, tables and fenced code. It is not a
complete CommonMark implementation: unsupported notation remains visible text.
The Markdown source remains authoritative and is linked on every page. Raw
HTML is escaped; code fences remain inert. No scripts, image embeds, analytics,
external stylesheets or fonts are emitted.

The builder refuses invalid revisions, missing/nonregular/symlinked sources,
source files larger than 1 MiB, invalid UTF-8, unsupported link schemes,
repository-root escapes and existing output directories. It validates sources
and renders pages before creating output. OS failures during writing can still
leave a partial new directory; that directory is not a successful build and
must not be presented as one. Existing files are never overwritten.

The selected checkout and output parent are trusted local filesystem inputs;
these checks do not claim protection against concurrent hostile filesystem
mutation. No authentication, sharing, hosting or deployment policy is changed.

## Checks

```console
python3 -B tests/test_offline_docs.py -v
```

The tests exercise deterministic output and provenance, inert malicious-looking
code/raw HTML, exact link routing, unsafe-link refusal before output creation,
missing/symlink inputs, revision/no-overwrite refusal, nested lists and unclosed
fences. Building the accepted selected documents also permits static checks of
local pages/anchors and content hashes. These are static artifact checks, not
browser visual QA, runtime conformance, release readiness or search evidence.
