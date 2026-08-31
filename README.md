# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6.6.6

`nvlx` v1.6.6.6.6.6.6.6.6.6 adds canonical `Connection` token-list containment to the live HTTP surface. After the inherited framing, version, Host, request-target, header-syntax, `Expect`, Host-authority, request-line separator, percent-escape, canonical-CRLF, protocol-upgrade, `Trailer`, `TE`, and `Proxy-Connection` gates succeed, every `Connection` field must be a non-empty comma-separated list of ASCII HTTP tokens with optional SP/HTAB around each token.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6.6.6 canonical Connection token-list containment

- **Connection list syntax is now explicit.** Each `Connection` field must contain one or more comma-separated HTTP tokens.
- **OWS around tokens remains accepted.** SP and HTAB may appear around each token, including around comma separators.
- **Empty list elements are terminal.** Empty fields, leading/trailing commas, doubled commas, and whitespace-only elements are rejected.
- **Only token characters are admitted inside each option.** Quoted strings, semicolon parameters, embedded whitespace, `=`, `/`, `:`, raw non-ASCII, and other non-token characters are rejected.
- **Valid extension tokens remain supported.** `Connection: x-custom`, `close`, `keep-alive`, and canonical multi-token lists remain syntactically admitted unless an earlier policy gate rejects a specific option such as `upgrade`, `te`, or `proxy-connection`.
- **Multiple Connection fields remain supported when each field is canonical.** This release validates field syntax without collapsing or rewriting the parsed values.
- **HTTP/1.0 and HTTP/1.1 are covered.** Canonical list syntax is required under either admitted request version.
- **Earlier gates retain precedence.** Body framing, exact version admission, Host cardinality/authority, target syntax, obsolete folding, field-name/value syntax, `Expect`, request-line spacing, malformed percent escapes, canonical CRLF line endings, protocol-upgrade containment, request `Trailer` containment, request `TE` containment, and `Proxy-Connection` containment still run first.
- **The canonical Expect contract remains intact.** A request that also carries `Expect` is rejected by the earlier `417 Request Rejected` gate and emits no interim `100 Continue` response.
- **Malformed Connection syntax uses canonical terminal 400 framing.** `Connection: close` on the rejection prevents trailing bytes from becoming a pipelined follow-on request.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without sending the rejection body.
- **Runtime/endpoint evaluation remains isolated.** Malformed Connection syntax cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Rejection releases its bounded worker slot.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v1666666666`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, canonical origin-form request-target containment, obsolete folded-header rejection, strict request-header field-name grammar, strict request-header field-value octets, request-expectation rejection, strict HTTP/1.1 Host authority syntax, canonical request-line separator containment, malformed percent-escape rejection, canonical CRLF request/header line endings, protocol-upgrade containment, request `Trailer` declaration containment, request `TE` negotiation containment, `Proxy-Connection` containment, then canonical `Connection` token-list containment.

## Safety invariants

1. CPython's legacy headerless parser representation is accepted only when it is an exact empty mapping.
2. HTTP/0.9 and unsupported/non-canonical HTTP/1.x requests remain terminally rejected before endpoint/runtime evaluation.
3. HTTP/1.1 requests require exactly one non-empty, non-folded, non-list-like Host field and a valid operational authority.
4. The raw request target must survive parsing unchanged and begin with exactly one `/`.
5. Absolute-form, authority-form, asterisk-form, fragments, backslashes, controls, and raw non-ASCII target bytes are rejected.
6. Every percent sign in an otherwise-admitted encoded target must be followed by exactly two ASCII hex digits; valid escapes remain undecoded.
7. Any raw request-header continuation line beginning with SP or HTAB is rejected by the inherited obs-fold gate.
8. Every physical header-field start must have a non-empty ASCII token-style name immediately followed by `:`.
9. Every physical field value is limited to HTAB, SP, and visible ASCII; C0 controls other than HTAB, DEL, and raw non-ASCII octets are rejected.
10. Any `Expect` field is rejected with canonical terminal 417 framing; the server emits no `100 Continue` response.
11. An otherwise-admitted request line must reconstruct exactly with one ASCII SP between its three tokens.
12. The request line, all physical header lines, and the blank header terminator must use CRLF; EOF is not accepted as the header terminator.
13. Any `Upgrade` field or exact `upgrade` Connection token is rejected before dispatch.
14. Any request `Trailer` declaration is rejected before dispatch.
15. Any request `TE` field or exact `te` Connection token is rejected before dispatch.
16. Any `Proxy-Connection` field or exact `proxy-connection` Connection token is rejected before dispatch.
17. Every remaining `Connection` field must be a non-empty comma-separated list of ASCII HTTP tokens; malformed lists are terminally rejected.
18. HEAD rejection remains bodyless while preserving representation `Content-Length`.
19. Rejected requests cannot process trailing pipelined bytes on the same connection.
20. Rejection releases bounded worker capacity.
21. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
22. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
23. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
24. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
25. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.6.6.
