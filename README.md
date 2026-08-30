# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.2

`nvlx` v1.6.6.6.6.6.2 bounds idle and partial live HTTP request reads. Accepted health sockets now have a finite request-read deadline, so a client cannot hold a live handler thread indefinitely by sending an incomplete request and then going silent.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.2 ingress-idle timeout containment

- **Live request reads are bounded.** Accepted health sockets receive a 5-second request-read timeout by default.
- **Partial requests expire connection-locally.** An idle or incomplete request closes only that client connection; the health server remains available to subsequent probes.
- **Timeouts are non-reflective and traceback-free.** Request-controlled text is not echoed to the client or default stderr logs when the read deadline expires.
- **Timeout validation is strict.** Embedded callers may override `request_timeout_seconds`, but the value must be finite, positive, numeric, and not boolean.
- **Expected timeout errors are narrow.** `TimeoutError`/`ETIMEDOUT` request-read expiration is contained; unrelated `OSError`, runtime failures, and application failures remain visible.
- **Completed response contracts are unchanged.** `/livez`, `/readyz`, `/metrics`, parser `400/414/431/505`, resource `404`, method `405`, metrics `500`, GET/HEAD parity, and exact framing remain as before.
- **Client-abort containment remains intact.** v1.6.6.6.6.6 handler-level disconnect containment and v1.6.6.6.6.6.1 server-level traceback suppression remain unchanged.
- **The live operator now uses `http_v1666662`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Request-timeout contract

The default request-read timeout is 5 seconds. `HealthServer(..., request_timeout_seconds=<value>)` accepts finite positive numeric values for embedding and tests. Boolean, zero, negative, NaN, and infinite values are rejected during server construction.

The timeout applies to accepted client sockets before BaseHTTP begins parsing the request. If a request line or headers remain incomplete until the deadline, the connection is closed and serving continues for other clients.

## Safety invariants

1. A silent partial request cannot hold a live handler thread indefinitely.
2. Timeout expiration affects only the associated client connection.
3. The server remains immediately usable after a timed-out request.
4. Timeout handling does not expose request-controlled text or a server traceback.
5. Only request timeout conditions are newly contained; unrelated implementation errors remain visible.
6. v1.6.6.6.6.6.1 server-level expected-abort traceback containment remains unchanged.
7. v1.6.6.6.6.6 handler-level response-write/final-cleanup containment remains unchanged.
8. Canonical parser status lines, bodyless framing, resource-aware `404/405`, unified GET/HEAD dispatch, and typed diagnosis propagation remain unchanged.
9. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.2.
