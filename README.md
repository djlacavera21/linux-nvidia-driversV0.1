# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6.1

`nvlx` v1.6.6.6.6.6.6.6.1 adds strict request-header field-name containment to the live HTTP surface. After the existing body-framing, request-version, Host, canonical request-target, and obsolete-folding gates succeed, each physical header-field start must now contain a non-empty ASCII HTTP token-style name immediately followed by `:`. Malformed names terminate through the existing canonical `400 Request Rejected` path before endpoint or runtime evaluation.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6.1 request-header field-name containment

- **Header names must be non-empty HTTP token names.** ASCII letters, digits, and the standard token punctuation ``!#$%&'*+-.^_`|~`` are admitted before the first colon.
- **Whitespace before the colon is rejected.** Spellings such as `X-Test : value` cannot be silently dropped or normalized by the Python header parser.
- **Non-token punctuation is rejected.** Names such as `Bad@Name` are terminated even if a parser would otherwise accept them.
- **Empty and colonless field starts are rejected.** `: value` and `NoColon` cannot pass through as ignored parser defects.
- **Raw non-ASCII field-name bytes are rejected.** Header field names on this live surface are strictly ASCII token syntax.
- **Field values are not redefined by this release.** This increment intentionally isolates field-name grammar; value-octet policy remains a separate hardening concern.
- **Obsolete folding keeps precedence.** SP/HTAB-prefixed continuation lines remain owned by the inherited v1.6.6.6.6.6.6.6 `obs-fold` gate rather than being reclassified as malformed names.
- **HTTP/1.0 and HTTP/1.1 are covered.** Name syntax is enforced consistently after the exact request-version gate.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without emitting the rejection body.
- **Field-name rejection is terminal.** `Connection: close` prevents trailing bytes from becoming a second pipelined request.
- **Runtime/endpoint evaluation remains isolated.** Malformed generic header names cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Rejection releases its bounded worker slot.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v166666661`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, canonical origin-form request-target containment, obsolete folded-header rejection, then strict request-header field-name grammar.

## Safety invariants

1. CPython's legacy headerless parser representation is accepted only when it is an exact empty mapping.
2. HTTP/0.9 and unsupported/non-canonical HTTP/1.x requests remain terminally rejected before endpoint/runtime evaluation.
3. HTTP/1.1 requests require exactly one non-empty, non-folded, non-list-like Host field.
4. The raw request target must survive parsing unchanged and begin with exactly one `/`.
5. Absolute-form, authority-form, asterisk-form, fragments, backslashes, controls, and raw non-ASCII target bytes are rejected.
6. Any raw request-header continuation line beginning with SP or HTAB is rejected by the inherited obs-fold gate.
7. Every physical header-field start must have a non-empty ASCII token-style name immediately followed by `:`.
8. Malformed field-name rejection uses canonical terminal `400 Request Rejected` framing with `Connection: close`.
9. HEAD rejection remains bodyless while preserving representation `Content-Length`.
10. Rejected requests cannot process trailing pipelined bytes on the same connection.
11. Rejection releases bounded worker capacity.
12. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
13. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
14. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
15. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
16. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.1.
