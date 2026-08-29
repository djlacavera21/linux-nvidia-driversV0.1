# nvlx: Linux-NVIDIA-Driver v1.3

`nvlx` v1.3 integrates the 1.2 operations safeguards directly into the production reconciliation runtime. The controller now makes one deterministic execution decision across leadership, approval, maintenance window, fresh preflight facts, idempotency, rollout disruption budget, and fleet circuit state before disruptive work can proceed.

> [!IMPORTANT]
> v1.3 does not bypass operator control. Emergency maintenance-window override does not bypass approval, leader election, compatibility, health/SLO, PSIRT, quarantine, rollback, or audit requirements.

## v1.3 runtime integration

- **Integrated runtime gate stack.** `runtime-evaluate` combines the 1.2 controls into one fail-closed execution decision.
- **Persistent guard state.** Circuit failure count, completed execution keys, and last successful generation are atomically persisted with a versioned runtime-state contract.
- **Progressive canaries.** `canary-check` advances waves only when health, diagnostics, security, quarantine, and circuit state all permit promotion.
- **Rollback orchestration.** `rollback-plan` composes package/module restore, depmod, initramfs refresh, boot validation, and health/SLO/security revalidation without claiming unsafe live module swaps.
- **Kubernetes maintenance policy.** `maintenance-policy` renders a namespaced ConfigMap with UTC maintenance-window controls and explicit emergency override state.
- **Expanded observability.** Controller Prometheus output now includes circuit state, rollout slots, completed executions, stale-preflight count, and canary wave.
- **Idempotency CLI.** Deterministic plan/target/generation execution keys are first-class controller output.
- **1.2 retained.** Change windows, drift classification, preflight snapshots, rollout budgets, circuit breakers, deterministic recovery, and all earlier safety contracts remain active.

## Runtime model

```text
DESIRED STATE / DRIFT
        |
        v
PREFLIGHT + COMPATIBILITY + PLAN
        |
        v
APPROVAL + LEADER LEASE
        |
        v
MAINTENANCE WINDOW
        |
        v
FRESH PREFLIGHT FACTS
        |
        v
IDEMPOTENCY + ROLLOUT BUDGET + CIRCUIT BREAKER
        |\
        | blocked -> HOLD / QUARANTINE + AUDIT
        v
CANARY EXECUTION
        |
        v
HEALTH + DIAGNOSTICS + SLO + SECURITY
        |\
        | fail -> ROLLBACK ORCHESTRATION
        v
PROMOTE NEXT WAVE
```

## Controller commands

```bash
# deterministic execution identity
nvlx-controller idempotency-key <plan-fingerprint> gpu01 2

# integrated runtime decision
nvlx-controller runtime-evaluate facts.json \
  --leader --approval-valid \
  --execution-key exec-... \
  --total-nodes 20

# persistent guard state
nvlx-controller runtime-state /var/lib/nvlx/runtime.json --record-failure
nvlx-controller runtime-state /var/lib/nvlx/runtime.json --record-success exec-... --generation 2

# progressive canary promotion
nvlx-controller canary-check \
  --current-wave 0 --total-waves 3 \
  --healthy-fraction 1.0 \
  --diagnostics-passed --security-passed

# rollback and maintenance policy
nvlx-controller rollback-plan --rollback-available --failure-count 1
nvlx-controller maintenance-policy --start-hour 2 --end-hour 5
```

## Safety invariants

1. Integrated runtime execution is denied if any required gate fails.
2. Security failure opens the circuit path to quarantine rather than ordinary continuation.
3. Completed execution keys are replay-protected across controller restarts when runtime state is persisted.
4. Canary promotion requires health, diagnostics, security, quarantine, and circuit gates to pass together.
5. Automatic rollback remains limited to a verified bounded first failure.
6. Maintenance emergency override affects only the time window; it does not bypass any other production gate.
7. Runtime-state writes are atomic and future/unknown state versions fail closed.
8. All v0.1-v1.2 rollback, Secure Boot, DRA, fabric, policy, SLO, PSIRT, audit, SBOM and provenance safeguards remain in force.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```
