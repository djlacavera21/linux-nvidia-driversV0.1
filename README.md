# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.5

`nvlx` v1.6.6.6.6.6.6.5 adds canonical origin-form request-target containment to the live HTTP surface. After body framing, request-version, and Host validation succeed, the server now requires the raw request target to remain unchanged by the Python parser and to use a visible-ASCII origin form beginning with exactly one `/`. Alternate proxy/tunnel forms and ambiguous spellings terminate through the existing canonical `400 Request Rejected` path before endpoint or runtime evaluation.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.5 request-target containment

- **Only canonical origin-form targets are admitted.** Normal `/path` and `/path?query` request targets remain syntactically valid.
- **Absolute-form targets are rejected.** Proxy-style targets such as `http://host/path` cannot reach the live resource dispatcher.
- **Authority-form and asterisk-form targets are rejected.** The health server has no CONNECT tunnel or server-wide `*` role.
- **Parser normalization cannot create a live endpoint.** The raw request target must equal the parsed target exactly; a raw `//livez` that Python normalizes internally cannot become `/livez`.
- **Fragments and backslashes are rejected.** These ambiguous forms terminate before resource identity or runtime logic.
- **Raw targets must be visible ASCII.** Control bytes and raw non-ASCII octets fail closed; percent-encoded URI data remains ordinary visible ASCII and is still handled by existing exact resource identity rules.
- **Query syntax remains admitted without changing endpoint identity.** For example, `/livez?probe=1` passes target syntax but remains an unknown resource under the existing exact-path contract.
- **HEAD target rejection remains bodyless.** Representation `Content-Length` is preserved without emitting the rejection body.
- **Target rejection is terminal.** `Connection: close` prevents trailing bytes from becoming a second pipelined request.
- **Earlier gates keep precedence.** Body-framing, request-version, and HTTP/1.1 Host containment continue to fail closed before target evaluation.
- **Runtime/endpoint evaluation remains isolated.** Rejected targets cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Target rejection releases its bounded worker slot.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v16666665`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, then canonical origin-form request-target containment.

## Safety invariants

1. CPython's legacy headerless parser representation is accepted only when it is an exact empty mapping.
2. HTTP/0.9 and unsupported/non-canonical HTTP/1.x requests remain terminally rejected before endpoint/runtime evaluation.
3. HTTP/1.1 requests require exactly one non-empty, non-folded, non-list-like Host field.
4. The raw request target must survive parsing unchanged and begin with exactly one `/`.
5. Absolute-form, authority-form, asterisk-form, fragments, backslashes, controls, and raw non-ASCII target bytes are rejected.
6. Target rejection uses canonical terminal `400 Request Rejected` framing with `Connection: close`.
7. HEAD rejection remains bodyless while preserving representation `Content-Length`.
8. Rejected requests cannot process trailing pipelined bytes on the same connection.
9. Rejection releases bounded worker capacity.
10. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
11. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
12. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
13. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
14. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.5.
