# nvlx: Linux-NVIDIA-Driver v1.4

`nvlx` v1.4 adds a **Kubernetes-native GPU fleet API** above the 1.3 runtime enforcement core. Desired NVIDIA fleet state can now be represented as a `GPUFleet` custom resource with status conditions, protective finalizers, Kubernetes Events, admission policy, and canary-aware reconciliation results.

> [!IMPORTANT]
> Kubernetes-native does not mean unbounded autonomy. The 1.3 leader, approval, maintenance, preflight, idempotency, rollout-budget, circuit-breaker, rollback, health/SLO, PSIRT and quarantine gates remain authoritative.

## v1.4 Kubernetes-native control plane

- **GPUFleet CRD contract.** Cluster-scoped `gpufleets.nvlx.io` with `v1alpha1` desired driver, GPU Operator, allocation mode and canary-wave state.
- **Status subresource.** Kubernetes-style `Ready`, `Progressing`, and `Degraded` conditions carry observed generation and transition time.
- **Protective finalizer.** `nvlx.io/fleet-protection` cannot be removed while rollback, quarantine or active execution remains unresolved.
- **Events API.** Reconciliation outcomes emit `events.k8s.io/v1` Normal/Warning event plans.
- **Admission guard.** A fail-closed `ValidatingAdmissionPolicy` and binding require an explicit approved-change marker for GPUFleet spec mutation.
- **Runtime-backed reconcile mapping.** 1.3 runtime allow/hold results map into Kubernetes phases, conditions, events, requeue behavior and persisted canary-wave progression.
- **Dedicated CLI.** `nvlx-k8s` renders the CRD, GPUFleet objects, conditions, event plans, admission policy, finalizer checks and reconcile results.

## Kubernetes commands

```bash
nvlx-k8s crd
nvlx-k8s fleet prod --driver-version 610.57.04 --gpu-operator-version 26.7.0
nvlx-k8s conditions --generation 2 --ready
nvlx-k8s admission-policy
nvlx-k8s reconcile prod --generation 2 --allowed --runtime-action execute --current-wave 0 --promoted
nvlx-k8s finalize-check --deleting
```

## Current NVIDIA/Kubernetes baseline

For NVIDIA GPU Operator 26.7 DRA deployments, `GPUCluster` remains mutually exclusive with `ClusterPolicy`; the managed DRA workflow requires Kubernetes 1.34.2+, NVIDIA driver 580+, and a CDI-capable runtime. `GPUCluster` manages DRA/ComputeDomain/DCGM operands but not the driver itself; use `NVIDIADriver` or a preinstalled driver. ComputeDomain CRDs still require explicit handling on GPU Operator upgrade paths.

## Safety invariants

1. GPUFleet status never overrides the 1.3 runtime decision; it reflects it.
2. Finalization is held while rollback, quarantine, or execution state remains unresolved.
3. Spec mutation is denied unless the approved-change admission condition is satisfied.
4. Blocked runtime decisions become `Degraded` status and Warning Events, not partial execution.
5. Canary-wave state advances only from an allowed/promoted runtime outcome.
6. `GPUCluster` and `ClusterPolicy` coexistence remains invalid.
7. All v0.1-v1.3 rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, audit, SBOM and provenance safeguards remain in force.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```
