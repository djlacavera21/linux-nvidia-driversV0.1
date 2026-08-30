# nvlx: Linux-NVIDIA-Driver v1.6.4.8

`nvlx` v1.6.4.8 makes each readiness/metrics observation internally consistent by evaluating the authoritative runtime readiness contract before capturing the individual diagnostic gates exported in the same HTTP response.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.4.8 atomic readiness snapshot consistency

- **Authoritative readiness is evaluated first.** `_readiness_snapshot()` now calls the runtime readiness contract before observing API, leadership, inventory, preflight, checkpoint and termination diagnostics.
- **One scrape no longer mixes pre- and post-readiness state.** If `runtime.ready()` refreshes or invalidates cached Lease leadership, checkpoint safety or other fail-closed state, the remaining gauges are captured from the resulting state.
- **Leadership telemetry stays coherent.** `nvlx_controller_leader`, `nvlx_controller_leadership_fresh` and `nvlx_controller_ready` now reflect the same post-evaluation state within a scrape.
- **Checkpoint telemetry stays coherent.** `nvlx_nvidia_checkpoint_ready` is observed after the authoritative readiness call, avoiding a stale checkpoint-ready value when readiness evaluation changes checkpoint state.
- **Exceptions remain fail closed.** A readiness exception still produces `nvlx_controller_ready 0`, and diagnostic gates are then observed from any fail-closed state transition already applied by the runtime.
- **No readiness-policy change.** The existing runtime `ready()` method remains authoritative; this release changes observation order only.
- **Prometheus exposition remains unchanged.** Stable HELP metadata, correct counter/gauge TYPE metadata, deterministic ordering and UTF-8 text format from v1.6.4.7 remain intact.
- **No checkpoint protocol change.** Unified transactions, replay-floor fencing, readback verification, idempotent acknowledgement handling and Lease-epoch validation are unchanged.
- **No RBAC expansion.** The release changes only HTTP readiness snapshot ordering, regression coverage and packaging.

## Safety invariants

1. The runtime's complete readiness contract remains the authoritative serving decision.
2. Diagnostic gates are observed only after that authoritative readiness evaluation completes or fails closed.
3. A single `/metrics` response cannot intentionally combine a pre-readiness Lease/checkpoint observation with post-readiness controller state.
4. Readiness exceptions remain fail closed.
5. Metric names, HELP text, TYPE metadata and numeric normalization remain compatible with v1.6.4.7.
6. Checkpoint persistence, sequence, replay, epoch, readback and idempotency semantics are unchanged.
7. No new Kubernetes mutation path or RBAC permission is introduced.
8. NVIDIA driver/GPU Operator resources remain read-only in v1.6.4.8.
