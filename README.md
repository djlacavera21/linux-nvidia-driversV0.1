# nvlx: Linux-NVIDIA-Driver v1.6.5.1

`nvlx` v1.6.5.1 narrows ambiguous NVIDIA continuity checkpoint reconciliation so only transport-level outcomes that may have committed are eligible for same-call recovery. Deterministic validation failures now remain failures even if a later read could find matching state.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.5.1 narrow ambiguous-write reconciliation

- **Reconciliation is now eligibility-gated.** Same-call recovery is attempted only when a PATCH or post-write readback fails with a transport-level unknown outcome, including Kubernetes transport `ApiError(status=0)` and direct timeout/connection failures from compatible clients.
- **Deterministic safety failures are not rescued.** Malformed write responses, leadership or Lease-epoch changes, checkpoint/floor mismatches, canonical readback mismatches and other explicit validation errors fail immediately without being converted into idempotent success.
- **Explicit HTTP errors remain fail-closed in the current call.** Nonzero Kubernetes API error responses do not trigger ambiguous-write reconciliation. If the canonical state was nevertheless committed, a later save may safely discover it through the normal pre-existing-commit path.
- **Write conflicts retain their existing bounded retry.** HTTP 409/412 conflicts still retry through the established two-attempt resourceVersion loop.
- **Post-write transport loss remains recoverable.** If the PATCH may have committed but the response is lost, a fresh Lease GET can prove the exact canonical checkpoint and return a reconciled idempotent receipt.
- **Readback transport loss remains recoverable.** If the independent verification GET fails at the transport layer after a verified PATCH response, a fresh reconciliation GET can prove the exact commit.
- **Per-call receipt proof remains mandatory.** Equal-sequence acknowledgements still require the v1.6.5 `CheckpointCommitReceipt`, exact canonical SHA-256, matching Lease epoch and `idempotent=True`.
- **No checkpoint envelope or replay-floor change.** Canonical v3 checkpoint encoding, sequence floor, readback validation, rollback fencing and Lease transition semantics are unchanged.
- **No readiness or telemetry change.** Closed readiness snapshots and standards-clean Prometheus HELP/TYPE/UTF-8 exposition remain unchanged.
- **No RBAC expansion.** The live operator uses the new v1.6.5.1 store over the same Lease path and permissions.

## Recovery classification

A write is eligible for same-call reconciliation only when nvlx cannot know from the transport whether the write reached Kubernetes. A deterministic response or validation failure is not treated as ambiguous.

This keeps recovery conservative: uncertainty may be proven by a fresh canonical read, while explicit safety violations cannot be overwritten by later evidence in the same operation.

## Safety invariants

1. Same-call reconciliation is reserved for transport-unknown write or post-write readback outcomes.
2. Deterministic checkpoint validation failures remain fail-closed and are never converted into a reconciled receipt.
3. Reconciled receipts still require an exact current Lease holder, Lease transition, sequence floor, baseline/candidate and canonical envelope match.
4. Equal-sequence runtime acceptance still requires exact per-call receipt proof and canonical SHA-256 validation.
5. Lower checkpoint sequences remain rollback failures; cross-epoch equal sequences remain invalid.
6. HTTP 409/412 write conflicts retain bounded retry behavior.
7. The historical tuple `save()` API and advancing tuple-only custom stores remain compatible through v1.6.5 semantics.
8. Readiness, leadership telemetry and Prometheus exposition are unchanged.
9. No new Kubernetes mutation path or RBAC permission is introduced.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.5.1.
