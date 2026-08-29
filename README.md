# nvlx: Linux-NVIDIA-Driver v1.5.5

`nvlx` v1.5.5 is a fifth stabilization patch for the live Kubernetes operator. It hardens leadership handoff by binding mutation authority to an exact lease holder, fencing epoch, and Lease `resourceVersion`, while preserving the existing duplicate-event, retry, finalizer, shutdown, approval, rollback and security gates.

> [!IMPORTANT]
> A controller that loses leadership is no longer permitted to finish controller-owned Kubernetes writes using stale authority. Leadership loss removes mutation readiness immediately and forces the old leader into fenced drain/standby behavior.

## v1.5.5 fixes

- **Leadership fencing token.** Mutation authority can be bound to the exact lease holder, leadership epoch and Lease `resourceVersion` observed before execution.
- **Stale-leader rejection.** A holder, epoch or Lease `resourceVersion` change invalidates the token and returns a `fence` decision.
- **Lease freshness.** Even an otherwise matching token is rejected when the Lease is stale.
- **Operator mutation gate.** Internal reconciliation can return `fenced` before reconcile/status mutation when leadership authority has changed.
- **Handoff drain semantics.** Leadership loss during an active mutation becomes `fence-drain`; once no mutation remains, the old replica becomes standby.
- **Regression coverage.** Tests cover exact-token success, holder/epoch/resourceVersion handoff, stale leases, fenced operator plans and handoff drain behavior.
- **1.5.4 retained.** Duplicate-event suppression, deterministic bounded retry jitter, ordered finalization, stale-generation guards and status-write idempotency remain active.

## Safety invariants

1. Mutation authority is valid only for the exact observed Lease holder, fencing epoch and Lease `resourceVersion`.
2. Leadership loss blocks all subsequent controller-owned mutation writes from the old leader.
3. A stale Lease cannot authorize mutation.
4. In-flight work on a lost leader drains under a fence and cannot regain mutation authority without a new valid token.
5. Standby replicas remain unable to mutate fleet state.
6. All v0.1-v1.5.4 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM and provenance safeguards remain in force.
