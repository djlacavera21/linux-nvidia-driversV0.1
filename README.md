# nvlx: Linux-NVIDIA-Driver v1.5.7

`nvlx` v1.5.7 is a seventh stabilization patch for the live Kubernetes operator. It adds integrity-checked persisted fencing state and rollback-aware startup recovery so a restarted controller cannot regain mutation authority from tampered, stale, or logically regressed Lease state.

> [!IMPORTANT]
> Persisted fencing state remains evidence only. A restored token must pass file-integrity verification and then match the live Lease holder, fencing epoch, Lease `resourceVersion`, and freshness before controller-owned mutation is allowed.

## v1.5.7 fixes

- **Integrity envelope.** Newly persisted fence tokens are wrapped in a versioned SHA-256 integrity envelope and verified before reload.
- **Durability tightening.** Fence-state replacement now also `fsync`s the containing directory after atomic replacement.
- **Legacy compatibility.** Existing v1.5.6 token files remain readable, but newly written state uses the integrity envelope.
- **Tamper detection.** A modified token whose integrity digest no longer matches fails closed instead of being accepted at startup.
- **Rollback-aware recovery.** Startup distinguishes exact restoration, older persisted epochs that require reacquisition, and a live Lease epoch lower than persisted state, which is surfaced as `rollback-detected`.
- **Live revalidation.** Even integrity-valid persisted state must exactly match current Lease holder/epoch/resourceVersion/freshness before mutation authority is restored.
- **Regression coverage.** Tests cover tampered envelopes, legacy state, exact restore, newer-epoch reacquisition, missing state, and epoch rollback detection.
- **1.5.6 retained.** Atomic persistence, renewal-race fencing, stale-leader blocking, fence-drain behavior, duplicate-event suppression, bounded jitter, ordered finalization, and status-write idempotency remain active.

## Safety invariants

1. Integrity-valid persisted state still cannot authorize mutation without live Lease revalidation.
2. Tampered or malformed persisted fencing state fails closed.
3. A newer live leadership epoch invalidates an older persisted token and forces reacquisition.
4. A live leadership epoch lower than the persisted epoch is treated as a rollback condition, not silently accepted.
5. Directory metadata is flushed after atomic fence-state replacement to tighten crash durability.
6. All v0.1-v1.5.6 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM and provenance safeguards remain in force.
