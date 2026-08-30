# nvlx: Linux-NVIDIA-Driver v1.6.2.1

`nvlx` v1.6.2.1 is a narrow post-1.6.2 runtime-safety hotfix. It preserves the Kubernetes API surface and NVIDIA read-only boundary while tightening Lease freshness semantics and making readiness depend on recently verified leadership rather than a sticky leader boolean.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.2.1. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.2.1 hotfixes

- **Future-dated Lease fencing.** Lease `renewTime`/`acquireTime` values more than the configured clock-skew allowance ahead of local UTC time are rejected as fresh instead of extending leadership indefinitely.
- **Timezone fail-closed handling.** Naive or malformed Lease timestamps do not participate in freshness decisions.
- **Verified-readiness window.** The operator runtime records the monotonic time of its last successful live leadership verification. `/readyz` requires that verification to remain within the configured freshness window.
- **Stale leader demotion.** If the local verified-leadership window expires, readiness fails and the local runtime leader flag is cleared rather than remaining sticky.
- **Empty-cluster Lease renewal.** Every relist now probes leadership before list/watch processing, so a cluster with zero GPUFleet objects still renews/verifies the controller Lease.
- **Lease-safe watch cadence.** `nvlx-operator` defaults to Kubernetes `timeoutSeconds=20` with a 25-second client watch socket timeout, staying below the default 30-second Lease duration while preserving the required socket-over-server timeout margin.
- **Prior v1.6.2 safeguards retained.** Conflict-safe status recomputation, conflict-safe finalizer recovery, UID-bound mutation verification, token-file authentication, bounded watch state, opaque resourceVersion semantics, and verified Lease write responses remain active.

## Safety invariants

1. A Lease timestamp cannot be considered fresh solely because it is arbitrarily far in the future.
2. Lease freshness uses timezone-aware timestamps and a bounded explicit skew allowance.
3. Readiness requires a recent successful live leadership verification, not only `stats.leader == true`.
4. Quiet or empty GPUFleet clusters still renew leadership once per relist cycle.
5. The default watch lifetime is shorter than the default Lease duration.
6. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
7. Conflict retries remain bounded and leadership-fenced.
8. NVIDIA resources remain read-only in v1.6.2.1.
9. All v0.1-v1.6.2 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay, UID-integrity and Lease-CAS safeguards remain in force.
