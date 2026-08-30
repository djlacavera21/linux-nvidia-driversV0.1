# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6.6.1

`nvlx` v1.6.6.6.6.6.6.6.6.1 adds canonical CRLF request-line/header containment to the live HTTP surface. After the inherited framing, version, Host, request-target, header-syntax, `Expect`, Host-authority, request-line separator, and percent-escape gates succeed, the physical request line, every physical header line, and the blank header terminator must use `CRLF` before endpoint or runtime evaluation.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6.6.1 canonical CRLF containment

- **The request line must end in CRLF.** LF-only or other non-CRLF request-line termination is rejected through canonical terminal `400 Request Rejected` framing.
- **Every physical header field must end in CRLF.** LF-only header lines are not admitted even when Python's parser would otherwise accept them.
- **The blank header terminator must itself be CRLF.** LF-only termination is rejected.
- **EOF cannot replace the blank header terminator.** A connection close after header fields no longer acts as an accepted end-of-header marker.
- **The gate is observational only.** It does not rewrite line endings or otherwise modify request bytes before inherited parsing.
- **HTTP/1.0 and HTTP/1.1 are covered.** The same physical-line rule applies after exact request-version admission.
- **Earlier gates retain precedence.** Body framing, version admission, Host cardinality, target syntax, obsolete folding, field-name/value syntax, `Expect`, Host authority, request-line spacing, and percent-escape containment still run first.
- **The canonical Expect contract remains intact.** Requests rejected by the earlier `Expect` gate still use `417 Request Rejected` framing and emit no interim `100 Continue` response.
- **Valid percent escapes remain opaque.** This release does not decode or reinterpret `%HH` target sequences.
- **Line-ending failures are terminal.** `Connection: close` prevents rejected bytes from becoming a pipelined follow-on request.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without sending the rejection body.
- **Runtime/endpoint evaluation remains isolated.** Non-canonical physical line endings cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Rejection releases its bounded worker slot.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v1666666661`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, canonical origin-form request-target containment, obsolete folded-header rejection, strict request-header field-name grammar, strict request-header field-value octets, request-expectation rejection, strict HTTP/1.1 Host authority syntax, canonical request-line separator containment, malformed percent-escape rejection, then canonical CRLF request/header line endings.

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
13. HEAD rejection remains bodyless while preserving representation `Content-Length`.
14. Rejected requests cannot process trailing pipelined bytes on the same connection.
15. Rejection releases bounded worker capacity.
16. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
17. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
18. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
19. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
20. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.6.1.
