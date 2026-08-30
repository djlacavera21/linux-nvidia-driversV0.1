# nvlx: Linux-NVIDIA-Driver v1.6.2.7

`nvlx` v1.6.2.7 is a narrow post-1.6.2.6 runtime-correctness hotfix. It preserves the Kubernetes API surface and NVIDIA read-only boundary while making live watch duplicate suppression retry-safe: a watch fingerprint is no longer permanently committed before reconciliation proves that the event reached a settled outcome.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.2.7. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.2.7 hotfixes

- **Retry-safe watch dedupe.** ADDED/MODIFIED/DELETED fingerprints are staged during reconciliation and committed to duplicate suppression only after a settled result.
- **Deferred-event retry.** `standby`, `fenced`, `finalizer-hold`, and other non-settled outcomes restore the prior watch-cache state so an identical later delivery remains eligible for retry.
- **Exception rollback.** If reconciliation raises after a fingerprint is staged, the prior cache state is restored before the exception propagates.
- **Prior-state restoration.** When a newer event was staged over an older settled cache entry, a deferred reconciliation restores that older entry rather than dropping watch history entirely.
- **DELETED retry safety.** A deferred DELETED/finalizer attempt restores the prior non-DELETED cache state, so an identical DELETED delivery can retry instead of being suppressed as already processed.
- **Settled suppression retained.** Successful settled outcomes still commit the fingerprint, so exact duplicate watch deliveries remain suppressible after work actually completes.
- **Semantic finalizer safeguards retained.** Duplicate-free semantic finalizer preservation, generation binding, UID/name verification, and pre-mutation duplicate fencing remain active.
- **Watch/readiness safeguards retained.** Corrupt watch relists, inventory-continuity invalidation, Lease freshness, leadership invalidation, token-file auth, bounded watch cache, and opaque resourceVersion semantics remain unchanged.

## Safety invariants

1. A live watch fingerprint cannot permanently suppress an identical future delivery unless reconciliation reached a settled outcome.
2. Deferred or failed watch reconciliation restores the exact prior cache state.
3. DELETED events remain retryable when finalizer work is deferred.
4. Exceptions during watch reconciliation cannot strand staged duplicate-suppression state.
5. Settled events remain eligible for exact duplicate suppression.
6. List-snapshot seeding continues to occur only for settled list reconciliation outcomes.
7. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
8. Malformed state-bearing watch content still forces a trusted relist.
9. Leadership freshness and inventory freshness remain independent readiness requirements.
10. Conflict retries remain bounded and leadership-fenced.
11. NVIDIA resources remain read-only in v1.6.2.7.
12. All v0.1-v1.6.2.6 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay, UID-integrity, Lease-CAS, leadership-freshness, inventory-continuity, watch-trust, generation-verification, and semantic-finalizer safeguards remain in force.
