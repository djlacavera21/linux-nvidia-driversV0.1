# nvlx: Linux-NVIDIA-Driver v1.6.2.4

`nvlx` v1.6.2.4 is a narrow post-1.6.2.3 runtime-safety hotfix. It preserves the Kubernetes API surface and NVIDIA read-only boundary while making malformed state-bearing watch content fail closed by forcing a trusted relist instead of silently continuing with stale inventory assumptions.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.2.4. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.2.4 hotfixes

- **Watch corruption relist.** Malformed raw watch deliveries now invalidate GPUFleet inventory freshness and force a relist rather than being ignored while the prior snapshot remains trusted.
- **Malformed state-object fencing.** ADDED, MODIFIED, and DELETED events with invalid GPUFleet identity metadata force a relist and cannot advance the watch cursor or enter reconciliation.
- **Cursor preservation.** Corrupt state-bearing watch content cannot advance `last_resource_version`; the runtime rebuilds from a fresh list snapshot instead.
- **Unknown-event compatibility.** Unknown future watch event types remain ignorable so forward-compatible server extensions do not automatically trigger relist churn.
- **BOOKMARK boundary retained.** Malformed BOOKMARK metadata remains non-fatal and cannot replace the existing cursor because BOOKMARK carries no GPUFleet object-state mutation.
- **Inventory continuity retained.** Clean EOF, 410 relist, reconnect, watch errors, exceptions, malformed replacement lists, and shutdown continue to clear `inventory_fresh`.
- **Leadership proof separation retained.** Lease freshness remains independent from inventory continuity; readiness requires both proofs.
- **Prior safeguards retained.** Immediate leadership invalidation on API loss, Lease clock-skew fencing, timezone-aware Lease freshness, 20-second Kubernetes watch lifetime, 25-second watch socket timeout, conflict-safe status/finalizer recomputation, UID-bound mutation verification, token-file auth, opaque resourceVersion semantics, bounded watch cache, and verified Lease writes remain active.

## Safety invariants

1. Malformed state-bearing watch content cannot be ignored while inventory remains trusted.
2. A malformed ADDED, MODIFIED, or DELETED object forces a full relist before readiness can become true again.
3. Corrupt watch content cannot advance the stored watch cursor.
4. Unknown future event types remain forward-compatible and are not treated as corruption by default.
5. Malformed BOOKMARK metadata cannot poison the cursor and does not imply lost object state.
6. `inventory_fresh` still represents an active validated list/watch continuity window.
7. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
8. Conflict retries remain bounded and leadership-fenced.
9. NVIDIA resources remain read-only in v1.6.2.4.
10. All v0.1-v1.6.2.3 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay, UID-integrity, Lease-CAS, leadership-freshness and inventory-continuity safeguards remain in force.
