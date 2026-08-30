# nvlx: Linux-NVIDIA-Driver v1.6.4.4

`nvlx` v1.6.4.4 aligns Prometheus readiness telemetry with the full compositional readiness contract restored in v1.6.4.3.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.4.4 readiness telemetry parity

- **Full controller readiness is now exported.** `/metrics` adds `nvlx_controller_ready`, using the same runtime readiness evaluator as `/readyz`.
- **Checkpoint readiness remains separate.** `nvlx_nvidia_checkpoint_ready` continues to report only the persisted NVIDIA checkpoint gate, so operators can distinguish checkpoint health from overall controller readiness.
- **Lease freshness is reflected in metrics.** If the Lease leadership proof expires, the full readiness gauge becomes `0` and the existing leader gauge reflects the fail-closed invalidation performed by the established runtime readiness chain.
- **NVIDIA preflight failures are visible as controller unready.** A failed preflight can now produce `nvlx_controller_ready 0` while `nvlx_nvidia_checkpoint_ready` remains `1`, accurately identifying that the checkpoint is safe but the controller cannot serve.
- **Checkpoint restore/stale-epoch failures remain visible.** When checkpoint safety itself blocks readiness, both the full controller-ready gauge and checkpoint-ready gauge are `0`.
- **One fail-safe evaluator backs both surfaces.** `/readyz` and `/metrics` now share the same wrapper around `runtime.ready()`, and exceptions resolve to unready rather than leaking an HTTP error or optimistic metric.
- **Older runtimes remain compatible.** If a runtime does not implement `ready()`, the health server retains the existing API/leader/inventory/termination fallback.
- **No persistence protocol change.** v1.6.4 unified transactions, replay-floor fencing, independent readback verification, ambiguous-write reconciliation, idempotent acknowledgements and checkpoint-aware readiness remain unchanged.
- **No RBAC expansion.** The new gauge is derived entirely from in-memory controller state.

## Readiness metrics

- `nvlx_controller_ready` — full controller readiness, matching `/readyz`.
- `nvlx_nvidia_checkpoint_ready` — checkpoint-only readiness gate.

## Safety invariants

1. `nvlx_controller_ready` may be `1` only when the runtime's complete readiness contract passes.
2. A safe checkpoint does not imply that the controller is ready; Lease freshness, NVIDIA preflight, API reachability, inventory continuity and termination gates still apply.
3. A checkpoint that is un-restored or stale for the active Lease epoch cannot coexist with full controller readiness.
4. Readiness evaluator exceptions fail closed on both `/readyz` and `/metrics`.
5. Metrics evaluation preserves the established fail-closed leadership invalidation behavior.
6. Checkpoint persistence, sequence, replay, epoch, readback and idempotency semantics are unchanged.
7. No new Kubernetes mutation path or RBAC permission is introduced.
8. NVIDIA driver/GPU Operator resources remain read-only in v1.6.4.4.
