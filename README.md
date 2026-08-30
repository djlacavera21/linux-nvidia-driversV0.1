# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6.2

`nvlx` v1.6.6.6.6.6.6.6.2 adds strict request-header field-value octet containment to the live HTTP surface. After the existing body-framing, request-version, Host, canonical request-target, obsolete-folding, and field-name gates succeed, each physical field value is now restricted to horizontal tab, space, and visible ASCII. Embedded controls, DEL, and raw non-ASCII octets terminate through the canonical `400 Request Rejected` path before endpoint or runtime evaluation.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6.2 request-header field-value containment

- **Field values use a strict ASCII serving profile.** Empty values, SP, HTAB, and visible ASCII bytes `0x21-0x7e` remain admitted.
- **Embedded controls are rejected.** NUL and other C0 controls are not accepted inside a field value; HTAB remains the sole admitted control byte.
- **DEL is rejected.** Byte `0x7f` cannot enter parsed request metadata.
- **Raw non-ASCII values are rejected.** Bytes `0x80-0xff` are intentionally outside this minimal health-server profile, even though broader HTTP deployments can carry legacy opaque octets.
- **Ordinary punctuation and additional colons remain compatible.** A value such as `alpha:beta` is unchanged by this release.
- **Empty values remain compatible.** A syntactically valid field such as `X-Empty:` is admitted.
- **Field-name and obs-fold gates retain ownership.** Malformed physical field names and SP/HTAB-prefixed continuation lines continue to fail through their earlier inherited containment layers.
- **HTTP/1.0 and HTTP/1.1 are covered.** Value-octet syntax is enforced consistently after exact request-version admission.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without emitting the rejection body.
- **Field-value rejection is terminal.** `Connection: close` prevents trailing bytes from becoming a second pipelined request.
- **Runtime/endpoint evaluation remains isolated.** Unsafe generic field values cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Rejection releases its bounded worker slot.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v166666662`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, canonical origin-form request-target containment, obsolete folded-header rejection, strict request-header field-name grammar, then strict request-header field-value octets.

## Safety invariants

1. CPython's legacy headerless parser representation is accepted only when it is an exact empty mapping.
2. HTTP/0.9 and unsupported/non-canonical HTTP/1.x requests remain terminally rejected before endpoint/runtime evaluation.
3. HTTP/1.1 requests require exactly one non-empty, non-folded, non-list-like Host field.
4. The raw request target must survive parsing unchanged and begin with exactly one `/`.
5. Absolute-form, authority-form, asterisk-form, fragments, backslashes, controls, and raw non-ASCII target bytes are rejected.
6. Any raw request-header continuation line beginning with SP or HTAB is rejected by the inherited obs-fold gate.
7. Every physical header-field start must have a non-empty ASCII token-style name immediately followed by `:`.
8. Every physical field value is limited to HTAB, SP, and visible ASCII; C0 controls other than HTAB, DEL, and raw non-ASCII octets are rejected.
9. Malformed request metadata rejection uses canonical terminal `400 Request Rejected` framing with `Connection: close`.
10. HEAD rejection remains bodyless while preserving representation `Content-Length`.
11. Rejected requests cannot process trailing pipelined bytes on the same connection.
12. Rejection releases bounded worker capacity.
13. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
14. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
15. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
16. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
17. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.2.
