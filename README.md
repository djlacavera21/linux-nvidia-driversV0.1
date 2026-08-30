# nvlx: Linux-NVIDIA-Driver v1.6.4.6

`nvlx` v1.6.4.6 corrects Prometheus metric type metadata so cumulative totals are exported as counters while readiness, health, checkpoint sequence and Lease epoch state remain gauges.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.4.6 Prometheus type correctness

- **Cumulative totals are counters.** Reconcile totals, reconcile failures, preflight-stale events, checkpoint writes, idempotent acknowledgements, rollbacks, transaction mismatches, checkpoint failures, restore attempts and restore successes now emit `# TYPE ... counter`.
- **Instantaneous state remains gauge data.** Controller readiness, API reachability, Lease freshness, inventory freshness, termination state, NVIDIA preflight readiness, checkpoint readiness, pending approvals, rollback-required state, rollout slots, canary wave, checkpoint sequence and checkpoint Lease epoch remain gauges.
- **Metric names are unchanged.** Existing dashboards and queries can continue using the same series names.
- **Metric values are unchanged.** The release changes Prometheus metadata only; runtime counters and readiness values retain their existing meaning and normalization behavior.
- **HTTP telemetry is covered end-to-end.** Regression tests validate the actual `/metrics` surface as well as the renderer.
- **One declaration per metric.** Every emitted sample has exactly one corresponding `# TYPE` declaration.
- **No readiness-policy change.** Structured readiness diagnostics from v1.6.4.5 and readiness parity from v1.6.4.4 remain intact.
- **No checkpoint protocol change.** Unified transactions, sequence fencing, replay protection, readback verification, idempotent acknowledgement handling and Lease-epoch validation are unchanged.
- **No RBAC expansion.** The release changes only telemetry formatting and tests.

## Prometheus type rules

### Counters

- `nvlx_controller_reconcile_total`
- `nvlx_controller_reconcile_failures_total`
- `nvlx_controller_preflight_stale_total`
- `nvlx_nvidia_checkpoint_writes_total`
- `nvlx_nvidia_checkpoint_idempotent_acks_total`
- `nvlx_nvidia_checkpoint_rollbacks_total`
- `nvlx_nvidia_checkpoint_transaction_mismatches_total`
- `nvlx_nvidia_checkpoint_failures_total`
- `nvlx_nvidia_checkpoint_restore_attempts_total`
- `nvlx_nvidia_checkpoint_restore_successes_total`

### Gauges

All exported point-in-time controller, readiness, rollout, checkpoint sequence and Lease epoch values remain gauges.

## Safety invariants

1. Metric names and numeric values remain compatible with v1.6.4.5.
2. Cumulative `*_total` series listed above are declared as Prometheus counters.
3. Instantaneous readiness and state series remain gauges.
4. Type metadata cannot alter runtime readiness, checkpoint persistence or controller mutation behavior.
5. Structured readiness diagnostics and `/readyz` parity remain unchanged.
6. Checkpoint persistence, sequence, replay, epoch, readback and idempotency semantics are unchanged.
7. No new Kubernetes mutation path or RBAC permission is introduced.
8. NVIDIA driver/GPU Operator resources remain read-only in v1.6.4.6.
