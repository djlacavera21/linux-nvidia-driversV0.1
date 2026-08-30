# nvlx: Linux-NVIDIA-Driver v1.6.3.6

`nvlx` v1.6.3.6 strengthens the replay-fenced Lease-backed NVIDIA continuity checkpoint by binding persisted trust to both the Lease transition epoch and the exact holder identity that wrote it.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.3.6 holder-bound checkpoint

- **Holder-bound envelope.** The continuity checkpoint now records the exact Lease `holderIdentity` alongside the Lease transition epoch and monotonic sequence.
- **Same-epoch holder mismatch fencing.** If the live Lease holder differs from the checkpoint writer even when `leaseTransitions` did not advance, the checkpoint is treated as stale and must pass the existing two-observation takeover revalidation.
- **Verified write identity.** Successful writes require the same holder identity and Lease transition epoch before and after the resourceVersion-CAS PATCH.
- **No direct foreign-holder advancement.** A current v4 checkpoint written by another holder cannot be advanced directly by a new holder; stale-state revalidation must occur first.
- **Replay floor retained.** The v1.6.3.5 monotonic checkpoint sequence and retained sequence-floor annotation remain authoritative consistency witnesses.
- **Safe v3 migration.** A v1.6.3.5/v3 checkpoint can migrate to v4 without resetting the monotonic sequence; legacy v3 state is always marked stale and revalidated before trust is inherited.
- **Opaque resourceVersion retained.** Kubernetes resourceVersion remains a CAS token only and is never treated as an ordered continuity identity.
- **No RBAC expansion.** The patch reuses the existing Lease permissions and adds no NVIDIA write verbs or storage resources.

## Safety invariants

1. Persisted NVIDIA continuity trust is bound to both Lease transition epoch and exact holder identity.
2. A holder change without a transition-counter change cannot silently inherit the previous holder's accepted baseline.
3. v4 checkpoint/floor disagreement fails closed in either direction.
4. v3 migration preserves sequence monotonicity and requires revalidation.
5. Holder identity and transition epoch must remain stable through every verified checkpoint write.
6. SHA-256 remains corruption/tamper mismatch detection only, not authentication.
7. All v1.6.3.5 replay fencing, v1.6.3.4 takeover revalidation, and earlier inventory/watch/Lease safeguards remain active.
8. NVIDIA resources remain read-only in v1.6.3.6.
