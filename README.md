# nvlx: Linux-NVIDIA-Driver v1.5.8

`nvlx` v1.5.8 is an eighth stabilization patch for the live Kubernetes operator. It makes persisted fencing state monotonic so a stale disk snapshot, same-epoch holder collision, or reacquisition that fails to advance leadership cannot re-enter the controller mutation path.

> [!IMPORTANT]
> Persisted fencing state remains evidence only. Integrity verification, live Lease validation, leadership freshness, and monotonic fencing checks all have to pass before controller-owned mutation authority can continue.

## v1.5.8 fixes

- **Monotonic fence persistence.** A candidate fencing token with an epoch lower than the persisted epoch is rejected as `reject-rollback`.
- **Same-epoch holder collision protection.** A holder change without a fencing-epoch advance is rejected as `reject-epoch-collision` rather than being persisted.
- **Renewal-safe persistence.** The current holder may persist a new Lease `resourceVersion` within the same epoch after a validated renewal.
- **Duplicate persistence suppression.** Rewriting an identical fencing token becomes a `noop` instead of another disk mutation.
- **Guarded reacquisition.** A reacquired leadership token must advance beyond the previously persisted fencing epoch; same-epoch reacquisition is rejected as stale.
- **New-epoch handoff.** A valid newer epoch may persist a new holder and resourceVersion as `persist-new-epoch`.
- **Regression coverage.** Tests cover epoch rollback, same-epoch holder collision, same-epoch renewal, duplicate tokens, stale reacquisition, newer-epoch handoff, and startup rollback detection.
- **1.5.7 retained.** Integrity envelopes, directory fsync, legacy 1.5.6 state compatibility, rollback-aware startup recovery, live Lease revalidation, renewal-race fencing and stale-leader blocking remain active.

## Safety invariants

1. Persisted fencing epochs never move backward.
2. A Lease holder cannot change inside the same fencing epoch and retain mutation authority.
3. Normal renewal may update resourceVersion only for the same holder and epoch after live validation.
4. Reacquisition must advance the fencing epoch before new authority can be persisted.
5. Identical fencing state does not trigger redundant persistence.
6. All v0.1-v1.5.7 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM and provenance safeguards remain in force.
