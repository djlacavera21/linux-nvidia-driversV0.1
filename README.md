# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6

`nvlx` v1.6.6.6.6.6 contains expected client disconnects at the live HTTP handler boundary. Broken pipes, connection resets, aborted connections, and equivalent connection-local socket errors can no longer escalate into server-level request failures while a probe response is being written or finalized.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6 client-abort response containment

- **Probe disconnects are connection-local.** Broken pipes, resets, aborted connections, not-connected sockets, and shutdown sockets are treated as client-abort transport events.
- **Response-write aborts are contained.** Expected abort errors raised while emitting status lines, headers, or bodies terminate only that connection.
- **Final stream cleanup is contained.** The same narrow abort class is tolerated during handler `finish()` cleanup.
- **The boundary is deliberately narrow.** Unrelated `OSError` values and non-`OSError` exceptions still propagate normally and remain visible as implementation failures.
- **Completed response contracts are unchanged.** `/livez`, `/readyz`, `/metrics`, parser errors, `404`, and `405` retain their established status, headers, bodies, and HEAD semantics whenever the client remains connected.
- **Logging remains best-effort and non-reflective.** v1.6.6.6.6.5 sink-failure containment and v1.6.6.6.6.4 bounded server-owned log markers remain intact.
- **Parser containment remains canonical.** `400/414/431/505` responses retain `HTTP/1.0 <code> Request Rejected`, fixed framing, and `Connection: close`.
- **The live operator now uses `http_v166666`.** The live runtime remains `runtime_v1664`.
- **Checkpoint, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation semantics are unchanged.**

## Client-abort contract

The live handler recognizes only connection-local abort conditions: `EPIPE`, `ECONNRESET`, `ECONNABORTED`, `ENOTCONN`, and `ESHUTDOWN` where available, including their standard Python exception subclasses.

If one of those failures occurs during request handling or final stream cleanup, the handler marks the connection closed and returns without escalating it to server-level request error handling. Other ordinary errors are not swallowed.

## Safety invariants

1. Client disconnects cannot escalate a completed or in-progress probe response into a server-level handler failure.
2. Only recognized connection-abort `OSError` conditions are contained.
3. Unrelated `OSError`, `RuntimeError`, and application exceptions still propagate.
4. v1.6.6.6.6.5 best-effort log-sink containment remains unchanged.
5. v1.6.6.6.6.4 non-reflective bounded logging remains unchanged.
6. v1.6.6.6.6.3 canonical parser status lines and terminal parser connection closure remain unchanged.
7. Canonical bodyless framing, resource-aware `404/405`, unified GET/HEAD dispatch, and typed diagnosis propagation remain unchanged.
8. All v1.6.6.x typed readiness/metrics validation remains unchanged.
9. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.
