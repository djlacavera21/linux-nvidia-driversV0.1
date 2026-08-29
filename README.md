# nvlx: Linux-NVIDIA-Driver v1.5.3

`nvlx` v1.5.3 is a third stabilization patch for the live Kubernetes operator. It closes stale-generation and duplicate-status-write races while tightening finalizer sequencing and Kubernetes patch response handling, without expanding the CRD or control-plane API surface.

> [!IMPORTANT]
> The operator remains approval-bound and fail-closed. Desired driver and GPU Operator changes still pass through the existing approval, maintenance, preflight, rollout, circuit, health/SLO, PSIRT, rollback and audit gates.

## v1.5.3 fixes

- **Stale generation guard.** Reconcile events older than the latest observed `metadata.generation` are discarded before runtime planning or status mutation.
- **Status write idempotency.** Stable status fingerprints ignore volatile transition/event timestamps, suppressing repeated status writes when the logical status is unchanged.
- **Finalizer sequencing.** Deletion processing treats an already-absent protective finalizer as complete instead of attempting another metadata mutation.
- **Patch classification consistency.** `410 Gone` is terminal, `412 Precondition Failed` relists and retries, and `408`/`425`/`429` plus 5xx responses remain retryable.
- **Regression coverage.** Tests cover stale event generations, duplicate status suppression, already-removed finalizers, precondition conflicts, gone resources, and timeout retries.
- **1.5.2 retained.** Delete-event safety, bounded dead-letter behavior, leader-lease readiness, strict field ownership, watch cursor validation, optimistic concurrency and all previous controller safeguards remain active.

## Safety invariants

1. An older generation cannot overwrite status derived from a newer desired state.
2. Logically identical status does not produce repeated Kubernetes writes solely because timestamps changed.
3. Finalizer removal is idempotent when deletion races another controller/API update.
4. Patch precondition conflicts force relist/retry instead of blind overwrite.
5. Gone resources terminate mutation attempts.
6. All v0.1-v1.5.2 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM and provenance safeguards remain in force.
