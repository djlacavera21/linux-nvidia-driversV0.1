# nvlx: Linux-NVIDIA-Driver v1.6.4.3

`nvlx` v1.6.4.3 restores compositional Kubernetes readiness so checkpoint safety is added on top of the existing controller, Lease-freshness, inventory-continuity and NVIDIA preflight gates instead of replacing them.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.4.3 compositional readiness restoration

- **Checkpoint readiness is now additive.** The v1.6.4.2 checkpoint gate remains required, but it is composed with the established readiness implementation inherited from earlier releases.
- **Lease leadership freshness is restored.** A cached `stats.leader=True` value is no longer enough; readiness again requires a non-expired Lease verification within `leader_fresh_seconds`.
- **Expired leadership fails closed.** When the cached Lease proof ages out, readiness becomes false and the cached leadership state is invalidated.
- **NVIDIA preflight gating is restored.** A failed or unavailable NVIDIA inventory preflight prevents readiness even if generic controller flags and checkpoint state look healthy.
- **API-loss leadership invalidation is restored.** API reachability loss clears cached leadership freshness before readiness can recover.
- **Inventory continuity and termination gates remain active.** The established watch/inventory freshness and shutdown semantics stay part of the readiness decision.
- **Checkpoint restore and Lease-epoch gates remain active.** A configured store must still be restored and must not be stale for the active Lease transition.
- **No checkpoint protocol change.** v1.6.4 unified transactions, replay fencing, readback verification, idempotent reconciliation, sequence monotonicity and checkpoint telemetry remain unchanged.
- **No RBAC expansion.** This release changes only in-memory readiness composition.

## Safety invariants

1. Checkpoint readiness can only restrict the established readiness chain; it cannot replace or weaken earlier gates.
2. A stale or expired Lease leadership proof cannot coexist with a ready controller.
3. A failed NVIDIA preflight cannot coexist with a ready controller.
4. A configured checkpoint store must be restored and current for the active Lease epoch before readiness succeeds.
5. API reachability, inventory continuity and termination gates remain mandatory.
6. Sequence rollback, equal-sequence proof, replay-floor, readback and transaction-state fences remain unchanged.
7. No new Kubernetes mutation path or RBAC permission is introduced.
8. NVIDIA driver/GPU Operator resources remain read-only in v1.6.4.3.
