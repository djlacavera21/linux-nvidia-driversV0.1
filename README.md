# nvlx: Linux-NVIDIA-Driver v1.6.4.2

`nvlx` v1.6.4.2 makes Kubernetes readiness checkpoint-aware so the controller cannot advertise `/readyz` while persisted NVIDIA continuity state is still un-restored or stale for the active Lease epoch.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.4.2 checkpoint-aware readiness

- **Readiness now includes checkpoint safety.** Generic controller readiness must still have API reachability, active leadership, fresh inventory and a non-terminating runtime.
- **Configured checkpoint stores must be restored.** If a Lease-backed NVIDIA continuity checkpoint store is configured, `/readyz` remains unavailable until atomic checkpoint restore has completed successfully.
- **Stale Lease epochs block readiness.** A checkpoint inherited from a previous Lease transition keeps the controller unready until the existing two-observation takeover revalidation clears `nvidia_checkpoint_epoch_stale`.
- **Recovered controllers become ready again.** Historical checkpoint failure counters do not permanently poison readiness after state has been restored and revalidated.
- **No-store runtimes remain compatible.** Runtimes without a checkpoint store retain the previous controller readiness behavior.
- **Checkpoint health is exported.** `/metrics` adds `nvlx_nvidia_checkpoint_ready`, with `1` only when the checkpoint readiness gate is satisfied.
- **Metrics failures fail safe.** If checkpoint readiness evaluation raises while rendering metrics, the checkpoint-ready gauge resolves to `0` rather than breaking `/metrics`.
- **No checkpoint protocol change.** v1.6.4 unified transactions, v1.6.3.9 idempotent acknowledgement fencing, v1.6.3.8 reconciliation, readback verification, replay-floor protection and atomic restore remain unchanged.
- **No RBAC expansion.** Readiness and telemetry use in-memory runtime state only.

## Safety invariants

1. A controller with a configured checkpoint store is not ready until checkpoint restore has completed.
2. A stale Lease-transition checkpoint cannot coexist with a ready controller.
3. Generic API, leadership, inventory-freshness and termination readiness gates remain mandatory.
4. Historical failure counters do not block readiness after successful recovery.
5. Readiness evaluation cannot mutate checkpoint state or acknowledge a checkpoint.
6. Sequence rollback, equal-sequence proof, Lease epoch, replay-floor, readback and transaction-state fences remain unchanged.
7. No new Kubernetes mutation path or RBAC permission is introduced.
8. NVIDIA driver/GPU Operator resources remain read-only in v1.6.4.2.
