# nvlx: Linux-NVIDIA-Driver v1.6.5

`nvlx` v1.6.5 hardens idempotent NVIDIA continuity checkpoint acknowledgements by replacing coarse store-class capability trust with a typed proof returned by the exact checkpoint save call.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.5 per-call checkpoint commit receipts

- **Every modern checkpoint save can return a typed receipt.** `CheckpointCommitReceipt` carries the Lease transition epoch, sequence, idempotent-reuse flag, ambiguous-write reconciliation flag and SHA-256 of the exact canonical checkpoint envelope.
- **Equal-sequence acknowledgements require proof from that call.** The v1.6.5 runtime no longer accepts a non-advancing checkpoint merely because a store advertises `proves_idempotent_commits` at class level.
- **Canonical state is bound into the proof.** The runtime recomputes the canonical checkpoint envelope from its current baseline/candidate plus the returned epoch and sequence, hashes it, and requires an exact digest match before trusting the receipt.
- **Ambiguous writes remain recoverable.** A timeout or transport failure after a successful commit can still be reconciled by a fresh Lease read; the resulting receipt explicitly records `idempotent=True` and `reconciled=True`.
- **Exact pre-existing commits are explicit.** A save that finds the requested canonical state already committed returns an idempotent receipt without rewriting the Lease.
- **New writes are distinguishable.** A freshly advanced checkpoint returns `idempotent=False` and `reconciled=False`.
- **The historical tuple API remains available.** `LeaseCheckpointStore.save()` still returns `(lease_transition, sequence)` for older callers.
- **Tuple-only custom stores remain compatible for advancing sequences.** They may continue to advance the checkpoint sequence, but they cannot prove an equal-sequence acknowledgement under the v1.6.5 runtime.
- **Rollback and cross-epoch fences remain unchanged.** Lower sequences still fail closed and equal sequences from a different Lease epoch remain invalid.
- **The live operator now uses the v1.6.5 receipt-aware store and runtime.** Existing readiness telemetry, Prometheus exposition, checkpoint readback verification and replay-floor behavior remain intact.
- **No RBAC expansion.** The receipt is an in-process proof object derived from state already read or written through the existing Lease path.

## Commit receipt contract

A `CheckpointCommitReceipt` contains:

- `lease_transition` — the verified Lease transition epoch;
- `sequence` — the verified checkpoint sequence;
- `idempotent` — whether this call reused a canonical commit that already existed;
- `reconciled` — whether that reuse was established after an ambiguous write outcome;
- `canonical_sha256` — SHA-256 of the exact canonical checkpoint envelope for the saved runtime state.

`reconciled=True` is valid only when `idempotent=True`.

## Safety invariants

1. A non-advancing checkpoint sequence is accepted only with a valid per-call `CheckpointCommitReceipt` marked idempotent.
2. The receipt digest must match the runtime's exact canonical baseline/candidate, Lease epoch and sequence.
3. A class-level capability flag alone cannot authorize an equal-sequence acknowledgement in the v1.6.5 runtime.
4. Equal-sequence acknowledgements from another Lease epoch remain rejected.
5. Lower checkpoint sequences remain rollback failures and continue to increment rollback telemetry.
6. Fresh advancing writes remain compatible with tuple-only stores.
7. The legacy `(epoch, sequence)` store API remains available for older callers.
8. Readiness, leadership snapshot closure, Prometheus HELP/TYPE metadata and UTF-8 exposition remain unchanged.
9. No new Kubernetes mutation path or RBAC permission is introduced.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.5.
