# nvlx: Linux-NVIDIA-Driver v1.6.1.9

`nvlx` v1.6.1.9 is a narrow runtime-identity hotfix on top of v1.6.1.8. It keeps the same controller API surface and NVIDIA read-only boundary while making Kubernetes GPUFleet UID continuity mandatory across list/watch/reconcile and controller-owned mutation verification.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.1.9. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.1.9 hotfixes

- **Mandatory GPUFleet UID identity.** Live GPUFleet objects now require non-empty `metadata.name`, `metadata.uid`, and `metadata.resourceVersion` before entering reconciliation, list snapshot acceptance, or watch processing.
- **No name-only watch fallback.** Watch state is keyed only by Kubernetes UID. The old `name:<name>` fallback is removed, eliminating cross-incarnation ambiguity when a same-name GPUFleet is deleted and recreated.
- **Status response UID binding.** A successful status PATCH response must echo the exact expected GPUFleet UID in addition to name/resourceVersion and controller-owned status fields.
- **Conflict refetch UID binding.** A 409/412 recovery refetch without the original UID, or with a replacement UID, cannot authorize retry of the old status plan.
- **Finalizer response UID binding.** Runtime finalizer completion is verified against the exact GPUFleet UID as well as name, resourceVersion, protective-finalizer absence, and exact unrelated-finalizer preservation.
- **Whitespace identity rejection.** Blank/whitespace-only names, UIDs, and resourceVersion values fail closed rather than entering cache or mutation paths.
- **Regression coverage.** Tests cover missing/blank UID rejection, list/watch suppression for UID-less objects, status response UID echo, conflict-refetch UID continuity, and finalizer UID continuity.
- **Prior safeguards retained.** Bounded/pruned watch cache lifecycle, deferred-reconcile retry preservation, opaque resourceVersion semantics, generation regression fencing, Event attribution, mutation response verification, reflected-token redaction, deterministic reconnects, and shutdown fencing remain active.

## Safety invariants

1. A GPUFleet without a stable Kubernetes UID cannot enter the live reconcile or watch-state machinery.
2. Same-name object replacement cannot inherit cache or mutation verification through a name-only fallback.
3. Status conflict recovery cannot retry an old plan against an object whose UID is absent or changed.
4. Finalizer completion is bound to the exact GPUFleet incarnation being finalized.
5. Kubernetes resourceVersion remains opaque and is never numerically or lexically ordered.
6. Deferred list work remains retry-eligible rather than being hidden by duplicate suppression.
7. Every controller-owned Kubernetes mutation remains fenced by live leadership.
8. NVIDIA resources remain read-only in v1.6.1.9.
9. All v0.1-v1.6.1.8 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay and Lease-CAS safeguards remain in force.
