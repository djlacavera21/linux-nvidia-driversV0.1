# nvlx: Linux-NVIDIA-Driver v1.6.4.7

`nvlx` v1.6.4.7 completes the Prometheus text exposition metadata hardening started in v1.6.4.6 by adding stable HELP descriptions and an explicit UTF-8 content type while preserving all existing metric names, values and types.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.4.7 Prometheus exposition metadata hardening

- **Every metric is self-describing.** `/metrics` now emits one `# HELP` line for every exported sample.
- **HELP and TYPE ordering is deterministic.** Every metric is rendered as `HELP`, then `TYPE`, then the sample value.
- **Prometheus types remain correct.** Cumulative totals continue to use `counter`; readiness, health, rollout, checkpoint sequence and Lease epoch values remain `gauge`.
- **Metric names and numeric values are unchanged.** Existing PromQL queries and dashboards retain the same series names and sample semantics.
- **The HTTP content type is explicit.** `/metrics` now returns `text/plain; version=0.0.4; charset=utf-8` and encodes the body as UTF-8.
- **HELP metadata is static and bounded.** Descriptions are fixed strings with no runtime labels, identities, checkpoint contents or other dynamic data.
- **Normalization behavior is unchanged.** Invalid or negative numeric telemetry still normalizes to zero as before.
- **Structured readiness remains intact.** The v1.6.4.5 gate-by-gate readiness diagnostics and v1.6.4.4 `/readyz` parity are unchanged.
- **No checkpoint protocol change.** Unified transactions, replay-floor fencing, readback verification, idempotent acknowledgement handling and Lease-epoch validation remain unchanged.
- **No RBAC expansion.** This release changes only telemetry exposition metadata, HTTP response metadata, tests and packaging.

## Prometheus exposition contract

For each exported metric, nvlx now emits:

1. exactly one non-empty `# HELP` declaration;
2. exactly one `# TYPE` declaration;
3. exactly one sample line in the existing deterministic order.

Cumulative `*_total` metrics remain counters. Point-in-time state, readiness, sequence and epoch metrics remain gauges.

## Safety invariants

1. Metric names and numeric values remain compatible with v1.6.4.6.
2. Counter/gauge type corrections from v1.6.4.6 remain unchanged.
3. HELP strings contain no dynamic runtime or checkpoint data.
4. Telemetry metadata cannot alter readiness, leadership, checkpoint persistence or mutation behavior.
5. `/metrics` remains Prometheus text format version 0.0.4 and now explicitly declares UTF-8.
6. Checkpoint persistence, sequence, replay, epoch, readback and idempotency semantics are unchanged.
7. No new Kubernetes mutation path or RBAC permission is introduced.
8. NVIDIA driver/GPU Operator resources remain read-only in v1.6.4.7.
