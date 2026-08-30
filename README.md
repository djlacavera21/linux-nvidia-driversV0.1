# nvlx: Linux-NVIDIA-Driver v1.6.1.5

`nvlx` v1.6.1.5 is a narrow runtime-integrity hotfix on top of v1.6.1.4. It keeps the same controller API surface and NVIDIA read-only boundary while tightening Event attribution and list/watch object validation.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.1.5. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.1.5 hotfixes

- **Event attribution verification.** Event POST success must return coherent metadata and echo the expected GPUFleet `regarding.name` and `regarding.uid`.
- **Reporting identity verification.** Event responses must echo `nvlx.io/operator` and the active controller reporting instance before Event creation is considered verified.
- **Atomic list snapshot validation.** Every listed GPUFleet is prevalidated before any object from that snapshot is reconciled. A malformed item aborts the snapshot and leaves inventory freshness false, preventing partial reconciliation of an untrusted list.
- **Watch object identity hardening.** ADDED/MODIFIED/DELETED watch objects require valid metadata name, resourceVersion, and non-negative generation before reconciliation. Invalid objects are ignored and counted as reconciliation failures without advancing the object cursor.
- **Shared identity validation.** Direct reconcile inputs, list items, and watch objects use the same fail-closed identity validator.
- **Regression coverage.** Tests cover wrong Event name/UID/reporting identity, valid Event attribution, atomic list rejection, and malformed watch-object suppression.
- **Prior safeguards retained.** Status UID/generation continuity, exact unrelated-finalizer preservation, conflict refetch fencing, status echo checks, strict list envelope validation, bookmark hardening, Event leadership fencing, reflected-token redaction, deterministic reconnects, and shutdown fencing remain active.

## Safety invariants

1. A Kubernetes Event is not treated as verified unless the API response attributes it to the intended GPUFleet and reporting instance.
2. A list snapshot containing any malformed GPUFleet is rejected before any item in that snapshot can mutate controller-owned state.
3. Malformed watch objects cannot enter reconciliation or advance object state.
4. Successful mutation verification remains bound to coherent Kubernetes object identity.
5. Every controller-owned Kubernetes mutation remains fenced by live leadership.
6. NVIDIA resources remain read-only in v1.6.1.5.
7. All v0.1-v1.6.1.4 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay and Lease-CAS safeguards remain in force.
