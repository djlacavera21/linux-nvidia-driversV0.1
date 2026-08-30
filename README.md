# nvlx: Linux-NVIDIA-Driver v1.6.6.2

`nvlx` v1.6.6.2 extends the runtime-owned typed observability contract with value-domain validation, so typed metrics must now be not only correctly typed but also operationally valid before they can reach Prometheus.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.2 typed telemetry value-domain validation

- **Typed metrics must be nonnegative.** Every exported reconcile/checkpoint integer in the live diagnosis contract now rejects negative values instead of relying on the Prometheus renderer to clamp them.
- **Reconcile accounting must be internally possible.** `reconcile_failures` cannot exceed `reconcile_total`.
- **Restore accounting must be internally possible.** `checkpoint_restore_successes` cannot exceed `checkpoint_restore_attempts`.
- **Reconciliation accounting must be internally possible.** `checkpoint_reconciled_commits` cannot exceed successful checkpoint writes plus proven idempotent acknowledgements.
- **The live operator now uses `runtime_v1662`.** The new runtime layer preserves v1.6.6/v1.6.6.1 diagnosis behavior and adds value-domain validation to the current typed provider.
- **HTTP independently enforces the same domain.** Custom runtimes that opt into `metrics_diagnosis()` cannot bypass nonnegative or relational invariants by returning diagnosis-shaped objects directly.
- **Malformed typed metrics remain fault-contained.** `/metrics` returns the established static `500 metrics unavailable` response and does not reread legacy runtime state.
- **Legacy compatibility remains deliberate.** Runtimes without typed diagnosis methods retain the historical exporter behavior, including nonnegative normalization for legacy numeric inputs.
- **Readiness semantics are unchanged.** v1.6.6 single authoritative readiness evaluation and no-double-checkpoint observation remain intact.
- **Prometheus and HTTP transport contracts are unchanged for valid diagnoses.** Metric names, HELP/TYPE metadata, ordering, `Server: nvlx`, no-store caching and byte-accurate framing are preserved.
- **Checkpoint semantics are unchanged.** Receipt proof, canonical digest validation, ambiguity recovery, reconciliation accounting, rollback fencing, replay floors and Lease-epoch behavior are untouched.
- **No RBAC expansion.** This release changes typed telemetry validation, live runtime wiring, HTTP diagnosis adaptation, tests, package metadata and documentation only.

## Validation boundary

The current runtime-owned metrics path now validates in two independent places:

1. `runtime_v1662.MetricsDiagnosis` validates strict integer typing inherited from v1.6.6.1, then validates nonnegative values and cross-counter relationships;
2. the HTTP adapter independently validates diagnosis-shaped objects from custom typed providers before creating the frozen Prometheus snapshot.

A typed provider that violates the contract is treated as broken and remains inside the existing exporter-failure boundary. The historical fallback is used only when a runtime does not advertise typed diagnosis methods.

## Safety invariants

1. Typed exported metrics must be exact Python `int` values and must be nonnegative.
2. `reconcile_failures <= reconcile_total`.
3. `checkpoint_restore_successes <= checkpoint_restore_attempts`.
4. `checkpoint_reconciled_commits <= checkpoint_writes + checkpoint_idempotent_acks`.
5. Invalid typed metrics do not reach Prometheus normalization or rendering.
6. Invalid typed metrics do not trigger legacy live-state fallback.
7. Legacy runtimes without diagnosis methods retain their established compatibility behavior.
8. v1.6.6.1 strict bool/int validation remains unchanged.
9. v1.6.6 single-readiness and no-double-checkpoint diagnosis semantics remain unchanged.
10. All v1.6.5.x checkpoint receipt, reconciliation and persistence semantics remain unchanged.
11. No new Kubernetes mutation path or RBAC permission is introduced.
12. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.2.
