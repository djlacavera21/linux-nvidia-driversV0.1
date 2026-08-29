# nvlx: Linux-NVIDIA-Driver v1.2

`nvlx` v1.2 adds an **operations-control layer** above the 1.1 production controller. The goal is bounded blast radius: detect drift, freeze the facts used for approval, honor maintenance windows, prevent duplicate executions, cap concurrent disruption, trip a fleet circuit breaker, and choose recovery deterministically.

> [!IMPORTANT]
> v1.2 does not make disruptive GPU changes autonomous. Existing plan fingerprints, approvals, leader election, compatibility, rollback, health, SLO, PSIRT and quarantine gates remain mandatory.

## v1.2 operations controls

- **Change windows.** UTC maintenance windows gate disruptive work; emergency override is explicit and visible.
- **Circuit breaker.** Repeated failures stop fleet progression; a security-gate failure opens the breaker immediately.
- **Execution idempotency.** Deterministic execution keys prevent replaying the same plan/target/generation after completion.
- **Rollout budgets.** Concurrent unavailable GPU nodes are capped before another rollout slot is granted.
- **Desired-state drift.** Driver, GPU Operator, MIG, DRA, Fabric Manager and Network Operator drift is classified as disruptive and requires approval.
- **Preflight snapshots.** Approval-time facts are fingerprinted and can be revalidated immediately before execution so stale approvals do not act on changed fleet conditions.
- **Deterministic recovery.** A verified first-failure rollback may be automatic; repeated failures, uncertain state and security failures fail closed to operator review/quarantine.
- **1.1 retained.** Approval TTL/revocation, tamper-evident audit chains, state migrations, leader-aware reconciliation, metrics, execution records and Kubernetes HA/RBAC remain active.

## Production execution model

```text
OBSERVE DESIRED + ACTUAL STATE
          |
          v
       DRIFT?
          | no -> NOOP
          v
PREFLIGHT SNAPSHOT + COMPATIBILITY
          |
          v
PLAN + FINGERPRINT + APPROVAL
          |
          v
CHANGE WINDOW + LEADER + FRESH PREFLIGHT
          |
          v
IDEMPOTENCY + ROLLOUT BUDGET + CIRCUIT BREAKER
          |\
          | fail -> HOLD / QUARANTINE
          v
       EXECUTE
          |
          v
HEALTH / SLO / SECURITY VALIDATION
          |\
          | fail -> DETERMINISTIC RECOVERY
          v
        AUDIT
```

## Safety invariants

1. Security failures open the circuit breaker immediately.
2. Stale preflight facts invalidate execution eligibility.
3. Completed idempotency keys cannot be executed twice.
4. Rollout disruption cannot exceed the configured unavailable-node budget.
5. Disruptive desired-state drift requires approval.
6. Automatic rollback is limited to a bounded first failure with verified rollback availability.
7. Uncertain observed state fails closed.
8. Emergency change-window override is explicit; it does not bypass security, approval, leader, compatibility, health or rollback gates.
9. All v0.1-v1.1 safety invariants remain in force.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```
