# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.5

`nvlx` v1.6.6.6.6.6.5 adds an aggregate request-header byte budget to the live HTTP server. Individual request lines/headers remain protected by BaseHTTP parser limits, while this release additionally bounds the total header block retained for one admitted request.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.5 aggregate header-byte budget

- **Aggregate request headers are bounded.** The default maximum is 32 KiB of header bytes per admitted request, excluding the separately bounded request line.
- **Oversized header sets fail before endpoint logic.** The existing contained parser path returns canonical `431 Request Rejected` without readiness or metrics evaluation.
- **HEAD remains bodyless on rejection.** The representation `Content-Length` is retained while no response body bytes are written.
- **Worker capacity is recovered.** Header-budget rejection releases the bounded admission slot exactly like other parser completion paths.
- **Configuration is strict.** `max_request_header_bytes` accepts only exact positive integers; booleans, floats, strings, zero, and negative values are rejected.
- **Existing ingress timing remains intact.** The 5-second socket idle timeout and 5-second absolute request-header deadline remain unchanged.
- **Bounded admission remains intact.** The default live worker cap remains 32 and saturated connections are still rejected before parsing/runtime evaluation.
- **Completed response behavior is unchanged.** GET/HEAD parity, parser `400/414/431/505`, resource `404`, method `405`, metrics `500`, canonical framing, non-reflective logging, and client-abort containment remain unchanged.
- **The live operator now uses `http_v1666665`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live HTTP server now applies four independent ingress controls:

1. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
2. `request_header_deadline_seconds` — absolute total deadline for request-line/header parsing, default 5 seconds.
3. `max_concurrent_requests` — admitted request-worker bound, default 32.
4. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.

The aggregate budget applies only while `parse_request()` consumes headers. The request line remains governed by the existing parser line-length contract, and runtime/readiness/metrics work begins only after header parsing succeeds.

## Safety invariants

1. A silent partial request cannot hold a worker indefinitely.
2. A byte-trickle partial request cannot hold a worker indefinitely.
3. One admitted request cannot accumulate an unbounded aggregate header block.
4. Header-budget rejection occurs before endpoint/runtime evaluation.
5. Header-budget rejection releases bounded admission capacity.
6. Successful under-budget requests retain the established live wire contracts.
7. Existing client-abort, parser-error, logging, body-framing, idle-timeout, absolute-deadline, and admission containment remains unchanged.
8. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
9. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.5.
