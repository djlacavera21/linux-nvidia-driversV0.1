# nvlx: Linux-NVIDIA-Driver v1.6.1.4

`nvlx` v1.6.1.4 is a narrow runtime-safety hotfix on top of v1.6.1.3. It keeps the same controller API surface and NVIDIA read-only boundary while tightening successful mutation-response continuity and exact finalizer preservation.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.1.4. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.1.4 hotfixes

- **Status response UID continuity.** A successful status PATCH response that identifies a different GPUFleet UID is rejected instead of being counted as a verified write.
- **Status response generation continuity.** When the API response carries generation metadata, it must match the generation associated with the planned write.
- **Status echo verification retained.** Controller-owned status fields must still echo the values written before reconciliation is reported successful.
- **Exact unrelated-finalizer preservation.** Finalizer PATCH success now requires the returned finalizer list to exactly match the unrelated finalizers the controller intended to preserve, in addition to proving `nvlx.io/fleet-protection` is absent.
- **Finalizer loss/reordering detection.** Dropped, injected, or reordered unrelated finalizers cause the completion check to fail closed.
- **Regression coverage.** Tests cover UID mismatch, generation mismatch, valid continuity, missing unrelated finalizers, reordered finalizers, exact preservation, and protective-finalizer persistence.
- **Prior safeguards retained.** Conflict refetch name/UID/generation verification, verified mutation metadata, strict list/watch validation, bookmark hardening, Event fencing, reflected-token redaction, deterministic reconnects, shutdown fencing, and finalizer safety remain active.

## Safety invariants

1. A status mutation is not reported verified when the returned object represents a different GPUFleet incarnation.
2. A returned generation mismatch cannot be accepted as confirmation of an old planned status write.
3. Unrelated finalizers must survive protective-finalizer removal exactly as planned.
4. HTTP success without coherent mutation continuity remains fail-closed.
5. Every controller-owned Kubernetes mutation remains fenced by live leadership.
6. NVIDIA resources remain read-only in v1.6.1.4.
7. All v0.1-v1.6.1.3 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay and Lease-CAS safeguards remain in force.
