# nvlx: Linux-NVIDIA-Driver v1.6.2.5

`nvlx` v1.6.2.5 is a narrow post-1.6.2.4 runtime-safety hotfix. It preserves the Kubernetes API surface and NVIDIA read-only boundary while requiring successful GPUFleet mutation responses to prove generation continuity instead of accepting a 2xx response whose object generation is missing or inconsistent.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.2.5. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.2.5 hotfixes

- **Status generation proof.** A successful GPUFleet status PATCH must now return `metadata.generation`, and it must exactly match the generation of the object used to compute the status write.
- **Missing-generation fail closed.** A 2xx status response with correct name, UID, resourceVersion and status data is still rejected if generation evidence is absent.
- **Finalizer generation proof.** Successful finalizer PATCH completion is now bound to the exact GPUFleet generation used for that mutation, in addition to existing name, UID and unrelated-finalizer preservation checks.
- **Conflict retry generation binding.** After a finalizer `409/412`, the runtime may refetch a newer generation of the same UID and recompute the finalizer decision, but the retry only succeeds if the response proves that fresh generation exactly.
- **Malformed generation rejection.** Missing, negative, boolean, or non-integer generation evidence does not satisfy mutation verification.
- **Prior watch safeguards retained.** Malformed state-bearing watch deliveries still force trusted relists; inventory and leadership freshness proofs remain fail-closed and independent.
- **Prior mutation safeguards retained.** Conflict-safe status/finalizer recomputation, UID-bound verification, exact unrelated-finalizer preservation, bounded retries, token-file auth, opaque resourceVersion semantics and verified Lease writes remain active.

## Safety invariants

1. Successful status mutation is not trusted without exact returned GPUFleet generation evidence.
2. Finalizer completion is not trusted without exact returned generation evidence for the object used for that write.
3. A finalizer conflict retry may follow a newer generation only after a fresh same-UID refetch and recomputation; success is bound to that fresh generation.
4. Name, UID, resourceVersion and intended status/finalizer verification remain required alongside generation continuity.
5. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
6. Malformed state-bearing watch content still forces a trusted relist.
7. Leadership freshness and inventory freshness remain independent readiness requirements.
8. Conflict retries remain bounded and leadership-fenced.
9. NVIDIA resources remain read-only in v1.6.2.5.
10. All v0.1-v1.6.2.4 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay, UID-integrity, Lease-CAS, leadership-freshness, inventory-continuity and watch-trust safeguards remain in force.
