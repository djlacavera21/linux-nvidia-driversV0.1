# nvlx: Linux-NVIDIA-Driver v1.6.1.1

`nvlx` v1.6.1.1 is a surgical hotfix on top of the real Kubernetes runtime introduced in v1.6.0 and hardened in v1.6.1. It does not expand the controller API surface. Instead, it closes two mutation/error-handling gaps: Kubernetes Event creation now revalidates live leadership immediately before POST, and server-supplied API error text is scrubbed if it reflects the active ServiceAccount bearer token.

> [!IMPORTANT]
> NVIDIA resource changes remain read-only in v1.6.1.1. The operator mutates only nvlx-owned GPUFleet status/finalizers plus its Lease and Events; driver/GPU Operator mutation remains deferred.

## v1.6.1.1 hotfixes

- **Event mutation fencing.** `events.k8s.io/v1` Event creation now performs a live leadership check immediately before the API POST. If leadership is lost after a successful GPUFleet status PATCH but before Event emission, the Event is suppressed rather than written by a stale replica.
- **Reflected-token redaction.** Kubernetes API error messages are sanitized against the active bearer token before an `ApiError` is constructed, including both ordinary JSON requests and watch HTTP failures.
- **Timeout handling cleanup.** Transport timeout/connection reason selection is explicit rather than relying on conditional-expression precedence, preserving deterministic sanitized failure messages.
- **Regression coverage.** Tests exercise leadership loss between status PATCH and Event POST, successful Event creation while leadership remains valid, and bearer-token reflection through both normal and watch HTTP error responses.
- **1.6.1 safeguards retained.** Malformed JSON/watch handling, transient reconnect classification, bounded deterministic backoff, shutdown fencing, conflict-time leadership revalidation, and fail-closed finalizer safety remain active.

## Safety invariants

1. Every controller-owned Kubernetes mutation path, including Event POST, requires live leadership immediately before the write.
2. A stale replica may complete a status write only if it still held leadership at that write boundary; subsequent Event emission is independently fenced.
3. Active ServiceAccount bearer tokens are redacted from server-derived API error text before exceptions are surfaced.
4. Runtime timeouts or malformed API responses cannot authorize mutation.
5. NVIDIA resources remain read-only in v1.6.1.1.
6. All v0.1-v1.6.1 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM, provenance, fencing, replay and Lease-CAS safeguards remain in force.
