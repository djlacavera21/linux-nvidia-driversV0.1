# nvlx: Linux-NVIDIA-Driver v1.5.2

`nvlx` v1.5.2 is a second stabilization patch for the live Kubernetes operator. It closes race-condition gaps around conflict responses, delete events, retry exhaustion, finalizer inputs, and leader-lease readiness without expanding the API surface.

> [!IMPORTANT]
> The operator remains approval-bound and fail-closed. It still owns only its status fields and protective finalizer; desired driver/GPU Operator state remains controlled by the existing approval, maintenance, preflight, rollout, circuit, health/SLO, PSIRT, rollback and audit gates.

## v1.5.2 fixes

- **Conflict classification.** Kubernetes `409 Conflict` now maps to relist-and-retry, `404` maps to a terminal gone state, `429`/5xx remain retryable, and other 4xx outcomes hold for operator review.
- **Delete-event safety.** A `DELETED` watch event is observed but never produces a status patch against a disappearing object.
- **Retry exhaustion propagation.** Reconcile/relist paths surface a first-class `dead-letter` action once the bounded retry budget is exhausted.
- **Finalizer validation.** Impossible negative quarantine counts are rejected rather than influencing deletion safety decisions.
- **Leader-lease readiness.** A leader with a stale lease is explicitly not ready to mutate fleet state.
- **Regression coverage.** Tests cover patch conflicts, gone objects, delete-event races, exhausted retries, invalid finalizer inputs, and stale leader leases.
- **1.5.1 retained.** Watch-cursor validation, retry-bound checks, strict field-ownership parsing, optimistic patching, bounded workqueues, `GPUFleet` CRD, status conditions, finalizers, Events API and admission policy remain active.

## Safety invariants

1. Status writes never proceed blindly after a Kubernetes conflict.
2. Deleted resources are not patched after their terminal watch event.
3. Retry exhaustion stops automatic progression and becomes an explicit dead-letter outcome.
4. Finalizer safety inputs are validated before deletion decisions are made.
5. A stale leader lease removes mutation readiness.
6. All v0.1-v1.5.1 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM and provenance safeguards remain in force.
