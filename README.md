# nvlx: Linux-NVIDIA-Driver v1.5.1

`nvlx` v1.5.1 is a patch-hardening release for the live Kubernetes operator introduced in 1.5. It tightens watch cursor safety, retry configuration, and controller field-ownership parsing without changing the approval-bound execution model.

> [!IMPORTANT]
> The operator still owns only its status fields and protective finalizer. Driver/GPU Operator changes remain subject to approval, maintenance, preflight, rollout, circuit, health/SLO, PSIRT, rollback and audit gates.

## v1.5.1 fixes

- **Watch cursor validation.** `ADDED`, `MODIFIED`, `DELETED`, and `BOOKMARK` events now require a non-empty `resourceVersion`; missing cursors force a relist instead of reconciling from ambiguous state.
- **Retry-bound validation.** Invalid base delay, maximum delay, and retry-count configurations are rejected instead of creating undefined backoff behavior.
- **Explicit dead-letter reason.** Retry exhaustion now carries a stable `retry budget exhausted` reason for status/event reporting.
- **Ownership parser hardening.** Leading/trailing dots, repeated separators, and bracket/index syntax are denied rather than normalized into controller-owned fields.
- **Regression coverage.** Tests cover empty cursors, malformed ownership paths, invalid retry bounds, and operator relisting on missing resource versions.
- **1.5 retained.** Optimistic status patching, bounded workqueues, live reconciliation planning, readiness/liveness checks, `GPUFleet` CRD, status conditions, finalizers, Events API and admission policy remain unchanged.

## Safety invariants

1. A watch event cannot advance reconciliation without a valid cursor.
2. Expired/error watches and missing resource versions relist.
3. Malformed field paths never gain controller ownership by normalization.
4. Retry-loop configuration must remain bounded and internally consistent.
5. Retry exhaustion stops automatic progression and requires operator review.
6. All v0.1-v1.5 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM and provenance safeguards remain in force.
