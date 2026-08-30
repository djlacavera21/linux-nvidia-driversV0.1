# nvlx: Linux-NVIDIA-Driver v1.6.3.2

`nvlx` v1.6.3.2 adds continuity fencing to the live read-only NVIDIA inventory introduced in v1.6.3 and hardened in v1.6.3.1.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events.

## v1.6.3.2 NVIDIA snapshot continuity

- **Baseline identity.** The first healthy NVIDIA snapshot establishes a trusted in-process identity baseline.
- **Two-snapshot promotion.** Any later identity/topology change is fenced for one cycle and must be observed identically on the next fresh preflight before it becomes the new baseline.
- **Same-name replacement detection.** UID changes for GPUCluster, ClusterPolicy, NVIDIADriver, ComputeDomain, ComputeDomainClique, or GPU Nodes are treated as incarnation changes even when names stay the same.
- **API remapping detection.** Changes to discovered NVIDIA API versions or resource mappings break continuity and require confirmation.
- **GPU-node membership fencing.** GPU Node identity-set changes cannot silently establish a new GPUFleet continuity window.
- **Candidate churn fails closed.** If a candidate changes again before confirmation, the new candidate replaces it and the fence remains closed.
- **Return-to-baseline recovery.** If the original baseline reappears, the pending candidate is discarded and continuity may proceed normally.
- **Opaque resourceVersion preserved.** Ordinary Kubernetes `resourceVersion` changes are excluded from snapshot identity and are never numerically or lexically ordered.
- **UID required for continuity.** Objects participating in continuity must expose stable Kubernetes metadata.uid values; missing UID fails closed.
- **Read-only boundary unchanged.** No NVIDIA mutation path or write verb is introduced.

## Safety invariants

1. A changed NVIDIA snapshot cannot establish GPUFleet continuity after only one observation.
2. Stable legitimate topology changes can converge after two identical fresh preflights.
3. Same-name object recreation is distinguished by Kubernetes UID.
4. API-version/resource-map changes are part of continuity identity.
5. GPU-node membership and incarnation are part of continuity identity.
6. Kubernetes `resourceVersion` remains opaque update metadata, not incarnation identity.
7. v1.6.3.1 discovery/API identity validation remains active.
8. v1.6.2.9 relist settlement and all prior watch, cursor, finalizer, generation, Lease, leadership, and inventory safeguards remain active.
9. NVIDIA resources remain read-only in v1.6.3.2.
