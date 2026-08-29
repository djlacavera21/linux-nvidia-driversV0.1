# Linux NVIDIA Drivers v0.8

`nvlx` now extends the v0.7 GPU resource fabric into **workload placement and resilience**. v0.8 adds DRA-native placement claims, ComputeDomain-aware gang plans, GPUDirect/RDMA qualification, MIG/DynamicMIG brokerage, fleet power/thermal policy, checkpoint-aware evacuation plans, and deterministic multi-cluster failover planning.

> [!IMPORTANT]
> v0.8 remains inspection/planning-first for disruptive or alpha functionality. DynamicMIG is not silently enabled, GPU workloads are not assumed transparently checkpointable, and multi-cluster failover does not mutate clusters automatically.

## v0.8 highlights

- **DRA-native workload placement.** `nvlx-fleet placement` generates `ResourceClaim` plans using `gpu.nvidia.com`, optional product/memory selectors, and ComputeDomain intent.
- **ComputeDomain-aware gang scheduling.** `nvlx-fleet gang` plans all-or-nothing or bounded-minimum replica groups and explicitly accounts for the fact that Kubernetes DRA resources do not support preemption.
- **RDMA / GPUDirect qualification.** `nvlx-fleet gpudirect` checks RDMA tooling and NVIDIA peer-memory/DMA-BUF readiness and keeps Network Operator requirements visible.
- **MIG / DynamicMIG brokerage.** `nvlx-fleet mig-broker` validates profile demand and rejects known DynamicMIG feature-gate conflicts before any production geometry change.
- **Power / thermal fleet policy.** `nvlx-fleet power-policy` validates watt/temperature thresholds and the intended alert/drain/quarantine response.
- **Checkpoint / evacuation planning.** `nvlx-fleet evacuate-plan` defaults to application checkpoints and renders cordon/inventory/drain actions without pretending transparent CUDA checkpointing exists.
- **Multi-cluster federation / DR.** `nvlx-fleet federation-plan` deterministically ranks healthy failover clusters by available GPU capacity and rejects insufficient DR capacity.

## NVIDIA assumptions

GPU Operator 26.7 manages DRA Driver v0.5.0 through `GPUCluster`. Full GPU/existing MIG allocation and ComputeDomains are GA, while DynamicMIG remains alpha. DynamicMIG conflicts with `PassthroughSupport`, `NVMLDeviceHealthCheck`, and `MPSSupport`, so v0.8 blocks those combinations in the broker.

GPUDirect RDMA remains a joint GPU Operator + Network Operator capability. v0.8 therefore treats NIC/RDMA qualification as part of placement readiness instead of assuming GPU health alone implies high-speed fabric readiness.

## New commands

```bash
nvlx-fleet placement --count 8 --product H100 --min-memory-gib 80 --compute-domain rack-a
nvlx-fleet gang --replicas 4 --gpus-per-replica 8 --compute-domain rack-a
nvlx-fleet gpudirect
nvlx-fleet mig-broker --profile 1g.10gb --replicas 8 --dynamic
nvlx-fleet power-policy --max-watts 700 --max-temp-c 85 --action drain
nvlx-fleet evacuate-plan gpu01 --checkpoint-mode application
nvlx-fleet federation-plan --primary east --required-gpus 8 east:us-east:8 west:us-west:16
```

## Safety invariants

1. DRA placement is generated as a claim plan; cluster mutation remains explicit.
2. Gang plans never assume DRA preemption is available.
3. DynamicMIG is treated as alpha and conflicting feature gates are rejected before rollout.
4. GPUDirect qualification requires both GPU-side and RDMA/network evidence.
5. Power and thermal policy never silently changes clocks or power limits; it defines fleet responses.
6. Evacuation defaults to application-level checkpointing and never claims transparent CUDA state restoration.
7. Federation failover requires independently healthy capacity; no cluster is promoted merely because it is reachable.
8. All v0.1-v0.7 rollback, security, quarantine, PSIRT, reproducibility, SBOM, and provenance gates remain in force.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```
