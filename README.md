# nvlx: Linux-NVIDIA-Driver v1.6.1.2

`nvlx` v1.6.1.2 is a narrow runtime-verification hotfix on top of v1.6.1.1. It keeps the same controller API surface and NVIDIA read-only boundary while tightening how successful Kubernetes responses and list/watch payloads are trusted.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.1.2. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.1.2 hotfixes

- **Mutation response verification.** A successful HTTP status is not enough by itself. GPUFleet status/finalizer writes and Event creation must return an object with metadata and a non-empty `resourceVersion` before the runtime treats the write as verified.
- **Object identity verification.** GPUFleet mutation responses that identify a different object name fail closed rather than being counted as successful reconciliation.
- **Strict list payload validation.** GPUFleet list bodies and list metadata must be JSON objects, `resourceVersion` must be a non-empty string, and `items` must be a list before inventory freshness is asserted.
- **Bookmark hardening.** Malformed bookmark metadata cannot overwrite the active watch cursor.
- **Object metadata hardening.** Reconcile inputs require object metadata plus string name/resourceVersion identity before entering any mutation path.
- **Regression coverage.** Tests cover missing mutation metadata, wrong-object success responses, malformed list bodies/metadata, malformed bookmarks, and invalid object identity.
- **Prior safeguards retained.** Live Event fencing, reflected-token redaction, timeout normalization, watch error classification, deterministic reconnects, conflict-time leadership checks, shutdown fencing, and finalizer safety remain active.

## Safety invariants

1. A 2xx response with malformed or missing Kubernetes metadata cannot authorize a successful reconciliation result.
2. A mutation response for the wrong GPUFleet name is rejected.
3. Inventory is not marked fresh until list metadata, `resourceVersion`, and item structure are validated.
4. Malformed bookmarks cannot poison the stored watch cursor.
5. Every controller-owned Kubernetes mutation remains fenced by live leadership.
6. NVIDIA resources remain read-only in v1.6.1.2.
7. All v0.1-v1.6.1.1 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay and Lease-CAS safeguards remain in force.
