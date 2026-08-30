# nvlx: Linux-NVIDIA-Driver v1.6.1.6

`nvlx` v1.6.1.6 is a narrow runtime-integrity hotfix on top of v1.6.1.5. It keeps the same controller API surface and NVIDIA read-only boundary while tightening watch delivery deduplication and provable generation-regression fencing without treating Kubernetes `resourceVersion` as an ordered number.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.1.6. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.1.6 hotfixes

- **Opaque-resourceVersion-safe deduplication.** Exact repeated watch deliveries are suppressed using event type plus GPUFleet UID, generation, and the opaque resourceVersion token. The runtime never performs numeric or lexical ordering of resourceVersion values.
- **Generation-regression fencing.** For the same non-empty GPUFleet UID, a watch event whose generation is lower than the most recently accepted generation is rejected rather than reconciled.
- **Same-generation ambiguity preserved.** Different resourceVersion values at the same generation are both allowed through reconciliation because resourceVersion ordering is intentionally not inferred.
- **Object-replacement safety.** A new UID is treated as a new object incarnation even if its generation restarts at a lower value, preventing stale-generation logic from crossing a delete/recreate boundary.
- **Event-type-aware duplicate detection.** A MODIFIED and DELETED event carrying the same object metadata are not conflated as duplicates.
- **Runtime metrics.** `RuntimeStats` now records exact duplicate watch deliveries and stale-generation events independently from generic reconcile failures.
- **Regression coverage.** Tests cover exact duplicate suppression, same-UID generation rollback, same-generation opaque resourceVersion changes, UID replacement, event-type separation, and invalid watch-object rejection.
- **Prior safeguards retained.** Verified Event attribution, atomic list snapshot validation, shared watch identity checks, status UID/generation continuity, exact unrelated-finalizer preservation, conflict refetch fencing, reflected-token redaction, deterministic reconnects, and shutdown fencing remain active.

## Safety invariants

1. Kubernetes resourceVersion remains opaque and is never numerically or lexically ordered by the controller.
2. Exact repeated watch deliveries cannot trigger repeated reconciliation work.
3. A provable same-UID generation regression cannot roll controller state backward.
4. A new GPUFleet UID is always treated as a new incarnation rather than compared against the prior object's generation history.
5. Ambiguous same-generation resourceVersion changes remain eligible for reconciliation rather than being guessed stale.
6. Every controller-owned Kubernetes mutation remains fenced by live leadership.
7. NVIDIA resources remain read-only in v1.6.1.6.
8. All v0.1-v1.6.1.5 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay and Lease-CAS safeguards remain in force.
