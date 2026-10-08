# Direct function context for focused editing

Provide a separate bagaev-function-context/1 envelope containing the unchanged
fragment packet and direct caller/callee declarations (name, signature, function
hash). Missing callees appear explicitly with declared:false and null signature.
Do not include other bodies, execute code or infer runtime reachability. Include
calls in all syntactic branches, not only a presumed successful path. Variant
arm labels and binders are metadata and must not be mistaken for calls. The
whole base pin binds this finite syntactic view; no affected-test coverage or
transitive consumer closure is claimed. Existing fragment schema stays unchanged.
Freeze a small three-function graph with a variant alternative named call and
an unresolved helper, plus known catalogue callers of id_ok.
