# nvlx: Linux-NVIDIA-Driver v1.6.3.3

`nvlx` v1.6.3.3 makes the NVIDIA snapshot-continuity baseline introduced in v1.6.3.2 durable across controller restarts by persisting it in the existing Kubernetes Lease.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.3.3 persistent continuity checkpoint

- **Lease-backed persistence.** The accepted NVIDIA continuity baseline and pending candidate are stored in an annotation on the existing `nvlx-controller` Lease, so the state survives process, pod, and node replacement without a new storage resource.
- **No RBAC expansion.** Persistence reuses the Lease permissions already required for leader election; no ConfigMap, Secret, PVC, or NVIDIA write permission is added.
- **Leader-fenced writes.** A checkpoint write is allowed only when the live Lease currently reports this controller identity as `holderIdentity`.
- **Optimistic CAS.** Checkpoint writes use the Lease `metadata.resourceVersion` and retry at most once after `409/412` conflict.
- **Verified write response.** Success requires a returned non-empty resourceVersion and an exact echo of the continuity annotation.
- **Integrity envelope.** The checkpoint uses a canonical JSON payload plus SHA-256 digest for corruption/tamper mismatch detection. The digest is not an authentication or signature mechanism.
- **Fail-closed restore.** Invalid JSON, unsupported versions, malformed identities, impossible candidate-without-baseline state, or digest mismatch blocks NVIDIA continuity rather than resetting to first-observation trust.
- **Atomic in-memory rollback.** If persistence fails after a candidate or baseline transition, the runtime restores the previous in-memory continuity state and keeps inventory freshness false.
- **Restart-safe confirmation.** A pending v1.6.3.2 candidate remains pending across restart; its next identical fresh preflight can complete the existing two-snapshot promotion instead of starting over.
- **Opaque resourceVersion semantics retained.** NVIDIA object resourceVersions are not persisted as incarnation identity and remain opaque.

## Safety invariants

1. A controller restart cannot silently discard the accepted NVIDIA continuity baseline.
2. Only the current Lease holder may persist a new baseline or candidate.
3. A stale replica cannot overwrite the checkpoint after leadership moves.
4. Corrupt or malformed persisted continuity state fails closed.
5. Checkpoint persistence is bounded and CAS-protected.
6. The SHA-256 envelope provides integrity mismatch detection only, not authenticity.
7. v1.6.3.2 two-snapshot promotion, UID replacement detection, API-map fencing, and GPU-node membership fencing remain active.
8. v1.6.3.1 discovery/API identity validation and all v1.6.2.x watch, cursor, finalizer, Lease, and leadership safeguards remain active.
9. NVIDIA resources remain read-only in v1.6.3.3.
