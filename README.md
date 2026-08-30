# nvlx: Linux-NVIDIA-Driver v1.6.1

`nvlx` v1.6.1 is the first hardening patch for the real Kubernetes runtime introduced in v1.6.0. It keeps the same live API-backed operator surface while tightening transport failure handling, watch-stream tolerance, reconnect behavior, shutdown fencing, and conflict retry safety.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.1. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.1 hardening

- **Transport timeout normalization.** Socket/URL timeouts become sanitized `ApiError(status=0)` failures without leaking ServiceAccount tokens or raw multiline server data.
- **Malformed JSON protection.** Non-watch JSON responses that cannot be decoded fail closed with an explicit malformed-JSON API error.
- **Watch-stream tolerance.** Blank or malformed newline frames are ignored instead of crashing the runtime; unknown watch event types are ignored safely.
- **Transient watch classification.** `410` forces relist; `408`, `425`, `429`, and 5xx watch errors reconnect with bounded backoff; non-retryable watch errors do not trigger mutation.
- **Deterministic reconnects.** Reconnect delay is validated, exponential, and capped by the configured maximum.
- **Shutdown fencing.** `stop()` immediately revokes local leader state and prevents new Events or mutations while termination is in progress.
- **Conflict handoff safety.** Status conflict recovery rechecks leadership before refetching and retrying, so leadership loss during a `409`/`412` path cannot complete the stale write.
- **Finalizer input hardening.** Invalid quarantine-count status values fail closed instead of being coerced through deletion.
- **Regression coverage.** Tests cover transient/relist watch errors, malformed/unknown events, bounded reconnects, sanitized timeouts, conflict-time leader loss, and immediate shutdown fencing.

## Safety invariants

1. A runtime timeout or malformed API response cannot authorize mutation.
2. Leadership is revalidated after status conflicts before any retry boundary is crossed.
3. Termination immediately revokes local mutation readiness.
4. Malformed or unknown watch frames cannot crash the process into an uncontrolled mutation path.
5. Finalizer removal remains fail-closed on invalid safety inputs.
6. NVIDIA resources remain read-only in v1.6.1.
7. All v0.1-v1.6.0 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay and Lease-CAS safeguards remain in force.
