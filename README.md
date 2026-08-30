# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.3

`nvlx` v1.6.6.6.6.6.6.3 adds strict request-version admission to the live HTTP server. The health, readiness, and metrics surface now accepts exactly HTTP/1.0 and HTTP/1.1 request syntax, rejects legacy HTTP/0.9 and non-canonical HTTP/1.x minors through the existing terminal `505 Request Rejected` contract, and safely seeds an empty header object for legacy parser paths before the inherited body-framing gate runs.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.3 request-version containment

- **Only HTTP/1.0 and HTTP/1.1 requests are admitted.** Legacy HTTP/0.9, non-canonical spellings such as HTTP/1.01, and unsupported HTTP/1.x minors are rejected before endpoint dispatch.
- **Unsupported versions use the canonical parser contract.** Version rejection returns fixed `505 Request Rejected` framing, `Server: nvlx`, `Cache-Control: no-store`, exact representation length, and `Connection: close`.
- **HTTP/0.9 no longer reaches a headerless compatibility path unsafely.** The handler seeds an empty `Message` before inherited parsing so body-framing checks remain defined even when BaseHTTP does not construct parsed headers.
- **Legacy pipelining is terminated.** Bytes following a rejected HTTP/0.9 request cannot become a second request on the same connection.
- **HEAD version rejection remains bodyless.** Unsupported HEAD requests preserve the established representation `Content-Length` without emitting the rejection body.
- **BaseHTTP HTTP/2+ rejection remains contained.** Existing parser-generated 505 responses keep the same canonical non-reflective framing.
- **Body-framing precedence remains fail-closed.** Invalid `Transfer-Encoding` or `Content-Length` is still rejected as canonical `400` before the new version gate can dispatch endpoint logic.
- **Runtime/endpoint evaluation is isolated.** Rejected versions never reach `/livez`, `/readyz`, `/metrics`, readiness diagnosis, or metrics diagnosis.
- **Admission capacity recovers normally.** A version `505` releases its bounded worker slot like other terminal parser outcomes.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **Completed response behavior is unchanged.** Supported GET/HEAD parity, parser `400/414/431/505`, resource `404`, method `405`, metrics `500`, canonical framing, non-reflective logging, and client-abort containment remain unchanged.
- **The live operator now uses `http_v16666663`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The request-line, header-byte, and header-field budgets remain independent. Two protocol invariants now sit beside those budgets: admitted requests must be bodyless, and their request version must be exactly HTTP/1.0 or HTTP/1.1.

## Safety invariants

1. Legacy HTTP/0.9 and unsupported/non-canonical HTTP/1.x requests are rejected before endpoint/runtime evaluation.
2. Version rejection uses the existing canonical terminal `505 Request Rejected` path with `Connection: close`.
3. The inherited body-framing gate receives a defined header object even on BaseHTTP's legacy headerless request path.
4. Bytes following rejected legacy requests cannot become a second pipelined request.
5. HEAD version rejection remains bodyless while preserving representation `Content-Length`.
6. Invalid request-body framing remains fail-closed before endpoint dispatch.
7. Version rejection releases bounded worker capacity.
8. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
9. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
10. Saturated connections never reach endpoint/runtime logic.
11. Existing client-abort, parser-error, logging, response-body, and method containment remains unchanged.
12. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
13. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.3.
