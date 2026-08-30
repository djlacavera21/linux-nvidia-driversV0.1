# nvlx: Linux-NVIDIA-Driver v1.6.1.8

`nvlx` v1.6.1.8 is a narrow runtime-integrity hotfix on top of v1.6.1.7. It keeps the same controller API surface and NVIDIA read-only boundary while bounding/pruning in-memory watch state and preserving retry eligibility for list reconciliations that did not settle successfully.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.1.8. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.1.8 hotfixes

- **Bounded watch cache.** The per-process watch state has a validated positive integer limit (default 4096). New object keys beyond the bound deterministically evict the oldest retained key instead of growing memory without bound.
- **Trusted relist pruning.** A valid list snapshot prunes cached object keys that no longer exist in that snapshot, preventing deleted/replaced GPUFleet history from accumulating indefinitely.
- **Deferred-reconcile retry preservation.** List items that return deferred outcomes such as `standby`, `fenced`, `finalizer-hold`, `hold`, or other unsettled states are not seeded into duplicate suppression. An identical first watch delivery can therefore retry work after leadership or API conditions recover.
- **Settled-only relist seeding.** Only settled outcomes such as a verified status patch, status/event no-op, finalized object, or observe-only deletion seed relist dedupe state.
- **Opaque resourceVersion retained.** resourceVersion remains equality-only and is never numerically or lexically ordered.
- **Generation fencing retained.** Same-UID generation regressions remain fail-closed for retained cache entries.
- **Lifecycle counters.** RuntimeStats records cache pruning, bounded-cache evictions, and deferred relist objects in addition to prior duplicate, stale-generation, relist-seeded, and deletion counters.
- **Regression coverage.** Tests cover deferred list retry through an identical watch event, successful relist seeding, absent-object pruning, bounded deterministic eviction, invalid cache limits, and generation-regression fencing after cache lifecycle changes.

## Safety invariants

1. Watch-state memory cannot grow without a configured hard bound.
2. A trusted relist removes stale cache entries for objects no longer present in the snapshot.
3. Deferred list work cannot be hidden by duplicate suppression before it has a chance to retry.
4. Kubernetes resourceVersion remains opaque and is never ordered.
5. Same-UID generation regression fencing remains active for retained state.
6. Terminal DELETED events remain observe-only unless Kubernetes deletion flow still requires finalizer handling.
7. Every controller-owned Kubernetes mutation remains fenced by live leadership.
8. NVIDIA resources remain read-only in v1.6.1.8.
9. All v0.1-v1.6.1.7 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay and Lease-CAS safeguards remain in force.
