# nvlx: Linux-NVIDIA-Driver v1.6.0

`nvlx` v1.6.0 is the first release in this repository to move the Kubernetes operator from reconciliation planning into a real API-backed runtime. It performs live GPUFleet list/watch operations, status and finalizer PATCH requests, Kubernetes Event creation, Lease-based leader election/fencing, and serves HTTP liveness/readiness/Prometheus endpoints.

> [!IMPORTANT]
> v1.6 intentionally keeps NVIDIA resource changes read-only. The operator can observe NVIDIA CRDs/resources and mutate only nvlx-owned GPUFleet status/finalizers plus its Lease and Events. Driver/GPU Operator mutation remains behind the existing approval/preflight/rollback architecture for a later runtime release.

## v1.6.0 runtime

- **Real Kubernetes transport.** Stdlib HTTPS client supports in-cluster ServiceAccount token/CA authentication, bounded timeouts, JSON API calls, and newline watch streams without shelling out to `kubectl`.
- **Live GPUFleet list/watch.** The runtime lists cluster-scoped `nvlx.io/v1alpha1` GPUFleets, resumes from `resourceVersion`, accepts watch bookmarks, and relists on HTTP/watch `410 Gone`.
- **Real status PATCH.** Controller-owned status writes use the `/status` subresource with optimistic `resourceVersion`. `409`/`412` conflicts refetch and recompute the write boundary once rather than overwriting blindly.
- **Real finalizer PATCH.** Deletion removes only `nvlx.io/fleet-protection`, preserves unrelated finalizers, and retains the existing rollback/quarantine/active-execution safety gates.
- **Kubernetes Events.** Successful reconciles emit `events.k8s.io/v1` Events in `nvlx-system` (or the configured namespace) referencing the cluster-scoped GPUFleet UID.
- **Lease CAS fencing.** `coordination.k8s.io/v1` Lease acquisition and renewal use `resourceVersion` CAS. Every mutation path rechecks leadership immediately before API writes.
- **Graceful runtime loop.** SIGTERM/SIGINT stop new work; list/watch reconnects use bounded exponential backoff.
- **Health and metrics server.** `/livez`, `/readyz`, and `/metrics` are served over HTTP. Readiness requires API reachability, current leadership, fresh inventory, and a non-terminating process.
- **Production manifests.** Generated resources now include ServiceAccount, ClusterRole/Binding, two-replica Deployment, HTTP probes, PodDisruptionBudget, NetworkPolicy, non-root execution, read-only root filesystem, dropped capabilities, and RuntimeDefault seccomp.
- **Fake-API integration tests.** CI exercises list→watch→status PATCH, conflict refetch/retry, leader-loss fencing, finalizer preservation, watch bookmark/410 relist, and Lease renewal against a local fake Kubernetes HTTP server.

## Safety invariants

1. A replica that cannot prove current Lease leadership does not mutate GPUFleet status or finalizers.
2. Status conflicts are refetched before retry; stale `resourceVersion` is never blindly overwritten.
3. Finalizer removal preserves unrelated finalizers and remains subject to rollback/quarantine/execution safety gates.
4. Watch expiration causes relist from authoritative state.
5. Authentication tokens are never included in API error messages.
6. NVIDIA resources remain read-only in v1.6.0; no automatic driver/GPU Operator mutation or unsupported DRA migration is introduced.
7. All v0.1-v1.5.9 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing and replay safeguards remain in force.
