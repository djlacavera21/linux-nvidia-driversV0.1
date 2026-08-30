# nvlx: Linux-NVIDIA-Driver v1.6.3.9

`nvlx` v1.6.3.9 aligns runtime sequence handling with the idempotent Lease checkpoint reconciliation introduced in v1.6.3.8.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.3.9 runtime idempotent checkpoint acknowledgements

- **Runtime and store semantics now agree.** v1.6.3.8 can prove that an identical checkpoint is already durably committed without advancing its sequence; v1.6.3.9 allows the runtime to accept that proven non-advancing acknowledgement.
- **Proof capability is explicit.** The v1.6.3.8 Lease checkpoint store advertises `proves_idempotent_commits`, and equal-sequence acknowledgements are rejected from stores that do not provide that guarantee.
- **True rollback still fails closed.** A returned sequence lower than the runtime's last accepted sequence is rejected and counted as a checkpoint rollback.
- **Cross-epoch sequence reuse is rejected.** Even a proven equal sequence cannot be accepted if the Lease transition epoch differs from the runtime's current checkpoint epoch.
- **Sequence zero cannot be acknowledged idempotently.** Equal-sequence reuse is valid only for positive persisted checkpoint sequences.
- **New writes retain normal monotonic behavior.** Any sequence greater than the current sequence is handled as a normal durable checkpoint write and advances runtime state.
- **Observability is expanded.** Runtime counters distinguish normal writes, proven idempotent acknowledgements, and detected sequence rollbacks.
- **v1.6.3.8 reconciliation remains unchanged.** Exact canonical payload, holder identity, Lease epoch and retained sequence floor are still independently proved before a checkpoint can be reused.
- **No RBAC expansion.** The release requires no additional Kubernetes permissions or resources.

## Safety invariants

1. A non-advancing sequence is accepted only from a store that explicitly provides idempotent commit proof.
2. Equal sequence reuse requires the same positive sequence and the same Lease transition epoch.
3. A lower sequence is always treated as rollback and fails closed.
4. An unproven equal sequence is never treated as success.
5. New checkpoint writes must still advance the sequence monotonically.
6. Replay fencing, independent readback, ambiguous-write reconciliation and atomic restore semantics remain active.
7. No NVIDIA driver/GPU Operator mutation path is introduced.
8. NVIDIA resources remain read-only in v1.6.3.9.
