# nvlx: Linux-NVIDIA-Driver v1.6.3.5

`nvlx` v1.6.3.5 adds replay fencing to the Lease-backed NVIDIA continuity checkpoint introduced in v1.6.3.3 and bound to Lease transition epochs in v1.6.3.4.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.3.5 checkpoint replay fencing

- **Monotonic checkpoint sequence.** Every accepted checkpoint write advances an integer sequence exactly once.
- **Independent retained floor.** The current sequence is mirrored into a separate Lease annotation and updated atomically with the checkpoint.
- **Replay rejection.** A valid integrity-wrapped checkpoint whose sequence is below the retained floor fails closed as stale/replayed state.
- **Split-state rejection.** A checkpoint whose sequence is ahead of the retained floor also fails closed; the checkpoint and floor must agree exactly.
- **Write precondition.** Existing checkpoint and floor values must agree before a new sequence may be allocated.
- **Verified write response.** Success requires current holder identity, unchanged Lease transition epoch, non-empty returned resourceVersion, exact checkpoint echo, and exact sequence-floor echo.
- **Runtime monotonicity check.** The running controller additionally requires every successful persisted sequence to be strictly greater than the last sequence it restored or wrote.
- **Legacy revalidation retained.** Older v1/v2 continuity annotations remain fenced for revalidation rather than silently promoted.
- **No RBAC expansion.** The extra state is stored on the existing Lease under the permissions already required for leader election.

## Safety invariants

1. A stale checkpoint annotation cannot be accepted when its sequence is below the retained floor.
2. Checkpoint/floor disagreement fails closed in either direction.
3. A normal controller write advances the sequence exactly once under Lease resourceVersion CAS.
4. Lease holder identity and transition epoch must remain stable through the write.
5. The replay floor is an independent consistency witness inside the same Lease, not a defense against an actor able to arbitrarily rewrite the entire Lease object.
6. SHA-256 remains corruption/tamper mismatch detection only, not authentication.
7. v1.6.3.4 takeover revalidation and all prior continuity, inventory, watch, cursor, finalizer, Lease, and leadership safeguards remain active.
8. NVIDIA resources remain read-only in v1.6.3.5.
