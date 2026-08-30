# nvlx: Linux-NVIDIA-Driver v1.6.4.9

`nvlx` v1.6.4.9 closes the remaining leadership-specific consistency gap in readiness telemetry by capturing effective leader state inside the same post-readiness snapshot used for controller readiness and Lease freshness.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.4.9 leadership snapshot closure

- **Leader state is now part of `ReadinessSnapshot`.** The effective `stats.leader` value is captured once after authoritative readiness evaluation.
- **`/metrics` no longer rereads mutable leadership state.** `nvlx_controller_leader` is rendered from `snapshot.leader` rather than a later direct `stats.leader` access.
- **Lease freshness uses the captured gate set.** API reachability, leader state and termination state are passed into the freshness observer so it does not independently reread those mutable fields.
- **Leadership telemetry is closed over one observation.** `nvlx_controller_ready`, `nvlx_controller_leader` and `nvlx_controller_leadership_fresh` now derive from one post-readiness gate capture.
- **Legacy runtimes are closed too.** Runtimes without a custom `ready()` method have API, leader, inventory and termination state captured once and use those same values to compute compatibility readiness.
- **Authoritative readiness remains first for modern runtimes.** Any fail-closed leadership invalidation performed by `runtime.ready()` still occurs before the snapshot is captured.
- **No readiness-policy change.** The release changes observation closure only; it does not add or remove a serving gate.
- **Prometheus exposition remains unchanged.** HELP metadata, counter/gauge TYPE metadata, deterministic ordering and UTF-8 text format remain intact.
- **No checkpoint protocol change.** Persistence, replay-floor fencing, sequence checks, readback verification, idempotent acknowledgement handling and Lease-epoch validation are unchanged.
- **No RBAC expansion.** This release changes only health/metrics observation behavior, tests, documentation and packaging.

## Safety invariants

1. Runtime `ready()` remains authoritative whenever present.
2. Effective leader state is captured after authoritative readiness evaluation and read once per snapshot.
3. Lease freshness diagnostics consume that same captured API/leader/termination state.
4. `/metrics` renders the captured leader value and does not intentionally reread mutable leadership state.
5. Legacy readiness fallback computes from one captured generic gate set.
6. Readiness exceptions remain fail closed.
7. Checkpoint persistence, sequence, replay, epoch, readback and idempotency semantics are unchanged.
8. No new Kubernetes mutation path or RBAC permission is introduced.
9. NVIDIA driver/GPU Operator resources remain read-only in v1.6.4.9.
