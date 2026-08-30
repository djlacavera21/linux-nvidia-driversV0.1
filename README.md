# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6.6.3

`nvlx` v1.6.6.6.6.6.6.6.6.3 adds request `Trailer` declaration containment to the live HTTP surface. After the inherited framing, version, Host, request-target, header-syntax, `Expect`, Host-authority, request-line separator, percent-escape, canonical-CRLF, and protocol-upgrade gates succeed, any `Trailer` field is rejected before endpoint or runtime evaluation.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6.6.3 request Trailer containment

- **The live health server has no request-trailer phase.** Any `Trailer` declaration is rejected because transfer-encoded request bodies are already forbidden on this bodyless surface.
- **Presence alone is terminal.** Empty, single, and duplicate `Trailer` fields all fail through canonical `400 Request Rejected` framing.
- **`TE` is not redefined by this release.** `TE: trailers` remains outside this narrow declaration gate and continues to follow inherited header behavior.
- **HTTP/1.0 and HTTP/1.1 are covered.** A `Trailer` declaration is refused after exact request-version admission under either supported version.
- **Earlier gates retain precedence.** Body framing, exact version admission, Host cardinality/authority, target syntax, obsolete folding, field-name/value syntax, `Expect`, request-line spacing, malformed percent escapes, canonical CRLF line endings, and protocol-upgrade containment still run first.
- **The canonical Expect contract remains intact.** A request that also carries `Expect` is rejected by the earlier `417 Request Rejected` gate and emits no interim `100 Continue` response.
- **Trailer failures use canonical terminal 400 framing.** `Connection: close` on the rejection prevents trailing bytes from becoming a pipelined follow-on request.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without sending the rejection body.
- **Runtime/endpoint evaluation remains isolated.** Trailer declarations cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Rejection releases its bounded worker slot.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v1666666663`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, canonical origin-form request-target containment, obsolete folded-header rejection, strict request-header field-name grammar, strict request-header field-value octets, request-expectation rejection, strict HTTP/1.1 Host authority syntax, canonical request-line separator containment, malformed percent-escape rejection, canonical CRLF request/header line endings, protocol-upgrade containment, then request `Trailer` declaration containment.

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
14. Any request `Trailer` declaration is rejected; `TE` remains outside this release's scope.
15. HEAD rejection remains bodyless while preserving representation `Content-Length`.
16. Rejected requests cannot process trailing pipelined bytes on the same connection.
17. Rejection releases bounded worker capacity.
18. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
19. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
20. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
21. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
22. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.6.3.
