# nvlx: Linux-NVIDIA-Driver v1.6.4.1

`nvlx` v1.6.4.1 exposes the unified NVIDIA checkpoint transaction state added across v1.6.3.5-v1.6.4 through the controller's Prometheus `/metrics` endpoint.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.4.1 checkpoint telemetry integration

- **Unified checkpoint metrics are now exported.** `/metrics` exposes successful writes, proven idempotent acknowledgements, rollback detections, transaction mismatches, persistence failures, restore attempts and restore successes.
- **Current checkpoint position is visible.** The runtime's accepted checkpoint sequence and Lease transition epoch are exported as gauges.
- **No persistence semantics change.** v1.6.4's unified transaction gate remains unchanged; this release only exposes its runtime state for operations and alerting.
- **Older runtimes remain compatible.** The HTTP metrics path reads checkpoint fields with zero-valued fallbacks, so runtime variants that predate a counter do not break the metrics endpoint.
- **Renderer compatibility is preserved.** All existing `controller_metrics.render()` arguments remain valid and every new checkpoint metric parameter is optional with a zero default.
- **Malformed metric inputs fail safe.** Numeric metric values are normalized to non-negative integers instead of propagating invalid values into the Prometheus response.
- **Existing controller metrics are unchanged.** Leadership, reconcile, approval, rollback, circuit, rollout, execution, stale-preflight and canary metrics retain their previous names.
- **No RBAC or Kubernetes resource change.** Metrics are produced from in-memory runtime state and require no additional API permissions.

## New metrics

- `nvlx_nvidia_checkpoint_writes_total`
- `nvlx_nvidia_checkpoint_idempotent_acks_total`
- `nvlx_nvidia_checkpoint_rollbacks_total`
- `nvlx_nvidia_checkpoint_transaction_mismatches_total`
- `nvlx_nvidia_checkpoint_failures_total`
- `nvlx_nvidia_checkpoint_restore_attempts_total`
- `nvlx_nvidia_checkpoint_restore_successes_total`
- `nvlx_nvidia_checkpoint_sequence`
- `nvlx_nvidia_checkpoint_epoch`

## Safety invariants

1. Telemetry cannot alter checkpoint state or acknowledge a checkpoint.
2. Missing runtime telemetry attributes resolve to zero instead of breaking `/metrics`.
3. Existing metric names and renderer call sites remain backward compatible.
4. Sequence rollback, equal-sequence proof, Lease epoch, replay-floor, readback and transaction-state fences remain unchanged.
5. Checkpoint restore and write failure behavior remains fail-closed.
6. No new Kubernetes mutation path or RBAC permission is introduced.
7. NVIDIA driver/GPU Operator resources remain read-only.
8. v1.6.4 unified checkpoint transactions remain the sole durability path.
