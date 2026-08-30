# nvlx: Linux-NVIDIA-Driver v1.6.2.8

`nvlx` v1.6.2.8 is a narrow post-1.6.2.7 runtime-integrity hotfix. It preserves the Kubernetes API surface and NVIDIA read-only boundary while binding watch cursor advancement to trusted, settled work instead of merely receiving an object from the stream.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.2.8. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.2.8 hotfixes

- **Settlement-bound watch cursor.** `last_resource_version` is rolled back when reconciliation is deferred or raises; receiving a watch object is no longer sufficient to advance the cursor.
- **Deferred-event relist.** A state-bearing watch event that returns `standby`, `fenced`, `finalizer-hold`, or another non-settled outcome immediately breaks continuity and forces a full relist instead of continuing to consume later events.
- **BOOKMARK overrun prevention.** Because deferred work forces relist immediately, a later BOOKMARK cannot advance the cursor past unfinished reconciliation.
- **Exception cursor rollback.** Exceptions restore the exact prior cursor before propagating, matching the retry-safe watch-cache rollback behavior introduced in v1.6.2.7.
- **Stale-generation continuity break.** A same-UID generation regression now invalidates inventory and forces relist instead of allowing the watch stream to continue after a provably stale object state.
- **Settled cursor advancement.** Settled state-bearing deliveries explicitly advance the cursor to their returned opaque resourceVersion.
- **Trusted duplicate advancement.** Exact duplicate deliveries may advance the cursor because their fingerprint is already backed by settled reconciliation state.
- **BOOKMARK boundary retained.** Valid BOOKMARK resourceVersions may advance the cursor only while no deferred work remains outstanding; malformed BOOKMARK metadata is ignored without replacing the cursor.
- **Prior safeguards retained.** Retry-safe watch dedupe, semantic duplicate-free finalizer preservation, generation-bound mutation verification, corrupt-watch relists, inventory/leadership freshness invalidation, token-file auth, bounded watch cache, and verified Lease writes remain active.

## Safety invariants

1. A state-bearing watch delivery cannot permanently advance `last_resource_version` unless its reconciliation reached a settled result.
2. Deferred or exceptional watch reconciliation restores the prior cursor and prior watch-cache state.
3. Deferred watch work forces a relist before later stream events or BOOKMARKs are consumed.
4. Same-UID generation regression breaks watch continuity and cannot advance the cursor.
5. Exact duplicate watch deliveries remain suppressible and may advance the cursor only because they reference already-settled state.
6. Valid BOOKMARKs cannot leap past unfinished state-bearing work.
7. List snapshot resourceVersion remains the trusted cursor baseline for each new watch cycle.
8. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
9. Malformed state-bearing watch content still forces a trusted relist.
10. Leadership freshness and inventory freshness remain independent readiness requirements.
11. Conflict retries remain bounded and leadership-fenced.
12. NVIDIA resources remain read-only in v1.6.2.8.
13. All v0.1-v1.6.2.7 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay, UID-integrity, Lease-CAS, leadership-freshness, inventory-continuity, watch-trust, generation-verification, semantic-finalizer, and retry-safe-watch safeguards remain in force.
