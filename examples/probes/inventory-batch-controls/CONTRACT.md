# Concrete batch semantic controls

Do not change accepted programme or 32-case oracle. Before creating mutants,
select five independent one-site mistakes and existing frozen witness cases:
1. Skip first stock validation by routing index0 to valid-stock helper: duplicate.
2. Return tentative stock instead of original on business rejection: rollback-second.
3. Read requests in reverse order: sequential (receipt snapshots/order differ).
4. Append each receipt to an empty list instead of prior receipts: sequential.
5. Validate only the first request shape: later-malformed-takes-precedence.

Each mutant must differ in exactly its declared programme subtree, still pass
checked profile11, and exit normally with status success but a complete value
different from the frozen expected outcome. A syntax/type/runtime failure is
not a semantic mutant detection. Use the unchanged admitted reference, one
preselected case each; no compiler, native or model calls. These five named
controls test selected invariants and do not prove arbitrary mutation coverage,
backend equivalence or a universal resource bound.
