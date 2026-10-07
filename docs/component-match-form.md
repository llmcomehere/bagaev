# Readable variant matching

Explicit component-form/4 adds a way to consume typed variants within the
component, using the existing typed-record/10 match operation. It decodes to the
same component-source/2. Previous form codecs are unchanged. Use the fixed
bagaev_component_match_form API or explicitly select --form 4 in the data-only
component_text.py converter. The default stays form 2.

A helper can interpret a StockOutcome without moving that decision into host code:

```text
fn quantity(value: StockOutcome) -> Int64 =
  match (value) {
    Decline(error): -1;
    Propose(stock): stock.quantity;
  };
```

Here -1 is this helper's explicit local convention, not a new language-wide
representation of failure. The original outcome remains nominally typed.
A successful Propose is still a proposed value, not an applied state.

## Scope and checking

The scrutinee requires parentheses. Each arm names an alternative and a single
payload binder, followed by a colon, expression and semicolon. Arm order is
preserved exactly in the semantic source. Duplicate labels are a form refusal.
A binder is visible only within its own arm. An outer let remains visible there;
the scrutinee and other arms do not acquire that binder.

The actual typed checker still enforces exhaustive alternatives, valid variant
names, fresh bindings and a common result type. The codec alone does not prove
these properties. There are no wildcard/default arms, guards, recursive patterns
or implicit conversion between variants. An unused arm is checked statically
but not evaluated: overflow in it is not triggered by selecting another arm.
The existing depth, size, logical-work and overflow rules remain in force.

Encoding requires exact decode/encode equality. In particular, a raw arg node
cannot silently become a use node captured by an arm binder, and an unbound use
cannot silently become an arg. Unsupported representations refuse FORM_PROFILE.

## Compatibility and tools

Form 3 rejects the new header; form 4 rejects the form 3 header. The file converter
selects only a fixed codec from its explicit 2/3/4 choice. It continues to report
semantic_check:false and execution_admission:false and refuses existing outputs.

The optional diagnostic command still accepts only form 3. The existing detached
edit/3 route also still accepts only form 3. This slice does not silently extend
those versioned contracts. Prepare source/2 data and use its established checker;
no live admission follows from conversion.

## Bounded evidence

The [fixture manifest](../examples/probes/component-match/manifest.json) pins four
hand-authored exact semantic graphs frozen before the codec: payload extraction,
reversed arm order, outer let use, and lazy overflow. Five fixed syntax refusals
and two encoder capture controls passed. Twelve actual reference invocations
checked eight stated values/overflow outcomes and four core refusals for missing
arms, unknown alternatives, mismatched result types and cross-arm binder use.
One actual component-policy check passed. Work/location fields were retained as
observations, not invented as independent full-wire expectations.

Portable drivers are component_match_checks.py, component_match_core_checks.py
and component_match_cli_checks.py under tests/probes. The core driver requires
separately selected reviewed reader/reference binaries and their hashes. These
are finite same-maintainer checks, not independent reproduction or measurement.

Six new file-tool calls passed. The existing six-call arithmetic check uses 99
instead of 4 for its unknown-selector control because 4 is now explicitly
supported; prior captures remain historical. The default 32-call converter suite
and 15-case diagnostic suite passed. The diagnostic implementation and form/3
codec are unchanged; its fixture now labels the shared converter hash as a
dependency rather than claiming that converter remained unchanged.
