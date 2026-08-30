# nvlx: Linux-NVIDIA-Driver v1.6.6.3

`nvlx` v1.6.6.3 closes the logical consistency gap in the runtime-owned typed readiness contract. Typed diagnoses can no longer claim that the controller is ready while simultaneously reporting a failed exported serving gate.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.3 readiness logical-domain validation

- **Typed readiness is now logically self-consistent.** `controller_ready=True` requires API reachability, effective leadership, fresh leadership proof, fresh inventory, NVIDIA preflight readiness, checkpoint readiness, and non-termination.
- **Fresh leadership is internally constrained.** `leadership_fresh=True` requires API reachability, effective leadership, and non-termination.
- **The live runtime fails safe on torn post-evaluation captures.** If authoritative `ready()` succeeds but an exported gate changes before the diagnosis is frozen, `runtime_v1663` downgrades the captured `controller_ready` value to `False`; it never upgrades a failed authoritative decision.
- **Built-in diagnosis objects validate the same logical domain.** `runtime_v1663.ReadinessDiagnosis` rejects contradictory typed readiness combinations at construction.
- **HTTP independently enforces the same rules.** Custom runtimes that opt into `readiness_diagnosis()` or nested typed metrics diagnoses cannot bypass the logical-domain contract with diagnosis-shaped objects.
- **Contradictory typed readiness fails closed.** `/readyz` returns the established `503 not ready` response and never falls back to legacy live state once a typed provider has opted in.
- **Contradictory typed metrics remain fault-contained.** `/metrics` returns the established static `500 metrics unavailable` response when its nested readiness diagnosis is contradictory.
- **Legacy compatibility is unchanged.** Runtimes without diagnosis methods continue through the historical fallback without the new typed-only logical validation.
- **The live operator now uses `runtime_v1663`.** v1.6.6.2 metric value-domain validation and v1.6.6.1 strict bool/int typing remain inherited by the current runtime.
- **Prometheus and HTTP transport contracts are unchanged for valid diagnoses.** Metric names, HELP/TYPE metadata, ordering, `Server: nvlx`, no-store caching and byte-accurate framing are preserved.
- **Checkpoint semantics are unchanged.** Receipt proof, canonical digest validation, transport-ambiguity recovery, reconciliation accounting, rollback fencing, replay floors and Lease-epoch behavior are untouched.
- **No RBAC expansion.** This release changes readiness diagnosis validation, HTTP typed adaptation, live runtime wiring, tests, package metadata and documentation only.

## Logical readiness contract

The typed readiness boundary now treats `controller_ready` as a summary assertion over the exported serving gates rather than an unrelated boolean. A typed provider may be not-ready for additional internal reasons, so the implication is deliberately one-way:

`controller_ready=True` implies every exported serving gate passes.

The reverse is not required. This preserves room for future internal readiness gates without changing the typed schema.

Fresh leadership has its own narrower implication:

`leadership_fresh=True` implies API reachability, effective leadership, and non-termination.

For the built-in runtime, any post-evaluation drift that would violate the first implication is resolved toward not-ready before the diagnosis is returned.

## Safety invariants

1. Typed readiness fields remain exact Python `bool` values.
2. `controller_ready=True` requires `api_reachable`, `leader`, `leadership_fresh`, `inventory_fresh`, `nvidia_preflight_ready`, and `checkpoint_ready` to be true and `terminating` to be false.
3. `leadership_fresh=True` requires API reachability, effective leadership, and non-termination.
4. The built-in runtime may downgrade a torn `controller_ready=True` capture to false but never upgrades authoritative readiness.
5. Contradictory typed readiness does not trigger legacy live-state fallback.
6. Contradictory nested typed readiness does not reach Prometheus rendering.
7. Legacy runtimes without diagnosis methods retain their established compatibility behavior.
8. v1.6.6.2 typed metric nonnegative and relational invariants remain unchanged.
9. v1.6.6.1 strict diagnosis type validation remains unchanged.
10. v1.6.6 single authoritative readiness evaluation and no-double-checkpoint evaluation remain unchanged.
11. All v1.6.5.x checkpoint receipt, reconciliation and persistence semantics remain unchanged.
12. No new Kubernetes mutation path or RBAC permission is introduced.
13. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.3.
