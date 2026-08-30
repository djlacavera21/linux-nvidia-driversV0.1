# nvlx: Linux-NVIDIA-Driver v1.6.4

`nvlx` v1.6.4 unifies NVIDIA continuity checkpoint persistence so normal state changes and Lease-transition revalidation use the same sequence-, epoch-, replay-, and idempotency-fenced transaction path.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.4 unified checkpoint transactions

- **One persistence transaction path.** Normal NVIDIA continuity baseline/candidate updates now route through the same `_save_epoch_state()` transaction gate already used by Lease-transition revalidation.
- **Runtime sequence state stays synchronized.** Successful normal checkpoint writes now update the runtime's accepted Lease epoch and checkpoint sequence instead of bypassing those fields.
- **Idempotent acknowledgements work everywhere.** The v1.6.3.8 exact-state reconciliation proof and v1.6.3.9 equal-sequence acknowledgement logic now apply to normal continuity persistence as well as takeover revalidation.
- **Rollback fencing applies everywhere.** A lower checkpoint sequence returned during normal persistence is detected, counted, and rejected just like a lower sequence on the epoch-revalidation path.
- **Unproven equal sequences fail closed everywhere.** A store that does not explicitly prove idempotent commits cannot return a non-advancing sequence successfully on either persistence path.
- **Cross-epoch reuse remains forbidden.** Equal-sequence acknowledgements still require the current Lease transition epoch.
- **Transaction state is bound to runtime state.** `_persist_checkpoint()` rejects a stale baseline/candidate argument pair that does not exactly match the runtime state being committed.
- **Mismatch observability.** `nvidia_checkpoint_transaction_mismatches` counts attempts to persist state that no longer matches the runtime's active continuity state.
- **No checkpoint format or RBAC change.** v1.6.4 retains the v3 integrity envelope, sequence-floor annotation, Lease GET/PATCH permissions, and all earlier readback/reconciliation protections.

## Safety invariants

1. Every durable NVIDIA continuity state change uses the same runtime checkpoint transaction gate.
2. A normal checkpoint write cannot bypass sequence monotonicity, Lease epoch validation, or idempotent proof requirements.
3. Persisted baseline/candidate arguments must match the runtime's active continuity state exactly.
4. Lower sequences always fail closed and are counted as rollback attempts.
5. Equal sequences require positive sequence, current Lease epoch, and explicit idempotent proof.
6. Replay fencing, atomic restore, independent readback, ambiguous-write reconciliation, and takeover revalidation remain active.
7. No NVIDIA driver/GPU Operator mutation path is introduced.
8. NVIDIA resources remain read-only in v1.6.4.
