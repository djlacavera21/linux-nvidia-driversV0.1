# Linux NVIDIA Drivers v1.0

`nvlx` v1.0 promotes the project from a GPU fleet toolkit into a **production control plane**. The host `nvlx` CLI, cluster `nvlx-fleet` CLI, and new stable `nvlx-controller` surface now share a fail-closed operating model for configuration, compatibility, planning, approvals, execution, HA coordination, audit, security gating, and reproducible releases.

> [!IMPORTANT]
> v1.0 still does not grant unbounded autonomous mutation. A disruptive action is planned first, fingerprinted, approved against that exact fingerprint, compatibility-checked, and only then eligible for execution. A changed plan invalidates the approval.

## v1.0 production contracts

- **Stable configuration schema.** `schema_version: 1` is canonicalized and SHA-256 fingerprinted. Unknown top-level keys fail closed.
- **Approval-bound execution.** Plans include operation, target, ordered steps, configuration fingerprint, and their own immutable plan fingerprint. Approval must match the exact current plan.
- **Durable controller state.** Generation-aware state transitions prevent unsafe jumps such as `idle -> executing` and support durable JSON state writes.
- **HA controller lease model.** `nvlx-controller ha-plan` renders Kubernetes `coordination.k8s.io/v1` Lease state with bounded lease/renew/retry timing.
- **Kubernetes/DRA compatibility preflight.** v1.0 treats Kubernetes 1.34+ as the stable DRA API baseline and rejects `GPUCluster`/`ClusterPolicy` coexistence.
- **GPU Operator migration safety.** In-place `ClusterPolicy -> GPUCluster` migration is rejected because NVIDIA does not support it. GPUCluster upgrade planning requires ComputeDomain CRD readiness.
- **Production bundle integrity.** Deterministic SHA-256 bundle manifests verify configuration/release inputs and emit a Cosign `verify-blob` plan for external keyless signature validation.
- **v0.1-v0.9 retained.** Transactional driver rollback, boot health, Secure Boot, MIG/Fabric/DCGM/NVSDM, DRA placement, GPUDirect, SLO/policy gates, curtailment, checkpointing, federation, PSIRT security gates, SBOMs, and provenance remain in force.

## Stable controller commands

```bash
# validate the stable configuration contract
nvlx-controller config-validate fleet-v1.json

# production compatibility check
nvlx-controller compat \
  --kubernetes-version v1.35.2 \
  --gpucluster \
  --computedomains-crd-ready

# create a reconciliation plan
nvlx-controller reconcile-plan fleet-v1.json \
  --kubernetes-version v1.35.2 \
  --gpucluster \
  --computedomains-crd-ready \
  --operation upgrade-gpu-operator \
  --target prod-east \
  --step preflight \
  --step drain-canary \
  --step upgrade \
  --step validate

# approve exact plan, then verify it is still executable
nvlx-controller approve plan.json --by operator@example
nvlx-controller execute-check plan.json approval.json

# HA lease and deterministic bundle integrity
nvlx-controller ha-plan
nvlx-controller bundle-manifest . pyproject.toml README.md
nvlx-controller cosign-plan manifest.json manifest.sig --identity release-workflow
```

## v1.0 controller lifecycle

```text
CONFIG v1
   |
   v
SCHEMA VALIDATION + CONFIG FINGERPRINT
   |
   v
KUBERNETES / NVIDIA COMPATIBILITY PREFLIGHT
   |\
   | fail -> BLOCKED + AUDIT
   v
DETERMINISTIC RECONCILIATION PLAN
   |
   v
PLAN FINGERPRINT
   |
   v
AWAITING APPROVAL
   |
   +---- plan changes ----> APPROVAL INVALIDATED
   |
   v
APPROVED
   |
   v
LEASE / LEADER CHECK
   |
   v
EXECUTION ELIGIBLE
   |
   v
HEALTH + SLO + SECURITY VALIDATION
   |\
   | fail -> ROLLBACK / QUARANTINE / BLOCK
   v
SUCCEEDED + AUDIT
```

## Current platform baseline

Kubernetes Dynamic Resource Allocation is a stable API in modern Kubernetes, and v1.0 uses Kubernetes 1.34+ as its production DRA baseline. NVIDIA GPU Operator 26.7 manages DRA through the singleton `GPUCluster` resource and Device Plugin allocation through `ClusterPolicy`; they cannot coexist. NVIDIA also documents that an in-place migration from `ClusterPolicy` to `GPUCluster` is unsupported and that ComputeDomain CRDs require explicit handling during GPUCluster upgrades.

## Safety invariants

1. Unknown v1 configuration fields fail closed.
2. Compatibility failures prevent plan execution.
3. A plan approval is valid only for the exact plan fingerprint it approved.
4. Controller state transitions are explicit and generation-aware.
5. HA timing requires `retry < renew deadline < lease duration`.
6. `GPUCluster` and `ClusterPolicy` coexistence is rejected.
7. In-place Device Plugin-to-DRA migration is never synthesized automatically.
8. ComputeDomain CRD readiness is mandatory before relevant GPUCluster upgrades.
9. Bundle integrity uses deterministic SHA-256 manifests; external signatures are verified by standard tooling rather than custom cryptography.
10. All earlier rollback, Secure Boot, quarantine, telemetry, PSIRT, SBOM, provenance, DRA-alpha, placement, checkpoint, and failover safeguards remain active.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```
