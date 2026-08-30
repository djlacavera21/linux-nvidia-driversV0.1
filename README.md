# nvlx: Linux-NVIDIA-Driver v1.6.3.4

`nvlx` v1.6.3.4 binds the persistent NVIDIA continuity checkpoint to the Kubernetes Lease transition epoch so leadership takeovers cannot silently reuse an older holder's accepted baseline.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.3.4 Lease-transition continuity fencing

- **Epoch-bound checkpoint.** The continuity envelope now stores the Lease `leaseTransitions` value alongside the baseline and pending candidate.
- **Takeover detection.** If the stored epoch differs from the live Lease transition count, the restored baseline is treated as stale for the new holder.
- **Two-observation revalidation.** After takeover, the first healthy NVIDIA snapshot is persisted as a candidate in the new Lease epoch; an identical second observation is required before it becomes the accepted baseline.
- **Restart-safe takeover confirmation.** If the new holder restarts between confirmation #1 and #2, the persisted candidate allows the next identical observation to complete revalidation without weakening the two-snapshot rule.
- **Epoch-stable writes.** Checkpoint writes require current `holderIdentity`, resourceVersion CAS, unchanged `leaseTransitions`, and an exact annotation echo in the write response.
- **Legacy checkpoint fencing.** A v1.6.3.3 continuity annotation is treated as requiring revalidation rather than being inherited as current trust.
- **Opaque resourceVersion retained.** NVIDIA object resourceVersions are still excluded from identity and never numerically or lexically ordered.
- **No RBAC expansion.** Persistence still reuses the existing Lease permission; no NVIDIA write verb is introduced.

## Safety invariants

1. A Lease holder transition invalidates direct inheritance of the previous holder's NVIDIA continuity baseline.
2. A new holder must observe the same healthy NVIDIA snapshot twice before accepting it as its own baseline.
3. A restart between those observations does not collapse the confirmation requirement.
4. Checkpoint writes fail if holder identity or Lease transition changes during the CAS operation.
5. Corrupt, malformed, unsupported, or impossible checkpoint state fails closed.
6. SHA-256 remains corruption/tamper mismatch detection only, not authentication.
7. v1.6.3.3 restart persistence, v1.6.3.2 snapshot fencing, v1.6.3.1 inventory identity checks, and all prior runtime safeguards remain active.
8. NVIDIA resources remain read-only in v1.6.3.4.
