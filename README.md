# nvlx: Linux-NVIDIA-Driver v1.6.2.2

`nvlx` v1.6.2.2 is a narrow post-1.6.2.1 runtime-safety hotfix. It preserves the Kubernetes API surface and NVIDIA read-only boundary while making locally cached leadership proof fail closed across API loss, failed probes, stale readiness and list/watch exceptions.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.2.2. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.2.2 hotfixes

- **Immediate leadership invalidation.** A reusable runtime helper now clears both `stats.leader` and the monotonic timestamp of the last verified Lease whenever leadership proof becomes invalid.
- **API-loss proof clearing.** If list/watch transport handling marks the Kubernetes API unreachable, the runtime clears cached leadership before returning a reconnect/relist outcome.
- **List failure fencing.** A list/relist exception cannot carry a previous successful Lease verification into a later retry cycle.
- **Readiness fail-closed cleanup.** `/readyz` on an API-unreachable runtime actively erases cached leadership proof instead of only returning not-ready while leaving old proof resident.
- **Stale proof cleanup.** When the verified-leadership freshness window expires, both the local leader flag and cached monotonic verification timestamp are cleared.
- **Failed-probe cleanup retained.** Explicit failed Lease probes continue to revoke local leadership immediately.
- **Successful quiet-cluster behavior retained.** A successful empty relist still renews/verifies the Lease and remains ready while the proof is within the configured freshness window.
- **Prior safeguards retained.** Lease clock-skew fencing, timezone-aware freshness, 20-second Kubernetes watch lifetime, 25-second watch socket timeout, conflict-safe status/finalizer recomputation, UID-bound mutation verification, token-file auth, opaque resourceVersion semantics and verified Lease writes remain active.

## Safety invariants

1. Cached Lease verification is erased whenever Kubernetes API reachability is lost.
2. A list/watch exception cannot leave stale leadership proof available for a later cycle.
3. Readiness cannot rely on an old verified timestamp after the API has become unreachable.
4. Expired leadership proof clears both timestamp and local leader state.
5. Successful Lease verification on a healthy quiet cluster remains usable only within the configured freshness window.
6. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
7. Conflict retries remain bounded and leadership-fenced.
8. NVIDIA resources remain read-only in v1.6.2.2.
9. All v0.1-v1.6.2.1 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay, UID-integrity and Lease-CAS safeguards remain in force.
