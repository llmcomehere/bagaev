# Supplemental sender-journal model, revision 1

Frozen before implementation, 2026-10-14. Scope derives from accepted P0
save-before-first-send and restore-exact-intent obligations (p0.md106–108,194–196).
Existing85 frozen receiver cases assume saved intents; this separate model makes
that sender assumption explicit and testable. Original P0 files remain unchanged.

Pure synthetic state only. A committed in-memory journal image stands for durable
storage. No filesystem, crash durability, auth service, ID generation, network or
candidate execution is claimed. No inference that two arbitrary similar intents
represent the same human effect. A trusted caller supplies a stable effect handle;
recovery must reuse it. A new handle is a different model input, not an automatic retry.

Journal key is (kind, task_id, effect_handle), where kind is write or transfer.
A second index (kind, task_id, receipt_id) prevents one receipt ID being rebound
to a different effect handle. Both intent and handle are copied on save; all reads
and snapshots are detached. Intent validation reuses the accepted receiver's
structural definition and does not perform ordered receiver authorization checks.

save(kind, handle, intent):
- Validate kind, handle identifier and complete structural intent before mutation.
- Exact repeated save is idempotent.
- Existing handle with any different intent, including a new ID, is refused.
- Same receipt ID under another handle is refused even for equal intent.
- Otherwise commit both indexes atomically in the model.

prepare(kind, task_id, handle, session, epoch=None):
- Refuse if no committed saved intent exists or sender is crashed.
- Return a detached raw-request value using only that saved intent.
- Authorization context is supplied fresh; write requires an unsigned epoch and
  string session, transfer only string session and no epoch.
- No receiver call, network send or journal mutation occurs here.

crash(): make journal inaccessible without altering committed image.
recover(): require crashed state, restore committed saved values; no ID allocation.
Only committed images can be restored; exported image is trusted model data.
An interrupted save before commit leaves the old image; after commit leaves the
complete new image. This is a selected synthetic cut, never partial disk-write proof.

## Frozen independent expectations
1. Prepare before save refuses; receiver state/receipts unchanged.
2. Save then prepare returns exact original complete intent and supplied auth.
3. Mutating original intent, prepared request or snapshot cannot mutate saved state.
4. Exact save twice keeps one row and one ID binding.
5. Same handle with changed payload or new ID refuses and preserves full image.
6. Same ID under another handle refuses and preserves full image.
7. Different task or kind namespaces may reuse literal ID/handle without collision.
8. While crashed, save/prepare refuse. Recover requires crashed state.
9. Save-before-cut absence and save-after-cut presence survive synthetic recovery.
10. Write commit + lost reply + sender crash/recovery + retry gives identical frozen
    write receipt and exactly one effect; fresh auth context is not stored as intent.
11. Transfer commit + lost reply + sender crash/recovery + retry gives identical
    frozen transfer receipt and exactly one authority transition.
12. A timeout or absent receipt requires no journal update; saved ID stays fixed.
13. Invalid structural save or invalid auth context refuses without mutation.

Use original protocol-base, sessions and write-intent-k/transfer-intent-t1 and
frozen receipt fixtures. Expected values are original literals/oracle, not outputs
from the implementation under test. Receiver results remain unknown until a receipt
is observed; prepare alone provides no success/cancellation conclusion.

## Pre-implementation review clarification

Expectations10–11 require that current receiver authority gates still pass.
Saved intent is retry identity only, never authorization. Add explicit controls:
14. After a transfer, the old assignee's saved write retry returns the existing
    assignee-mismatch refusal before receipt lookup; its journal is unchanged.
15. After manage:transfer revocation, the coordinator's saved transfer retry
    returns transfer-scope-required before lookup; its journal is unchanged.
These use existing receiver gates, never journal-based permission. Current
eligible successor may reuse the saved exact write intent with current context.
16. Eligible successor retries the exact saved write using its fresh session/epoch;
    frozen receipt replays only after current receiver gates pass.
17. Recovery preserves both indexes and all prior rows. After recovery, same-handle/
    new-ID and same-ID/new-handle changes still refuse. A before-commit cut adds
    neither index; an after-commit cut preserves both.
18. Structurally valid invalid-tag intent is saveable. The receiver, not journal,
    decides its ordered semantic refusal. Structural invalidity refuses at save.

Diagnostic snapshots remain readable while crashed; save and prepare are blocked.
Synthetic cuts select complete pre-save/post-save images, rather than interrupting
execution inside save. Nested snapshot detachment and non-string sessions/forbidden
transfer epochs are explicit supplemental negative controls.
