# nvlx: Linux-NVIDIA-Driver v1.5.4

`nvlx` v1.5.4 is a fourth stabilization patch for the live Kubernetes operator. It suppresses duplicate watch delivery, adds deterministic bounded retry jitter, orders finalizer removal behind pending status writes, and adds an explicit graceful-shutdown mutation gate without expanding the CRD or control-plane API surface.

> [!IMPORTANT]
> The operator remains approval-bound and fail-closed. Desired driver and GPU Operator changes still pass through approval, maintenance, preflight, rollout, circuit, health/SLO, PSIRT, rollback and audit gates.

## v1.5.4 fixes

- **Duplicate event suppression.** A repeated `(event type, resourceVersion, generation)` delivery is fingerprinted and becomes `event-noop` before reconciliation or status mutation.
- **Deterministic retry jitter.** Retry delays keep the bounded exponential policy while adding stable per-event jitter to reduce synchronized retry bursts across replicas.
- **Finalizer/status ordering.** Protective finalizer removal waits until any pending status write is complete, preventing deletion from racing the final observable status update.
- **Graceful shutdown gate.** Terminating replicas stop accepting new work, drain an active mutation if one exists, then transition to exit only after mutation state is clear.
- **Regression coverage.** Tests cover duplicate event delivery, deterministic bounded jitter, pending-status finalization, and shutdown drain/exit sequencing.
- **1.5.3 retained.** Stale-generation guards, logical status-write idempotency, normalized patch response handling, delete-event safety, bounded dead-letter behavior and leader-lease readiness remain active.

## Safety invariants

1. The same watch event cannot trigger the same reconcile path twice after its fingerprint is recorded.
2. Retry jitter remains deterministic and bounded by the configured maximum delay.
3. Finalizer removal cannot overtake a pending controller-owned status write.
4. A terminating replica cannot accept new mutation work.
5. Active mutation is drained before shutdown exit is considered safe.
6. All v0.1-v1.5.3 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM and provenance safeguards remain in force.
