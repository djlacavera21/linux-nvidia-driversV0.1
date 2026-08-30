# nvlx: Linux-NVIDIA-Driver v1.6.3.6

`nvlx` v1.6.3.6 closes a fail-open restart edge in the replay-fenced Lease-backed NVIDIA continuity checkpoint introduced across v1.6.3.3-v1.6.3.5.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.3.6 atomic checkpoint restore

- **Restore guard is success-bound.** `nvidia_checkpoint_loaded` is set only after the Lease checkpoint has been fully read and validated.
- **Retry after transient failure.** A failed restore leaves the guard false, so the next NVIDIA preflight retries the persisted checkpoint instead of skipping restoration.
- **No first-observation fallback after corruption.** Repeated malformed/corrupt checkpoint reads continue to fail closed; they cannot degrade into an empty baseline that trusts the next observed NVIDIA state.
- **Atomic in-memory assignment.** Baseline, candidate, Lease epoch, stale-epoch flag, and replay sequence are first loaded into locals and committed to runtime state only after the store returns successfully.
- **State preservation on failure.** Existing in-memory continuity state is not partially overwritten when restore fails.
- **Restore observability.** Runtime counters expose restore attempts and successful restores for tests and operational introspection.
- **Replay fencing retained.** v1.6.3.5 sequence/floor checks, v1.6.3.4 Lease-transition revalidation, and all earlier continuity gates remain active.
- **No checkpoint format change.** v1.6.3.6 continues to use the v3 Lease checkpoint and sequence-floor annotations from v1.6.3.5.
- **No RBAC expansion.** The patch adds no permissions or Kubernetes storage resources.

## Safety invariants

1. A failed checkpoint restore can never mark persistence as successfully loaded.
2. A later preflight must retry restoration after a transient or validation failure.
3. Corrupt persisted state remains fail-closed on every retry until corrected.
4. Restore failure cannot erase or partially replace the current in-memory baseline/candidate/epoch/sequence.
5. Replay sequence and retained-floor checks remain unchanged and Kubernetes `resourceVersion` remains opaque.
6. Lease holder/transition fencing and two-snapshot takeover revalidation remain active.
7. No NVIDIA driver/GPU Operator mutation path is introduced.
8. NVIDIA resources remain read-only in v1.6.3.6.
