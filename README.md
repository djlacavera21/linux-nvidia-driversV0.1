# Linux NVIDIA Drivers v0.9

`nvlx` now extends the v0.8 placement/resilience layer into a **governed GPU fleet execution plane**. v0.9 adds policy-as-code, deterministic placement scoring, fleet SLO gates, GPU Direct Storage checkpoint readiness, Run:ai/DRA inspection, power-curtailment planning, append-only decision auditing, and guarded cross-cluster failover plans.

> [!IMPORTANT]
> v0.9 does not turn advisory planning into unbounded autonomy. Placement and failover decisions can be scored and gated, but disruptive cluster actions remain explicit. Power limits are never silently changed and checkpoint readiness must be proven before evacuation/failover is considered safe.

## v0.9 highlights

- **Policy-as-code.** `FleetPolicy` gates free GPU capacity, RDMA, fabric health, thermals, power headroom, alpha-DRA usage, checkpoint requirements, and cross-cluster failover.
- **Governed placement scoring.** `placement-decide` rejects policy-ineligible targets, then deterministically scores remaining targets using free capacity, fabric/RDMA readiness, thermal state, and power headroom.
- **Fleet SLO gates.** `slo-check` blocks progression on low healthy-node fraction, high workload-start latency, quarantined nodes, or exhausted Xid error budgets.
- **GPU Direct Storage readiness.** `gds` checks cuFile/GDS validation tooling, storage mounts, and NVIDIA storage-path evidence before checkpoint storage is treated as ready.
- **Run:ai/DRA visibility.** `runai` detects Run:ai scheduler components and ResourceClaim activity without coupling nvlx to a proprietary scheduler API.
- **Power curtailment planning.** `curtailment` selects hold, scheduler-throttle, checkpoint-and-evacuate, or stop-admission-and-drain responses based on the requested power reduction and workload checkpointability. It never issues `nvidia-smi -pl` automatically.
- **Governed failover.** `failover-plan` requires checkpoint, target capacity, and security readiness before a cross-cluster promotion is considered safe.
- **Append-only audit journal.** `audit` records JSONL decisions with UTC timestamps, action, target, allow/deny state, and reasons.

## Commands

```bash
# policy and deterministic placement
nvlx-fleet policy-check candidate.json --policy fleet-policy.json
nvlx-fleet placement-decide candidates.json --policy fleet-policy.json

# SLO and runtime integrations
nvlx-fleet slo-check --healthy-fraction 0.995 --p95-startup-seconds 45
nvlx-fleet gds
nvlx-fleet runai

# power-aware operations
nvlx-fleet curtailment --current-watts 1000 --target-watts 750
nvlx-fleet curtailment --current-watts 1000 --target-watts 500 --checkpointable

# governed disaster recovery
nvlx-fleet failover-plan --source east --target west --namespace training --checkpoint-ready --capacity-ready --security-ready

# audit a decision
nvlx-fleet audit --path ./nvlx-audit.jsonl --action failover --target west --allowed
```

## Governed execution model

```text
WORKLOAD INTENT
      |
      v
DRA / FABRIC / RDMA / CAPACITY INVENTORY
      |
      v
FLEET POLICY ---------------------------- fail ---> DENY + AUDIT
      |
      v
DETERMINISTIC PLACEMENT SCORE
      |
      v
SLO + SECURITY + QUARANTINE GATES ------- fail ---> HOLD / QUARANTINE
      |
      v
CHECKPOINT / GDS READINESS
      |
      +---- power event ---> CURTAIL / CHECKPOINT / EVACUATE PLAN
      |
      +---- cluster fault -> FAILOVER PLAN
      |
      v
EXPLICIT OPERATOR EXECUTION
      |
      v
AUDIT RECORD
```

## Safety invariants

1. Policy rejection happens before placement ranking.
2. Placement scoring is deterministic; ties resolve by target name rather than random selection.
3. SLO failures block rollout/failover advancement.
4. GDS readiness is evidence-based and does not claim every mounted filesystem is GPUDirect-capable.
5. Run:ai integration is observational; nvlx does not impersonate or bypass the scheduler.
6. Power curtailment is a response plan, not an implicit GPU power-limit mutation.
7. Cross-cluster failover requires checkpoint, capacity, and security readiness simultaneously.
8. Audit records are append-only JSONL and contain policy decisions, not credentials or GPU serial numbers.
9. All v0.1-v0.8 rollback, PSIRT, quarantine, DRA-alpha, reproducibility, SBOM, and provenance safeguards remain in force.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```
