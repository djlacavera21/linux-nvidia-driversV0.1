# nvlx: Linux-NVIDIA-Driver v1.6.3.7

`nvlx` v1.6.3.7 adds independent read-after-write verification to the replay-fenced Lease-backed NVIDIA continuity checkpoint.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.3.7 checkpoint readback verification

- **Independent GET after write.** A successful checkpoint PATCH is not sufficient by itself; the store performs a fresh Lease GET before reporting success.
- **Leadership is re-proved.** The readback Lease must still be held by the current controller identity.
- **Lease epoch is re-proved.** `leaseTransitions` must exactly match the epoch used for the committed checkpoint.
- **Sequence floor is re-proved.** The retained floor must exactly equal the sequence just written.
- **Checkpoint contents are re-proved.** Baseline, candidate, Lease transition and sequence must decode to the exact committed state.
- **Canonical envelope is re-proved.** The persisted v3 envelope must exactly match the canonical integrity-checked encoding.
- **Fail closed on readback loss or mismatch.** A missing/malformed checkpoint, leadership loss, epoch change, floor mismatch, or state mismatch causes persistence failure.
- **Existing replay and restore fences remain active.** v1.6.3.5 replay-floor protection and v1.6.3.6 atomic restore semantics are unchanged.
- **No RBAC expansion.** The extra verification uses the Lease GET permission already required by leader election/checkpoint persistence.

## Safety invariants

1. Checkpoint persistence is successful only after an independent Kubernetes readback proves the committed state.
2. A PATCH response alone cannot establish durable checkpoint success.
3. Leadership and Lease transition epoch must remain unchanged through readback.
4. Checkpoint sequence and retained floor must remain equal.
5. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
6. NVIDIA continuity baseline/candidate semantics and takeover revalidation remain unchanged.
7. No NVIDIA driver/GPU Operator mutation path is introduced.
8. NVIDIA resources remain read-only in v1.6.3.7.
