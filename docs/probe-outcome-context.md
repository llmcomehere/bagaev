# Detached outcome-context framing

Common native failure payloads do not identify their source, executable or invocation. This experimental [byte codec](../examples/probes/outcome-context/codec.py) retains independently expected context around a native payload. It does not invoke native code or prove that any code ran.

The [BOUTCTX1 contract](../examples/probes/outcome-context/contract.md) defines a160-byte header with profile, method, three32-byte pins, payload length/kind and checksum. Payloads are bounded to4325440bytes. The receiver must supply its expected context independently; the submitted frame may not choose it. Exact input bytes are pinned without normalization. Existing BCMPRES1/2/3 success framing and profile-specific language-failure pairs are checked.

Success returns FramedPayload with semantic_validated, authenticated and execution_authority all false. Node/type/source-path validation belongs to separate typed readers. A wrong value or invalid node with a recomputed checksum is deliberately accepted by outer framing. Checksums and matching expected pins are not signatures, execution proof, truth or permission. This is an experimental utility, not a production protocol or loader.

## Synthetic reproduction

Run python3 tests/probes/check_outcome_context.py in an approved bounded environment. The runner checks [40 existing literal cases](../examples/probes/outcome-context/cases.json), four immutable-input/size/type API guards, and [six comparison mutation witnesses](../examples/probes/outcome-context/mutation-cases.json). The original codec must refuse each mutation witness; its explicit single faulty comparison produces normal false acceptance while evidence flags remain false. Only these listed own-code substitutions are evaluated. No compiler, native artifact, network, key or credential is used.

No private capture sets, final executable hashes, host paths, call observer or retrospective build associations are included. Source/data checks and documentation CI do not establish full semantic conformance, historical execution authenticity or independent reproduction.
