# nvlx: Linux-NVIDIA-Driver v1.6.2.6

`nvlx` v1.6.2.6 is a narrow post-1.6.2.5 correctness hotfix. It preserves the Kubernetes API surface and NVIDIA read-only boundary while changing unrelated-finalizer verification from order-sensitive list equality to duplicate-free semantic preservation.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.2.6. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.2.6 hotfixes

- **Semantic finalizer preservation.** Successful finalizer completion now accepts harmless reordering of unrelated finalizers when the returned set is otherwise identical.
- **Drop/injection rejection.** Missing or unexpected unrelated finalizers still fail closed.
- **Duplicate rejection.** Duplicate returned finalizers are rejected, and duplicate source finalizers fail the finalizer plan before mutation is attempted.
- **Protective-finalizer rejection.** A response that still contains `nvlx.io/fleet-protection` cannot count as successful finalization.
- **Generation binding retained.** Finalizer responses must still prove the exact GPUFleet generation used for the write, including after `409/412` refetch/recompute.
- **Identity binding retained.** Name, UID and non-empty resourceVersion remain mandatory for verified mutation completion.
- **Status safeguards retained.** Status PATCH success still requires exact returned generation and intended controller-owned status fields.
- **Watch and readiness safeguards retained.** Watch-corruption relists, inventory-continuity invalidation, Lease freshness, leadership invalidation, token-file auth and opaque resourceVersion semantics remain unchanged.

## Safety invariants

1. Unrelated finalizers are compared semantically, not by list order.
2. Both expected and returned finalizer collections must be duplicate-free lists of non-empty strings.
3. Dropped, injected, duplicated, or still-protective finalizers fail closed.
4. Duplicate source finalizers prevent a finalizer mutation plan from being issued.
5. Finalizer completion remains bound to exact name, UID, resourceVersion presence and generation continuity.
6. Status mutation verification remains generation-bound and status-echo verified.
7. Kubernetes `resourceVersion` remains opaque and is never numerically or lexically ordered.
8. Malformed state-bearing watch content still forces a trusted relist.
9. Leadership freshness and inventory freshness remain independent readiness requirements.
10. Conflict retries remain bounded and leadership-fenced.
11. NVIDIA resources remain read-only in v1.6.2.6.
12. All v0.1-v1.6.2.5 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay, UID-integrity, Lease-CAS, leadership-freshness, inventory-continuity, watch-trust and generation-verification safeguards remain in force.
