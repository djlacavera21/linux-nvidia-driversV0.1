# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.1

`nvlx` v1.6.6.6.6.6.1 extends client-abort containment to the `ThreadingHTTPServer` error hook. Expected disconnects that escape before the request handler reaches its own containment boundary no longer generate default server tracebacks, while genuine implementation failures still use the stock error-reporting path.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.1 server-level abort traceback containment

- **Expected disconnects stay quiet at the server boundary.** `EPIPE`, `ECONNRESET`, `ECONNABORTED`, `ENOTCONN`, and `ESHUTDOWN` events that reach `ThreadingHTTPServer.handle_error()` are suppressed.
- **The classifier is shared.** The server hook reuses the exact narrow client-abort classifier introduced in v1.6.6.6.6.6 rather than creating a broader exception rule.
- **Real failures remain visible.** Unrelated `OSError` and non-transport exceptions still delegate to the stock `ThreadingHTTPServer.handle_error()` implementation and retain their traceback diagnostics.
- **Handler containment remains intact.** Response-write and final stream cleanup aborts are still handled at the request-handler layer before they reach the server hook.
- **Completed wire contracts are unchanged.** `/livez`, `/readyz`, `/metrics`, parser `400/414/431/505`, resource `404`, and method `405` retain their established status, headers, bodies, and HEAD semantics.
- **Logging remains best-effort and non-reflective.** Bounded server-owned live HTTP logging and log-sink failure containment remain unchanged.
- **The live operator now uses `http_v1666661`.** The live runtime remains `runtime_v1664`.
- **Checkpoint, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation semantics are unchanged.**

## Server error-hook contract

The live server wraps `ThreadingHTTPServer.handle_error()` only for an active exception that matches the established connection-local abort classifier. Those expected disconnects return silently. Any other active exception is passed directly to the original server error hook.

This preserves traceback visibility for genuine implementation defects while preventing normal probe disconnects during handler construction/setup or other pre-handler server paths from polluting stderr.

## Safety invariants

1. Expected client-abort errors cannot produce default server tracebacks, even when they escape before `Handler.handle()` is entered.
2. The server hook recognizes exactly the same narrow abort class as the handler layer.
3. Unrelated `OSError`, `RuntimeError`, and application failures still use the stock server error-reporting path.
4. v1.6.6.6.6.6 response-write and final-cleanup abort containment remains unchanged.
5. v1.6.6.6.6.5 best-effort log-sink containment remains unchanged.
6. v1.6.6.6.6.4 non-reflective bounded logging remains unchanged.
7. Canonical parser status lines, terminal parser connection closure, bodyless framing, resource-aware `404/405`, and unified GET/HEAD dispatch remain unchanged.
8. Typed readiness/metrics validation and partial-provider symmetry remain unchanged.
9. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.1.
