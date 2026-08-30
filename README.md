# nvlx: Linux-NVIDIA-Driver v1.6.3

`nvlx` v1.6.3 is the next live-runtime milestone after the v1.6.2.x hardening train. It adds a Kubernetes-native, read-only NVIDIA inventory and preflight layer in front of GPUFleet reconciliation while preserving the existing NVIDIA mutation boundary.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only in v1.6.3. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events. Live NVIDIA configuration changes remain deferred.

## v1.6.3 live NVIDIA inventory

- **Multi-version Kubernetes API discovery.** The operator discovers every served version of `nvidia.com` and `resource.nvidia.com`, then maps each resource to a served version instead of assuming all NVIDIA CRDs share one API version.
- **GPU Operator control-plane inventory.** Read-only snapshots include `GPUCluster`, `ClusterPolicy`, and `NVIDIADriver` resources.
- **DRA inventory.** When served, snapshots include `ComputeDomain` and `ComputeDomainClique` resources from `resource.nvidia.com`.
- **GPU node inventory.** Kubernetes Nodes carrying `nvidia.com/gpu.present=true` are included in the normalized snapshot.
- **GPUCluster/ClusterPolicy exclusion.** A cluster exposing both control planes fails preflight closed.
- **GPUCluster singleton enforcement.** A discovered GPUCluster must be the singleton `gpu-cluster` resource.
- **Control-plane readiness checks.** Explicit non-ready states reported by GPUCluster, ClusterPolicy, or NVIDIADriver block preflight.
- **Default-driver consistency.** More than one default NVIDIADriver fails preflight.
- **Unmanaged-GPU detection.** GPU nodes with neither GPUCluster nor ClusterPolicy block preflight rather than being treated as safely unmanaged.
- **ComputeDomain API validation.** If GPUCluster explicitly enables ComputeDomains, the `resource.nvidia.com/computedomains` API must be served.
- **Runtime gating.** NVIDIA preflight runs before each GPUFleet list/watch continuity attempt. A failed or unreadable NVIDIA inventory prevents the GPUFleet cycle from starting and keeps readiness false.
- **Read-only RBAC expansion.** `resource.nvidia.com` resources and core Nodes receive only `get`, `list`, and `watch`; no NVIDIA write verbs are introduced.

## Safety invariants

1. NVIDIA API discovery is fail closed on malformed or contradictory discovery data.
2. The runtime never guesses one API version for every NVIDIA CRD; each resource is resolved against a served group version.
3. GPUCluster and ClusterPolicy cannot coexist in an accepted preflight.
4. GPUCluster must be the singleton named `gpu-cluster`.
5. Explicit non-ready NVIDIA control-plane or driver state blocks GPUFleet continuity establishment.
6. GPU nodes without a recognized GPU Operator control plane block preflight.
7. NVIDIA inventory permissions remain read-only: `get`, `list`, and `watch` only.
8. NVIDIA preflight must pass before a new GPUFleet list/watch cycle begins.
9. The v1.6.2.9 atomic relist settlement barrier remains active after NVIDIA preflight succeeds.
10. Settlement-bound cursor handling, retry-safe watch dedupe, semantic finalizer verification, generation-bound mutation verification, Lease freshness, leadership invalidation, token-file auth, bounded watch cache, and opaque `resourceVersion` semantics remain active.
11. No automatic ClusterPolicy↔GPUCluster or Device Plugin↔DRA migration is introduced.
12. NVIDIA driver/GPU Operator resources remain read-only in v1.6.3.
