# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6.3

`nvlx` v1.6.6.6.6.6.6.6.3 adds request `Expect` containment to the live HTTP surface. After the existing body-framing, request-version, Host, canonical request-target, obsolete-folding, field-name, and field-value gates succeed, any `Expect` field is rejected with terminal `417 Request Rejected` framing. The live endpoints are deliberately bodyless and do not negotiate `100-continue` or extension expectations.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6.3 Expect containment

- **No request expectations are admitted.** Any `Expect` field is rejected, including `100-continue`, empty values, duplicates, and extension tokens.
- **417 is used for expectation rejection.** Otherwise-valid request syntax is distinguished from malformed request metadata while keeping the response non-reflective.
- **No interim 100 response is emitted.** The bodyless live surface never enters request-body expectation negotiation.
- **HTTP/1.0 and HTTP/1.1 are covered.** The same no-expectation contract applies after exact request-version admission.
- **Earlier framing gates retain precedence.** Invalid `Transfer-Encoding` or `Content-Length` still fails through the inherited canonical 400 path before expectation evaluation.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without emitting the rejection body.
- **Expectation rejection is terminal.** `Connection: close` prevents trailing bytes from becoming a second pipelined request.
- **Runtime/endpoint evaluation remains isolated.** Rejected expectations cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Rejection releases its bounded worker slot.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v166666663`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, canonical origin-form request-target containment, obsolete folded-header rejection, strict request-header field-name grammar, strict request-header field-value octets, then request-expectation rejection.

## Safety invariants

1. CPython's legacy headerless parser representation is accepted only when it is an exact empty mapping.
2. HTTP/0.9 and unsupported/non-canonical HTTP/1.x requests remain terminally rejected before endpoint/runtime evaluation.
3. HTTP/1.1 requests require exactly one non-empty, non-folded, non-list-like Host field.
4. The raw request target must survive parsing unchanged and begin with exactly one `/`.
5. Absolute-form, authority-form, asterisk-form, fragments, backslashes, controls, and raw non-ASCII target bytes are rejected.
6. Any raw request-header continuation line beginning with SP or HTAB is rejected by the inherited obs-fold gate.
7. Every physical header-field start must have a non-empty ASCII token-style name immediately followed by `:`.
8. Every physical field value is limited to HTAB, SP, and visible ASCII; C0 controls other than HTAB, DEL, and raw non-ASCII octets are rejected.
9. Any `Expect` field is rejected with terminal 417 framing; the server emits no `100 Continue` response.
10. HEAD rejection remains bodyless while preserving representation `Content-Length`.
11. Rejected requests cannot process trailing pipelined bytes on the same connection.
12. Rejection releases bounded worker capacity.
13. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
14. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
15. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
16. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
17. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.3.
