# nvlx: Linux-NVIDIA-Driver v1.6.3.8

`nvlx` v1.6.3.8 makes Lease-backed NVIDIA continuity checkpoint persistence idempotent across ambiguous API write outcomes.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.3.8 idempotent checkpoint commit reconciliation

- **Already-committed state is recognized.** Before writing, the store checks whether the current Lease already contains the exact requested baseline/candidate state for the active Lease transition.
- **No duplicate sequence advance for identical state.** If the canonical checkpoint and retained floor already prove the requested state, the existing `(leaseTransition, sequence)` is returned without another PATCH.
- **Ambiguous write outcomes are reconciled.** If a PATCH or its v1.6.3.7 verification path raises after the server may have committed the change, the store performs a fresh reconciliation GET.
- **Timeout-after-commit can recover safely.** Reconciliation succeeds only when the current Lease independently proves the exact canonical checkpoint, current holder identity, current Lease epoch and retained sequence floor.
- **Timeout-before-commit remains fail-closed.** If the intended checkpoint cannot be proven after an ambiguous failure, persistence fails instead of assuming success.
- **Leadership remains mandatory.** Reconciliation refuses success if the Lease is no longer held by the current controller identity.
- **Epoch and replay fences remain intact.** A checkpoint from an older Lease transition is never mistaken for a current idempotent commit, and sequence/floor mismatch still fails closed.
- **v1.6.3.7 readback verification remains active.** New writes still require the independent post-write GET and canonical content verification introduced in v1.6.3.7.
- **No RBAC expansion.** Reconciliation uses the same Lease GET/PATCH permissions already required by leader election and checkpoint persistence.

## Safety invariants

1. An identical current checkpoint may be reused only when holder identity, Lease transition, sequence floor and canonical payload all agree.
2. An ambiguous API failure is considered successful only if a later independent GET proves the exact intended state.
3. Reconciliation cannot manufacture or advance a checkpoint sequence.
4. A missing, malformed, stale-epoch, mismatched or differently owned Lease remains fail-closed.
5. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
6. Replay fencing, Lease-transition revalidation and atomic restore semantics remain unchanged.
7. No NVIDIA driver/GPU Operator mutation path is introduced.
8. NVIDIA resources remain read-only in v1.6.3.8.
