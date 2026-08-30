# nvlx: Linux-NVIDIA-Driver v1.6.1.7

`nvlx` v1.6.1.7 is a narrow runtime-integrity hotfix on top of v1.6.1.6. It keeps the same controller API surface and NVIDIA read-only boundary while tightening relist deduplication and DELETED-watch handling without treating Kubernetes `resourceVersion` as ordered.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.1.7. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.1.7 hotfixes

- **Relist-seeded watch state.** After a trusted list snapshot is reconciled, each listed GPUFleet seeds the in-memory watch state. The first exact ADDED/MODIFIED delivery for the same UID, generation, and opaque resourceVersion can therefore be suppressed after relist/reconnect.
- **Opaque resourceVersion retained.** resourceVersion tokens are matched only for exact equality; they are never numerically or lexically ordered.
- **Deletion separation.** A DELETED watch event is never swallowed merely because its object metadata exactly matches a prior list, ADDED, or MODIFIED state.
- **Observe-only terminal delete.** A DELETED event that does not carry `deletionTimestamp` is treated as `deleted-observed`; it cannot run status planning or a stale mutation path after the object is already gone.
- **Generation fencing retained.** Same-UID generation regressions remain fail-closed across relists.
- **New incarnation handling retained.** A new UID remains a new object incarnation even when generation restarts lower.
- **Runtime counters.** RuntimeStats now records relist-seeded objects and accepted DELETED watch events in addition to duplicate/stale-generation counters.
- **Regression coverage.** Tests cover first-watch duplicate suppression after a list, deletion separation, observe-only terminal deletion, post-list generation rollback, and UID replacement.

## Safety invariants

1. A trusted list snapshot can seed deduplication state, preventing the same exact state from being reconciled again immediately after relist.
2. A DELETED delivery remains semantically distinct from prior list/ADDED/MODIFIED deliveries.
3. Terminal DELETED events without deletionTimestamp are observe-only and cannot trigger status mutation.
4. Kubernetes resourceVersion remains opaque and is never ordered.
5. Same-UID generation regression fencing remains active across relists.
6. Every controller-owned Kubernetes mutation remains fenced by live leadership.
7. NVIDIA resources remain read-only in v1.6.1.7.
8. All v0.1-v1.6.1.6 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay and Lease-CAS safeguards remain in force.
