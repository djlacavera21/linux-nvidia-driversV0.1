# nvlx: Linux-NVIDIA-Driver v1.6.2

`nvlx` v1.6.2 is the first broader runtime-hardening release after the v1.6.1.x patch train. It preserves the current Kubernetes API surface and NVIDIA read-only boundary while closing stale conflict-retry behavior, adding conflict-safe finalizer recovery, bounding watch lifetimes, hardening bearer-token input, and verifying Lease ownership after Kubernetes writes.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.2. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.2 hardening

- **True status conflict recomputation.** A `409`/`412` status conflict triggers one fresh GPUFleet GET. The runtime verifies the same name/UID incarnation, rejects deletion or approval transitions, recomputes the operator plan against the fresh generation/resourceVersion, rechecks live leadership, and performs at most one retry.
- **Fresh-generation status.** A same-UID generation increase can now retry with a recomputed status whose `observed_generation` matches the fresh object instead of replaying stale status or blindly fencing every generation change.
- **Approval/deletion conflict fencing.** If approval state changes or deletion begins during conflict recovery, the original status mutation is abandoned rather than translated into a new write inside the stale reconcile attempt.
- **Finalizer conflict recovery.** Finalizer `409`/`412` responses now refetch the same UID, recompute rollback/quarantine/active-execution safety from the fresh object, preserve the fresh unrelated finalizer list exactly, recheck leadership, and retry at most once.
- **Bounded Kubernetes watches.** Normal API requests and watch socket reads have separate timeouts. Watch URLs include Kubernetes `timeoutSeconds`, while the client socket timeout must be longer than the server-side watch lifetime.
- **Safer bearer-token input.** `nvlx-operator` adds `--token-file` as a mutually exclusive alternative to `--token`, avoiding bearer tokens in normal process argument listings. In-cluster mode continues to use the mounted service-account token.
- **Verified Lease ownership.** Lease create/renew/takeover succeeds only when the Kubernetes response contains a non-empty resourceVersion, the expected holder identity and duration, valid transition state, and a fresh timestamp.
- **Lease state fail-closed checks.** Malformed Lease bodies, invalid transition counters, missing resourceVersion, fresh competing holders, CAS conflicts, and unverifiable write responses all return non-leader state.
- **Expanded regression coverage.** Tests cover generation-aware status recomputation, approval/deletion conflict fencing, finalizer conflict recovery and safety changes, watch timeout configuration, token-file handling, Lease creation, competing-holder refusal, stale takeover, and CAS failure.

## Safety invariants

1. Status conflict recovery never replays a pre-conflict status payload against a fresh generation.
2. A changed GPUFleet UID, approval transition, or newly deleting object fences status retry.
3. Finalizer conflict recovery re-evaluates fresh safety state and preserves unrelated finalizers from the fresh object.
4. Conflict retries are bounded to one retry and recheck live Lease leadership immediately before mutation.
5. Kubernetes `resourceVersion` remains opaque and is used only as an equality/CAS token, never numerically or lexically ordered.
6. Watches have an explicit server lifetime and a longer client-side socket timeout.
7. External bearer tokens can be loaded from a file instead of being exposed in normal CLI argument listings.
8. Lease leadership is accepted only after a verifiable Kubernetes response proves this identity holds a fresh Lease.
9. GPUFleet UID identity, bounded/pruned watch caching, deferred-reconcile retry preservation, Event attribution, mutation-response verification, reflected-token redaction, deterministic reconnects, and shutdown fencing remain active.
10. NVIDIA resources remain read-only in v1.6.2.
11. All v0.1-v1.6.1.9 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay and Lease-CAS safeguards remain in force.
