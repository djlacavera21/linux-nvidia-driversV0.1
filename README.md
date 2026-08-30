# nvlx: Linux-NVIDIA-Driver v1.6.4.5

`nvlx` v1.6.4.5 adds structured readiness diagnostics so operators can see which individual safety gate is blocking the full controller readiness result introduced in v1.6.4.4.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.4.5 structured readiness diagnostics

- **Readiness is now observable gate-by-gate.** `/metrics` exposes API reachability, Lease leadership freshness, inventory continuity, NVIDIA preflight readiness, checkpoint readiness and termination state independently.
- **The composite result remains authoritative.** `nvlx_controller_ready` still comes from the runtime's complete readiness contract and remains the metric counterpart to `/readyz`.
- **Lease freshness is observed independently.** A non-mutating observation of the timestamped Lease proof is exported as `nvlx_controller_leadership_fresh`, while the established runtime readiness path retains its existing fail-closed leadership invalidation behavior.
- **Preflight and checkpoint health are distinguishable.** `nvlx_nvidia_preflight_ready` and `nvlx_nvidia_checkpoint_ready` allow a safe checkpoint, failed inventory preflight, or vice versa to be identified directly.
- **API and inventory continuity are explicit.** `nvlx_controller_api_reachable` and `nvlx_controller_inventory_fresh` expose the two continuity prerequisites without requiring inference from the composite readiness result.
- **Termination is explicit.** `nvlx_controller_terminating` becomes `1` during shutdown so an intentional readiness drop can be distinguished from a failure.
- **Older runtimes remain compatible.** Runtimes without timestamped Lease freshness, NVIDIA preflight, checkpoint readiness or a custom `ready()` method retain safe fallbacks based on their existing stats.
- **No readiness-policy change.** The release adds diagnostics around the v1.6.4.3/v1.6.4.4 contract; it does not weaken or add a serving gate.
- **No persistence or RBAC change.** Checkpoint envelopes, replay floors, sequence fencing, readback verification, idempotent acknowledgement handling and Kubernetes permissions remain unchanged.

## Readiness metrics

- `nvlx_controller_ready` — authoritative full controller readiness.
- `nvlx_controller_api_reachable` — Kubernetes API reachability gate.
- `nvlx_controller_leadership_fresh` — effective Lease leadership freshness gate.
- `nvlx_controller_inventory_fresh` — validated list/watch continuity gate.
- `nvlx_nvidia_preflight_ready` — NVIDIA inventory/preflight gate.
- `nvlx_nvidia_checkpoint_ready` — persisted continuity checkpoint gate.
- `nvlx_controller_terminating` — shutdown state; `1` means the controller is terminating.

## Safety invariants

1. `nvlx_controller_ready` remains the authoritative result and continues to match `/readyz`.
2. Diagnostic gauges cannot make an unready controller ready or bypass any runtime gate.
3. Lease freshness diagnostics use a non-mutating observation; the established runtime may still invalidate stale leadership while evaluating the authoritative readiness result.
4. A failed API, Lease, inventory, NVIDIA preflight, checkpoint or termination gate remains sufficient to keep the controller unready under the existing runtime contract.
5. Unknown legacy runtime capabilities use conservative stats-based compatibility behavior rather than raising from the health endpoint.
6. Checkpoint persistence, sequence, replay, epoch, readback and idempotency semantics are unchanged.
7. No new Kubernetes mutation path or RBAC permission is introduced.
8. NVIDIA driver/GPU Operator resources remain read-only in v1.6.4.5.
