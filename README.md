# Linux NVIDIA Drivers v0.7

`nvlx` now treats a GPU fleet as a **resource fabric**, not just a set of driver-managed nodes. v0.7 layers DRA/CDI qualification, NVLink/NVSwitch fabric health, Network Operator/RDMA readiness, capacity-fragmentation reporting, confidential-GPU validation, and fail-closed admission guardrails on top of the v0.6 fleet safety model.

> [!IMPORTANT]
> v0.7 remains inspection-first. It does not silently migrate a cluster from Device Plugin to DRA, repartition MIG, rewrite networking, or remove quarantine. Mutating maintenance and quarantine actions retain the explicit confirmation model.

## v0.7 highlights

- **DRA/CDI qualification.** `nvlx-fleet dra` identifies `GPUCluster` versus `ClusterPolicy`, rejects coexistence, counts ComputeDomains, and surfaces enabled alpha DRA features.
- **Fabric health.** `nvlx-fleet fabric` checks `nvidia-smi topo -m`, NVLink edges, NVSwitch presence, and Fabric Manager readiness.
- **Topology domains.** `fabric-domains` creates deterministic topology-domain assignments for planners/canaries without mutating node labels.
- **Network Operator/RDMA readiness.** Detects NVIDIA/Mellanox NIC/RDMA labels and checks for a Network Operator `NicClusterPolicy`.
- **GPU capacity/fragmentation.** Reports allocatable, requested, free GPU capacity and nodes with stranded free capacity.
- **Confidential GPU readiness.** Validates `vm-passthrough` node separation and Kata runtime availability for confidential-container pools.
- **Admission guardrails.** Generates a fail-closed Kubernetes `ValidatingAdmissionPolicy` that protects quarantined-node state from generic node updates.
- **v0.6 retained.** Cluster qualification, guarded drain/uncordon, ClusterPolicy validation, DCGM burn-in, quarantine, Prometheus rules, canary waves, PSIRT gating, SBOM and provenance remain intact.

## Current NVIDIA ecosystem assumptions

The driver baseline remains **610.57.04** and GPU Operator planning targets **v26.7.0**. GPU Operator 26.7 documents DRA Driver v0.5.0 as an alternative to the Device Plugin path: a cluster can have `GPUCluster` or `ClusterPolicy`, but not both. Full GPU/existing MIG allocation and ComputeDomains are GA; DynamicMIG, MPS, NVML health checks, passthrough and time-slicing DRA feature gates remain alpha and are surfaced by v0.7 rather than silently accepted.

GPU Operator uses CDI by default starting with v25.10.0. v0.7 therefore treats CDI/DRA state as first-class fleet metadata rather than assuming the legacy runtime-class model.

## New commands

```bash
# resource API and topology
nvlx-fleet dra
nvlx-fleet fabric
nvlx-fleet fabric-domains gpu01 gpu02 gpu03 gpu04 --size 2

# network and capacity
nvlx-fleet network
nvlx-fleet capacity

# confidential GPU pool readiness
nvlx-fleet confidential

# generate fail-closed quarantine admission guardrail
nvlx-fleet admission-policy > nvlx-gpu-safety.json
```

## Resource-fabric model

```text
KUBERNETES NODE INVENTORY
          |
          v
GPU OPERATOR + DRA/CDI MODE
          |
          +---- GPUCluster + ClusterPolicy ----> STOP
          |
          v
GPU / NVLINK / NVSWITCH FABRIC
          |
          +---- unhealthy FM/fabric -----------> QUARANTINE / STOP
          |
          v
NETWORK OPERATOR + RDMA READINESS
          |
          v
CAPACITY + FRAGMENTATION
          |
          v
CONFIDENTIAL / TRADITIONAL POOL SEPARATION
          |
          v
CANARY + MAINTENANCE + DCGM + SECURITY GATES
```

## Safety invariants

1. `GPUCluster` and `ClusterPolicy` coexistence is invalid.
2. Alpha DRA features are surfaced explicitly and never treated as GA by the planner.
3. NVSwitch systems are not considered fabric-healthy when Fabric Manager is inactive.
4. Confidential `vm-passthrough` pools are kept logically separate from traditional GPU workload pools.
5. Admission policy generation is fail-closed and protects quarantine state; applying it remains an operator action.
6. Topology-domain generation is deterministic and non-mutating.
7. All v0.1-v0.6 rollback, security, diagnostic and release-provenance invariants remain in force.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## License

Project-authored orchestration code is MIT licensed. NVIDIA source, firmware, user-space components, trademarks, and redistributable packages remain subject to their respective NVIDIA licenses.
