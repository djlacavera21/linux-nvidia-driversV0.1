# nvlx: Linux-NVIDIA-Driver v1.1

`nvlx` v1.1 hardens the 1.0 production control plane for long-running GPU fleet operation. It keeps the stable v1 configuration and plan-fingerprint contracts while adding approval lifetime controls, tamper-evident audit chaining, explicit controller-state migrations, leader-aware reconciliation ticks, controller metrics, rollback-safe execution records, and Kubernetes HA deployment/RBAC manifests.

> [!IMPORTANT]
> v1.1 does not weaken the 1.0 execution boundary. Disruptive work still follows **plan → fingerprint → approve → leader/safety checks → execute → validate**, and a changed plan invalidates its approval.

## v1.1 hardening

- **Approval lifecycle.** `approval-status` adds bounded TTL checks and explicit revocation on top of exact plan-fingerprint matching.
- **Tamper-evident audit chain.** Controller audit records can be chained with SHA-256 over sequence, previous hash, and canonical payload; edits break verification.
- **State migrations.** Persistent controller state upgrades explicitly to `state_version: 2`; state from a future version is refused rather than guessed at.
- **Leader-aware runtime.** `runtime-tick` yields `standby`, `hold`, `noop`, or `reconcile` based on lease ownership, safety gates, and observed/desired generations.
- **Controller metrics.** Prometheus text output exposes leadership, reconcile totals/failures, pending approvals, and rollback-required state.
- **Rollback-safe execution records.** Failed executions are recorded with `rollback_required: true`; success never silently clears a prior failed record.
- **Kubernetes HA manifests.** `k8s-manifests` renders a ServiceAccount, least-scope namespaced Role/RoleBinding, and a two-replica Deployment. Lease permissions are explicit and production HA refuses fewer than two replicas.
- **1.0 contracts retained.** Stable configuration fingerprints, compatibility preflight, exact approval binding, HA lease timing, bundle manifests, and Cosign verification planning remain unchanged.

## Stable controller commands

```bash
# 1.0 production contracts
nvlx-controller config-validate fleet-v1.json
nvlx-controller compat --kubernetes-version v1.35.2 --gpucluster --computedomains-crd-ready
nvlx-controller reconcile-plan fleet-v1.json \
  --kubernetes-version v1.35.2 --gpucluster --computedomains-crd-ready \
  --operation upgrade-gpu-operator --target prod-east \
  --step preflight --step upgrade --step validate
nvlx-controller approve plan.json --by operator@example
nvlx-controller execute-check plan.json approval.json

# 1.1 lifecycle and runtime
nvlx-controller approval-status plan.json approval.json --ttl-seconds 1800
nvlx-controller state-migrate controller-state.json
nvlx-controller runtime-tick --observed-generation 41 --desired-generation 42 --leader
nvlx-controller metrics --leader --reconcile-total 120 --reconcile-failures 1
nvlx-controller execution-record <plan-fingerprint>
nvlx-controller k8s-manifests --namespace nvlx-system --replicas 2
```

## Production lifecycle

```text
CONFIG v1
   |
   v
VALIDATE + FINGERPRINT
   |
   v
COMPATIBILITY + POLICY + SECURITY PREFLIGHT
   |
   v
PLAN + PLAN FINGERPRINT
   |
   v
APPROVAL -------------------- expired/revoked/changed ---> BLOCK
   |
   v
LEASE OWNERSHIP
   |\
   | not leader ---> STANDBY
   v
GENERATION RECONCILIATION
   |\
   | safety gate ---> HOLD
   v
EXECUTION RECORD
   |\
   | failure -----> ROLLBACK REQUIRED
   v
VALIDATE + AUDIT CHAIN
```

## Safety invariants

1. Approval expiry and revocation are additive restrictions; they never bypass plan-fingerprint validation.
2. Only the lease holder may enter the reconcile path; replicas without leadership remain standby.
3. Safety-gate blocks result in `hold`, not partial execution.
4. Persistent state migrations are explicit and forward-version state fails closed.
5. Failed execution records require rollback handling and are never reported as success.
6. The audit chain is tamper-evident and contains controller decisions, not credentials or GPU serials.
7. Kubernetes controller RBAC is namespaced and limited to Lease mutation plus ConfigMap observation in the generated baseline.
8. HA deployment generation requires at least two replicas.
9. All v0.1-v1.0 rollback, Secure Boot, quarantine, DRA, telemetry, PSIRT, SBOM, provenance, checkpoint, federation, and approval safeguards remain active.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```
