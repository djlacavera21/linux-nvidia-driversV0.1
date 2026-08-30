# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6

`nvlx` v1.6.6.6.6.6.6 adds a strict request-line byte budget to the live HTTP server. Previous releases already bound concurrency, idle time, total header-parse time, and aggregate header bytes; this release closes the remaining request-line size asymmetry by enforcing an 8 KiB nvlx limit before BaseHTTP parsing.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6 request-line byte budget

- **Request lines are capped at 8 KiB by default.** This is tighter than BaseHTTP's historical roughly 64 KiB request-line allowance.
- **Oversize fails through the existing parser contract.** Requests that exceed the nvlx line budget return canonical `414 Request Rejected` framing and close the connection.
- **HEAD oversize remains bodyless.** An exact `HEAD ` prefix is recognized before parser rejection so the established HEAD body-suppression rule still applies.
- **Runtime/endpoint evaluation is isolated.** Oversized request targets never reach `/livez`, `/readyz`, `/metrics`, readiness diagnosis, or metrics diagnosis.
- **Admission capacity recovers normally.** A request-line `414` releases its bounded worker slot like other terminal parser outcomes.
- **Header accounting remains independent.** The 32 KiB aggregate request-header budget is unchanged and does not consume request-line bytes.
- **Configuration is strict.** `max_request_line_bytes` must be an exact positive integer no larger than BaseHTTP's 65,536-byte hard bound.
- **Existing ingress defenses remain intact.** The 5-second idle timeout, 5-second absolute request-header deadline, and 32-request concurrent admission cap are unchanged.
- **Completed response behavior is unchanged.** GET/HEAD parity, parser `400/414/431/505`, resource `404`, method `405`, metrics `500`, canonical framing, non-reflective logging, and client-abort containment remain unchanged.
- **The live operator now uses `http_v1666666`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server now applies four independent request-ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.

The request-line and header-byte budgets are intentionally separate. A normal short request line does not reduce the available aggregate header budget, and an under-budget header block does not expand the request-line allowance.

## Safety invariants

1. Oversized request targets are rejected before parser/runtime evaluation.
2. Request-line overflow uses the existing canonical terminal `414` path.
3. Exact HEAD overflow remains bodyless while preserving representation `Content-Length`.
4. Request-line rejection releases bounded worker capacity.
5. Request-line and aggregate header budgets remain independent.
6. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
7. Saturated connections never reach endpoint/runtime logic.
8. Existing client-abort, parser-error, logging, and body-framing containment remains unchanged.
9. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.
