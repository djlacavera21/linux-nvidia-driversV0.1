# nvlx: Linux-NVIDIA-Driver v1.6.3.1

`nvlx` v1.6.3.1 hardens the live read-only NVIDIA inventory introduced in v1.6.3. The patch validates Kubernetes discovery and returned-object identity before NVIDIA state can establish GPUFleet readiness.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events.

## v1.6.3.1 inventory identity hardening

- **Discovery identity verification.** A served discovery document may report `groupVersion`; when present it must match the group/version being queried.
- **Cluster-scope contract enforcement.** NVIDIA resources used by the inventory must not be advertised as namespaced, and returned objects must not carry a namespace.
- **Object API identity checks.** Returned NVIDIA objects may report `apiVersion`; when present it must match the exact discovered API endpoint used to list that resource.
- **Metadata integrity.** Optional UID and `resourceVersion` values must be non-empty strings when present. Kubernetes `resourceVersion` remains opaque and is never ordered.
- **GPU Node identity checks.** GPU-labeled inventory objects must remain core/v1 Nodes and cluster scoped when those identity fields are present.
- **TOCTOU discovery check.** The hardened layer revalidates that each mapped resource is still advertised by the selected served version before listing it.
- **Fail-closed runtime behavior retained.** Any discovery or identity mismatch raises an inventory error, keeps NVIDIA preflight false, invalidates inventory freshness, and prevents GPUFleet continuity establishment.
- **No RBAC expansion.** v1.6.3.1 adds no permissions beyond the read-only NVIDIA and Node inventory permissions from v1.6.3.

## Safety invariants

1. NVIDIA discovery and object identity must be coherent before inventory is trusted.
2. Cluster-scoped NVIDIA control-plane resources cannot be accepted from namespaced discovery or namespaced list objects.
3. Returned object API versions cannot contradict the endpoint that produced them.
4. Optional identity fields fail closed when present but malformed.
5. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
6. GPUCluster/ClusterPolicy mutual exclusion, singleton naming, readiness, default-driver, unmanaged-GPU, and ComputeDomain checks from v1.6.3 remain active.
7. The v1.6.2.9 atomic relist settlement barrier and all prior watch, cursor, finalizer, generation, Lease, and leadership safeguards remain active.
8. NVIDIA resources remain read-only; no live driver/GPU Operator mutation path is introduced.
