# Bounded portable context receiver

`src/bagaev_probe_context.py` implements the seven reconstruction phases of
the [portable context contract](probes.md#portable-context-and-finite-choices).
Its inputs are separate UTF-8 JSON frames. It does not discover files, fetch
sources, call a model, run a program, commit changes or grant admission.

`inspect(context, expectation, kernel_checker=None)` checks phases 1–6 and
returns pinned identities plus unresolved unknown/effect IDs.
`process(context, expectation, evidence=None, request=None, response=None,
kernel_checker=None)` additionally checks applicable evidence and a complete
request/response pair. Inputs to these functions are bytes or strings; optional
frames use `None`. Returned records are detached observations. Both functions
report `admission=false` and `model_calls=0`.

The caller supplies expectations independently of the candidate packet.
Source bytes, reference boundaries, obligations, candidate content and the
complete candidate mapping must match. Evidence result labels are retained
assertions, not proof of execution. Generate/refine may return only drafts;
selection resolves an already checked choice from the exact mapping. Refusal,
abstention and no-choice do not conceal a change or permit an effect.

## Semantic checking boundary

The L2 tuple uses the actual L2 program and patch checker. Its underlying
refusal codes are retained. Kernel semantic checking requires an explicit
trusted host callback supplied by the caller, never by packet metadata.
The callback must completely check the supplied program and return its exact
canonical bytes, or raise `KernelRefusal(code, program_relative_pointer)`.
The receiver binds the returned bytes to the complete original program.
It raises `ContextUnavailable` if the callback is absent, returns the wrong
type, or substitutes different program bytes. This exception is an unavailable
checking capability, not a semantic refusal or a successful observation.

Matching bytes alone cannot prove that a callback performed semantic checking.
The callback is a trusted dependency, not an implementation of the kernel
checker. A packet cannot install, select or authorize host code. Callback
configuration and execution remain subject to the host's separate policy.

## Observed bounded checks, October 4, 2026

Eight context test methods passed, covering all 23 frozen context cases and
their ordered exchange traces, absent/bad checker behavior, duplicate JSON,
UTF-8 references, required obligations, response binding, and actual L2 program
and patch checking. The ordinary unit suite explicitly uses a checker double
restricted to the single kernel baseline in the frozen oracle.

A separate integration pass checked that exact baseline with the existing Rust
frontend, verified the returned complete program and its expected pin, and
reran the eight methods using a cache restricted to those checked bytes. This
establishes that one bounded integration, not arbitrary kernel-program coverage
or a generic host adapter. The baseline pin is
`sha256:fb0a3a528338c01535de4a16bb52a4375e7c873373d67ffa9b55feb411be05ac`.
The unchanged context oracle SHA-256 is
`090d64ba08ca17d9f61f4a8bf7b91dda0a827ee6c6fb71b49764d49cdc5c1661`.

The same source revision also passed 12 codec, six edit and 17 existing L2 test
methods in separate bounded processes. Review was a separate same-maintainer
pass, not independent review. Full mutation acceptance, direct semantic-step
accounting, model observations and comparative cost/performance measurements
remain open. These checks do not close PB0 or establish production readiness.
