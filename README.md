# nvlx: Linux-NVIDIA-Driver v1.6.1.3

`nvlx` v1.6.1.3 is a narrow runtime-safety hotfix on top of v1.6.1.2. It keeps the same controller API surface and NVIDIA read-only boundary while tightening conflict recovery and post-write completion verification.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.1.3. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.1.3 hotfixes

- **Conflict refetch identity verification.** After a `409`/`412`, the runtime verifies that the refetched GPUFleet still has the same name and UID before any retry can occur.
- **Generation-change fencing.** A conflict refetch with a different generation blocks retry of the old planned status. The newer watch/list state must be reconciled separately rather than applying a stale plan to a new spec generation.
- **Status echo verification.** A 2xx status PATCH is only treated as verified when the response contains coherent metadata and echoes the controller-owned status fields that were written.
- **Finalizer completion verification.** A finalizer PATCH is only reported as complete when the returned metadata contains a valid finalizer list and `nvlx.io/fleet-protection` is actually absent.
- **Regression coverage.** Tests cover same-generation conflict retry, generation drift, UID replacement, mismatched status echoes, finalizer still-present responses, and malformed finalizer completion payloads.
- **Prior safeguards retained.** Verified mutation metadata, strict list/watch validation, bookmark hardening, live Event fencing, reflected-token redaction, timeout normalization, deterministic reconnects, shutdown fencing, and finalizer safety remain active.

## Safety invariants

1. A stale status plan is not retried after a conflict if the GPUFleet generation changed.
2. A deleted-and-recreated GPUFleet with a new UID cannot inherit a retry intended for the prior object.
3. A successful status response must confirm the status fields the controller attempted to write.
4. Finalizer removal is not reported complete unless the protective finalizer is absent in the API response.
5. Every controller-owned Kubernetes mutation remains fenced by live leadership.
6. NVIDIA resources remain read-only in v1.6.1.3.
7. All v0.1-v1.6.1.2 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay and Lease-CAS safeguards remain in force.
