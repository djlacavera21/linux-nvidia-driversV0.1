# nvlx: Linux-NVIDIA-Driver v1.6.2.3

`nvlx` v1.6.2.3 is a narrow post-1.6.2.2 runtime-safety hotfix. It preserves the Kubernetes API surface and NVIDIA read-only boundary while making GPUFleet inventory freshness an explicit list/watch continuity proof rather than a sticky flag from an older snapshot.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.2.3. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.2.3 hotfixes

- **Inventory freshness invalidation.** A reusable runtime layer clears `stats.inventory_fresh` whenever list/watch continuity ends or a replacement snapshot cannot be proven valid.
- **Relist starts stale.** Beginning a new list/relist immediately invalidates the previous inventory proof; only a fully validated replacement list may set inventory fresh again.
- **EOF fencing.** A clean watch EOF ends continuity for the preceding snapshot and therefore clears inventory freshness before reconnect/backoff.
- **Relist/reconnect fencing.** `410` relist signals, transient reconnects and non-retryable watch errors all invalidate the prior inventory proof before returning to the outer loop.
- **Malformed-list fencing.** A malformed replacement list cannot inherit `inventory_fresh=True` from an older successful snapshot.
- **Shutdown cleanup.** Operator shutdown clears inventory freshness together with leadership state.
- **Proof separation.** Lease leadership and inventory continuity remain separate proofs: a valid Lease may remain locally fresh across a non-transport relist signal, but readiness stays false until a new inventory snapshot is validated.
- **Prior safeguards retained.** Immediate leadership invalidation on API loss, Lease clock-skew fencing, timezone-aware Lease freshness, 20-second Kubernetes watch lifetime, 25-second watch socket timeout, conflict-safe status/finalizer recomputation, UID-bound mutation verification, token-file auth, opaque resourceVersion semantics and verified Lease writes remain active.

## Safety invariants

1. `inventory_fresh` represents an active validated list/watch continuity window, not merely a previously successful list.
2. Starting a relist clears the previous inventory proof before the replacement list is fetched and validated.
3. EOF, reconnect, relist and watch-error outcomes cannot leave stale inventory marked fresh during backoff.
4. A malformed or failed replacement list cannot reuse an older inventory-fresh state.
5. Leadership freshness and inventory freshness are independent readiness requirements.
6. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
7. Conflict retries remain bounded and leadership-fenced.
8. NVIDIA resources remain read-only in v1.6.2.3.
9. All v0.1-v1.6.2.2 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay, UID-integrity and Lease-CAS safeguards remain in force.
