# nvlx: Linux-NVIDIA-Driver v1.6.5.2

`nvlx` v1.6.5.2 adds first-class telemetry for checkpoint commits that were successfully recovered after a transport-ambiguous write or readback outcome.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.5.2 reconciliation telemetry

- **Recovered ambiguous commits are now observable.** The runtime tracks `nvidia_checkpoint_reconciled_commits` whenever an accepted `CheckpointCommitReceipt` is marked `reconciled=True`.
- **Prometheus exports a dedicated counter.** `nvlx_nvidia_checkpoint_reconciled_commits_total` reports successful checkpoint commits recovered after transport-ambiguous outcomes.
- **Advancing recovered writes remain normal writes.** If an ambiguous PATCH actually committed a new sequence, the operation increments both `nvlx_nvidia_checkpoint_writes_total` and `nvlx_nvidia_checkpoint_reconciled_commits_total`.
- **Non-advancing reconciled acknowledgements remain idempotent acknowledgements.** An accepted equal-sequence reconciled receipt increments both the existing idempotent-ack counter and the new reconciliation counter.
- **Rejected operations cannot inflate recovery telemetry.** Digest mismatches, rollback sequences, invalid receipts and other fail-closed outcomes do not increment the reconciliation counter.
- **Older runtimes remain scrape-compatible.** The HTTP metrics layer uses a zero fallback when the runtime does not expose the new counter.
- **Prometheus metadata remains standards-clean.** The new series has stable HELP metadata and `counter` TYPE metadata while existing HELP/TYPE/sample ordering and UTF-8 content type remain unchanged.
- **The live operator now uses the v1.6.5.2 runtime.** The v1.6.5.1 ambiguity-classifying checkpoint store remains the persistence implementation.
- **No checkpoint protocol change.** The v3 checkpoint envelope, sequence floor, per-call receipt digest, readback verification, rollback fencing and Lease-epoch rules are unchanged.
- **No RBAC expansion.** The release adds process-local accounting and telemetry only.

## New metric

`nvlx_nvidia_checkpoint_reconciled_commits_total`

This counter increases only after a reconciled receipt has passed the existing runtime acceptance checks. It is intentionally separate from `nvlx_nvidia_checkpoint_writes_total` and `nvlx_nvidia_checkpoint_idempotent_acks_total` so operators can distinguish normal persistence from transport-ambiguity recovery.

## Safety invariants

1. The reconciliation counter increments only for accepted receipts with `reconciled=True`.
2. Digest mismatches and rollback failures cannot increment reconciliation telemetry.
3. Advancing reconciled commits continue to count as successful checkpoint writes.
4. Equal-sequence reconciled commits still require `idempotent=True`, the same Lease epoch and exact per-call digest proof.
5. The v1.6.5.1 transport-versus-deterministic reconciliation eligibility rules are unchanged.
6. Checkpoint encoding, sequence-floor retention, readback verification and Lease transition semantics are unchanged.
7. Existing metric names and values retain their previous meanings.
8. Readiness, leadership snapshot closure and Prometheus exposition ordering are unchanged.
9. No new Kubernetes mutation path or RBAC permission is introduced.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.5.2.
