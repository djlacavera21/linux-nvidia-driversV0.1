# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.2

`nvlx` v1.6.6.6.6.6.6.2 adds bodyless request-framing containment to the live HTTP server. The health, readiness, and metrics surface does not consume request bodies, so this release rejects `Transfer-Encoding`, non-zero or malformed `Content-Length`, and duplicate `Content-Length` fields before endpoint or runtime evaluation. A single `Content-Length: 0` remains accepted for client compatibility.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.2 bodyless request-framing containment

- **Live requests remain bodyless by contract.** `/livez`, `/readyz`, and `/metrics` never consume request payload bytes.
- **`Transfer-Encoding` is rejected.** Any transfer-coding field, including `chunked` or `identity`, terminates the request through the canonical contained `400 Request Rejected` path.
- **Only one zero content length is admitted.** A single `Content-Length: 0` is accepted, with ordinary optional surrounding space or tab; non-zero, malformed, signed, comma-joined, leading-zero, folded, or duplicate values are rejected.
- **Framing rejection is terminal.** Rejected connections are closed so bytes after the header block cannot be reinterpreted as a pipelined request.
- **HEAD rejection remains bodyless.** Framing is checked after the request method is parsed, preserving the established HEAD body-suppression rule and representation `Content-Length`.
- **Runtime/endpoint evaluation is isolated.** Rejected framing never reaches `/livez`, `/readyz`, `/metrics`, readiness diagnosis, or metrics diagnosis.
- **Admission capacity recovers normally.** A framing `400` releases its bounded worker slot like other terminal parser outcomes.
- **The existing method contract is preserved.** A bodyless unsupported method still receives `405 Method Not Allowed` with `Allow: GET, HEAD`; malformed body framing is rejected first as `400`.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **Completed response behavior is unchanged.** GET/HEAD parity, parser `400/414/431/505`, resource `404`, method `405`, metrics `500`, canonical framing, non-reflective logging, and client-abort containment remain unchanged.
- **The live operator now uses `http_v16666662`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The request-line, header-byte, and header-field budgets remain independent. The new framing rule is a protocol invariant rather than another resource budget: admitted requests must be bodyless, represented by no body-framing headers or exactly one zero `Content-Length`.

## Safety invariants

1. Transfer-coded, non-zero-length, malformed-length, and duplicate-length requests are rejected before endpoint/runtime evaluation.
2. Body-framing rejection uses the existing canonical terminal `400 Request Rejected` path with `Connection: close`.
3. Bytes following rejected framing cannot become a second pipelined request on the same connection.
4. HEAD framing rejection remains bodyless while preserving representation `Content-Length`.
5. A single zero `Content-Length` remains compatible with normal GET/HEAD handling.
6. Framing rejection releases bounded worker capacity.
7. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
8. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
9. Saturated connections never reach endpoint/runtime logic.
10. Existing client-abort, parser-error, logging, response-body, and method containment remains unchanged.
11. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
12. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.2.
