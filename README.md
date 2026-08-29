# nvlx: Linux-NVIDIA-Driver v1.5.6

`nvlx` v1.5.6 is a sixth stabilization patch for the live Kubernetes operator. It hardens the restart boundary by persisting leadership fencing tokens atomically and treating uncertain Lease renewal outcomes as mutation-fencing events rather than assuming leadership remains valid.

> [!IMPORTANT]
> A persisted token is evidence of previously observed authority, not authority by itself. After restart it must still match the current Lease holder, fencing epoch and Lease `resourceVersion`, and the Lease must still be fresh before controller-owned mutation is allowed.

## v1.5.6 fixes

- **Restart-safe fencing store.** Fence tokens are written through a temporary file, flushed with `fsync`, and atomically replaced.
- **Fail-closed reload.** Missing state yields no token; malformed schema or invalid token values are rejected rather than silently accepted.
- **Post-restart revalidation.** Restored tokens are rechecked against current Lease holder, epoch, resourceVersion and freshness before mutation.
- **Lease renewal race handling.** `409`/`412` or observed resourceVersion changes force relist + fence; `404` loses leadership; `429` and 5xx outcomes remain retryable but mutation authority is fenced while renewal is uncertain.
- **Handoff preservation.** Existing stale-leader fencing, fence-drain and standby semantics remain active through restart and renewal races.
- **Regression coverage.** Tests cover persisted-token reload, stale persisted tokens after handoff, corrupt state, renewal conflicts, uncertain renewals and successful renewal.
- **1.5.5 retained.** Exact Lease fencing tokens, duplicate-event suppression, bounded jitter, ordered finalization, stale-generation guards and status-write idempotency remain active.

## Safety invariants

1. Persisted fencing state cannot authorize mutation without live Lease revalidation.
2. Corrupt persisted fencing state fails closed.
3. A token restored after another controller took leadership is rejected.
4. Lease renewal uncertainty removes mutation authority until leadership is re-established.
5. Concurrent Lease updates force relist/revalidation instead of continuing with stale authority.
6. All v0.1-v1.5.5 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM and provenance safeguards remain in force.
