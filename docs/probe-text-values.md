# Bounded immutable Text value precursor

Contract: `bagaev-text-value-probe/1`. This is a value-library precursor for a
future typed language profile, not support for Text in the current scalar source
syntax, scalar native ABI, or generated LLVM. Those profiles remain unchanged.
The public catalog workload needs string identity, lengths and ordering without
an opaque application-specific host operation.

Unicode scalar and UTF-8 well-formedness terminology follows
[Unicode 17.0, section 3.9](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-3/).
No version-dependent character-property or locale tables are used.

## Value and construction

A Text value is a borrowed, immutable UTF-8 byte slice containing only Unicode
scalars. Each value has at most 1024 UTF-8 bytes and at most 256 Unicode scalars.
These are experimental per-value caps, not an application title rule, aggregate
memory guarantee or production limit. Empty text is admitted. NUL, controls,
noncharacters and supplementary scalars are admitted. No normalization, case
folding, locale processing or grapheme segmentation occurs.

Construction takes a complete byte slice and applies these gates in order:

1. More than 1024 bytes: `TEXT_BYTES`.
2. Invalid UTF-8: `TEXT_UTF8`. This includes truncated, overlong, out-of-range
   encodings and UTF-8 encodings of surrogate code points.
3. More than 256 decoded scalars: `TEXT_SCALARS`.
4. Otherwise return a checked Text value borrowing exactly the original bytes.

No truncation, replacement character, lossy decoding or normalization repairs an
input. Construction does not interpret JSON escapes. A future JSON boundary must
decode a valid surrogate pair to one scalar and reject isolated surrogates before
constructing Text; that boundary is outside this byte-value contract.

## Pure observations

- `byte_len` returns the exact original UTF-8 byte count.
- `scalar_len` returns the Unicode scalar count, not display width or graphemes.
- `equal` compares the complete scalar sequence for exact equality.
- `compare` is lexicographic scalar-value order, returning -1, 0 or 1. At the
  first different scalar, the smaller scalar sorts first; otherwise the shorter
  sequence sorts first. Valid UTF-8 byte order gives the same result. In
  particular U+E000 sorts before U+10000, unlike UTF-16 code-unit order.
- A byte view returns exactly the borrowed original slice, including embedded
  zero bytes. It is not a zero-terminated C string.

Comparison accepts only two already checked values. No int/bool coercion,
ambient state, locale, allocation, callbacks, file I/O or native execution is
part of these operations. Borrowed values may not outlive their byte storage;
source-language handles or serialized pointers are not introduced. A Rust
implementation can express this with a private-field value and an input lifetime.
This is not an ownership strategy for containers or a complete export ABI.

## Deliberately not yet specified

No language syntax, runtime parameter decoder, native descriptor, Text return
ABI, semantic work budget, concatenation, slicing, allocation/export mechanism
or integration with scalar expressions is introduced. Before integration, a
separate versioned profile must fix work charges, resource-failure order,
source locations, aggregate limits and ownership across the call boundary.
Library observations here must not be advertised as a Text-capable language.

## Pre-implementation cases

[Literal cases](../examples/probes/text-value-cases.json) fix construction results,
lengths, byte preservation and comparisons before a value implementation. Hex
inputs are exact bytes. A repeat recipe means exact concatenation of the given
byte unit, not a call to a candidate operation. Expected outcomes and counts are
literal values. Combined-invalid cases test gate priority.

These finite examples are not a proof of all UTF-8 behavior or allocation safety.
Keep source acceptance, executed library checks and native language conformance
separate. No candidate code is authorized merely by appearing in this contract.
