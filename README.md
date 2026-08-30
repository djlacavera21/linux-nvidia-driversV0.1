# nvlx: Linux-NVIDIA-Driver v1.6.2.9

`nvlx` v1.6.2.9 is a narrow post-1.6.2.8 runtime-integrity hotfix. It makes relist establishment atomic: the operator will not mark inventory fresh or open a watch if any object from the trusted list snapshot failed to reach a settled reconciliation outcome.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.2.9. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.2.9 hotfixes

- **Atomic relist settlement barrier.** Every object in a trusted GPUFleet list snapshot must settle before that snapshot can establish a watch continuity window.
- **No partial-snapshot watch.** If even one list object returns `standby`, `fenced`, `finalizer-hold`, or another deferred result, the runtime returns `relist` without opening the watch stream.
- **Inventory freshness stays false.** A partially reconciled list cannot transiently advertise fresh inventory.
- **No partial dedupe seeding.** Deferred relists do not seed settled siblings into the watch cache; the next trusted relist starts from a coherent snapshot rather than mixed continuity state.
- **Cycle-local barrier reset.** The deferred flag resets before each new list/watch attempt, allowing a later fully settled relist to establish continuity normally.
- **Settlement-bound cursor retained.** v1.6.2.8 cursor rollback, deferred-event relist, BOOKMARK overrun prevention, stale-generation fencing, and opaque resourceVersion semantics remain active.
- **Prior safeguards retained.** Retry-safe watch dedupe, semantic duplicate-free finalizer preservation, generation-bound mutation verification, corrupt-watch relists, inventory/leadership freshness invalidation, token-file auth, bounded watch cache, and verified Lease writes remain active.

## Safety invariants

1. A list snapshot cannot establish inventory freshness or a watch unless every listed GPUFleet reaches a settled reconciliation outcome.
2. One deferred list object makes the entire relist continuity attempt fail closed.
3. A failed relist opens no watch stream and seeds no partial watch-cache state.
4. The next cycle must obtain a fresh trusted list before watch continuity can be re-established.
5. State-bearing watch deliveries remain settlement-bound and deferred watch work still forces relist before later events or BOOKMARKs are consumed.
6. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
7. Leadership freshness and inventory freshness remain independent readiness requirements.
8. Conflict retries remain bounded and leadership-fenced.
9. NVIDIA resources remain read-only in v1.6.2.9.
10. All v0.1-v1.6.2.8 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay, UID-integrity, Lease-CAS, leadership-freshness, inventory-continuity, watch-trust, generation-verification, semantic-finalizer, retry-safe-watch, and settlement-bound-cursor safeguards remain in force.
