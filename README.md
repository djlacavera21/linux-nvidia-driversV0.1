# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.4

`nvlx` v1.6.6.6.6.6.6.4 adds HTTP/1.1 Host singleton containment and repairs the CPython 3.13 legacy HTTP/0.9 compatibility edge discovered by the v1.6.6.6.6.6.6.3 CI matrix. HTTP/1.1 requests now require exactly one non-empty Host field; duplicate, folded, empty, or list-like Host values terminate through the canonical `400 Request Rejected` path. HTTP/1.0 remains compatible without Host.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.4 HTTP/1.1 Host singleton containment

- **The Python 3.13 HTTP/0.9 regression is repaired fail-closed.** CPython 3.13 can expose the legacy headerless HTTP/0.9 parser state as an empty `dict`; the body-framing gate now accepts only that exact empty mapping shape. Non-empty ordinary mappings remain rejected so duplicate-aware HTTP/1.x header semantics cannot silently degrade.
- **HTTP/0.9 remains rejected.** After the compatibility repair, legacy requests continue through the v1.6.6.6.6.6.6.3 version gate and receive canonical terminal `505 Request Rejected` framing rather than reaching endpoint logic.
- **HTTP/1.1 requires exactly one Host field.** Missing or duplicate Host fields are rejected before `/livez`, `/readyz`, or `/metrics` dispatch.
- **Ambiguous Host values are rejected.** Empty, whitespace-only, obsolete-folded, or comma/list-like Host values use the fixed terminal `400 Request Rejected` contract.
- **HTTP/1.0 compatibility is preserved.** HTTP/1.0 requests may continue without Host.
- **HEAD rejection remains bodyless.** Host rejection preserves representation `Content-Length` while emitting no body for HEAD.
- **Host rejection is terminal.** `Connection: close` prevents trailing bytes from being reinterpreted as a pipelined request.
- **Framing and version gates remain earlier in the chain.** Invalid `Transfer-Encoding`/`Content-Length` and unsupported request versions still fail closed before Host evaluation or endpoint dispatch.
- **Runtime/endpoint evaluation remains isolated.** Invalid Host framing cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Host rejection releases its bounded worker slot like other terminal parser outcomes.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v16666664`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced after parsing in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, then HTTP/1.1 singleton Host framing.

## Safety invariants

1. CPython's legacy headerless parser representation is accepted only when it is an exact empty mapping.
2. Any non-empty mapping without duplicate-aware `get_all()` semantics is rejected by the body-framing gate.
3. HTTP/0.9 and unsupported/non-canonical HTTP/1.x requests remain terminally rejected before endpoint/runtime evaluation.
4. HTTP/1.1 requests require exactly one non-empty, non-folded, non-list-like Host field.
5. Host rejection uses canonical terminal `400 Request Rejected` framing with `Connection: close`.
6. HTTP/1.0 requests remain compatible without Host.
7. HEAD Host rejection remains bodyless while preserving representation `Content-Length`.
8. Rejected requests cannot process trailing pipelined bytes on the same connection.
9. Host rejection releases bounded worker capacity.
10. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
11. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
12. Existing client-abort, parser-error, logging, response-body, and method containment remains unchanged.
13. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
14. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.4.
