# nvlx: Linux-NVIDIA-Driver v1.6.6.4

`nvlx` v1.6.6.4 closes the next logical gap in the runtime-owned typed readiness contract: `leader` now represents effective leadership and cannot remain true while the API is unreachable or the controller is terminating.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.4 effective-leadership domain closure

- **Effective leadership is now logically constrained.** Typed `leader=True` requires `api_reachable=True` and `terminating=False`.
- **The live runtime normalizes torn captures toward safety.** `runtime_v1664` converts a post-evaluation leader observation to false when API reachability is lost or termination is active, and also clears captured leadership freshness/controller readiness in the diagnosis.
- **Normalization does not rewrite runtime state.** The diagnosis is frozen conservatively without mutating the underlying stats object during observability reads.
- **The live HTTP adapter independently enforces the same invariant.** `http_v1664` guards typed readiness and nested typed metrics diagnoses from custom runtimes before they enter the established HTTP presentation layer.
- **Contradictory typed readiness fails closed.** `/readyz` returns the existing `503 not ready` response without falling back to legacy state.
- **Contradictory typed metrics remain contained.** `/metrics` returns the existing static `500 metrics unavailable` response.
- **Legacy compatibility remains deliberate.** Runtimes without typed diagnosis methods continue through the historical fallback unchanged.
- **The live operator now uses `runtime_v1664` and `http_v1664`.** v1.6.6.3 logical readiness validation, v1.6.6.2 metric value-domain validation, and v1.6.6.1 strict typing remain inherited.
- **Prometheus and HTTP transport contracts are unchanged for valid diagnoses.** Metric names, HELP/TYPE metadata, ordering, `Server: nvlx`, no-store caching, byte-accurate framing, and exporter fault containment are preserved.
- **Checkpoint semantics are unchanged.** Receipt proof, canonical digest validation, ambiguity recovery, reconciliation accounting, rollback fencing, replay floors, and Lease-epoch behavior are untouched.
- **No RBAC expansion.** This release changes typed diagnosis validation, live HTTP guarding, operator wiring, tests, package metadata, CI, and documentation only.

## Effective leadership contract

The typed observability boundary now treats `leader` as an effective serving-state assertion rather than a stale Lease cache bit:

`leader=True` implies API reachability and non-termination.

The existing v1.6.6.3 implication remains:

`leadership_fresh=True` implies API reachability, effective leadership, and non-termination.

And controller readiness remains one-way fail-safe:

`controller_ready=True` implies every exported serving gate passes.

The live runtime may downgrade torn observations, but it never upgrades authoritative readiness or leadership.

## Safety invariants

1. Typed readiness fields remain exact Python `bool` values.
2. `leader=True` requires API reachability and non-termination.
3. `leadership_fresh=True` requires API reachability, effective leadership, and non-termination.
4. `controller_ready=True` requires every exported serving gate to pass.
5. Built-in diagnosis normalization only downgrades contradictory observations.
6. Observability normalization does not mutate the runtime stats object.
7. Contradictory typed readiness does not trigger legacy fallback.
8. Contradictory nested typed readiness does not reach Prometheus rendering.
9. Legacy runtimes without diagnosis methods retain their established compatibility behavior.
10. v1.6.6.2 typed metric nonnegative and relational invariants remain unchanged.
11. v1.6.6.1 strict diagnosis type validation remains unchanged.
12. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
13. No new Kubernetes mutation path or RBAC permission is introduced.
14. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.4.
