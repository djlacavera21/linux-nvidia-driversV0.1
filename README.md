# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6.5

`nvlx` v1.6.6.6.6.6.6.6.5 adds canonical request-line separator containment to the live HTTP surface. After the inherited body-framing, version, Host, target, header-syntax, `Expect`, and Host-authority gates succeed, the parsed request line must reconstruct exactly as `METHOD SP TARGET SP HTTP/1.0|1.1`. Generic whitespace normalization is no longer admitted before endpoint or runtime evaluation.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6.5 request-line separator containment

- **Exactly one ASCII space separates request-line tokens.** Canonical `METHOD SP TARGET SP VERSION` spellings remain admitted.
- **Tabs are rejected as separators.** HTAB between method/target or target/version can no longer be normalized by `BaseHTTPRequestHandler` tokenization.
- **Repeated spaces are rejected.** Multiple SP characters between request-line tokens terminate before resource or runtime evaluation.
- **Leading and trailing request-line whitespace are rejected.** The original decoded request line must equal the exact reconstruction of the parsed command, target, and request version.
- **Method semantics are unchanged.** A canonically spaced unsupported method still reaches the existing resource-aware 404/405 contract; this release does not redefine method grammar.
- **Origin-form target behavior is unchanged.** Percent-encoded visible-ASCII targets remain governed by the inherited target gate and exact resource identity.
- **Earlier gates retain precedence.** Body framing, exact version admission, Host cardinality, canonical target syntax, obsolete folding, field-name/value syntax, `Expect` containment, and HTTP/1.1 Host authority syntax still run before the new spacing gate.
- **Spacing failures use canonical terminal 400 framing.** `Connection: close` prevents rejected bytes from becoming a pipelined follow-on request.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without sending the rejection body.
- **Runtime/endpoint evaluation remains isolated.** Non-canonical request-line whitespace cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Rejection releases its bounded worker slot.
- **The repaired Expect contract remains intact.** Rejected `Expect` fields use canonical `417 Request Rejected` framing and emit no interim `100 Continue` response.
- **Strict HTTP/1.1 Host authority syntax remains intact.** DNS/Kubernetes-style names, IPv4, bracketed IPv6 and valid optional ports retain the v1.6.6.6.6.6.6.6.4 policy.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v166666665`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, canonical origin-form request-target containment, obsolete folded-header rejection, strict request-header field-name grammar, strict request-header field-value octets, request-expectation rejection, strict HTTP/1.1 Host authority syntax, then canonical request-line separator containment.

## Safety invariants

1. CPython's legacy headerless parser representation is accepted only when it is an exact empty mapping.
2. HTTP/0.9 and unsupported/non-canonical HTTP/1.x requests remain terminally rejected before endpoint/runtime evaluation.
3. HTTP/1.1 requests require exactly one non-empty, non-folded, non-list-like Host field.
4. Required HTTP/1.1 Host values must additionally pass strict authority syntax before dispatch.
5. The raw request target must survive parsing unchanged and begin with exactly one `/`.
6. Absolute-form, authority-form, asterisk-form, fragments, backslashes, controls, and raw non-ASCII target bytes are rejected.
7. Any raw request-header continuation line beginning with SP or HTAB is rejected by the inherited obs-fold gate.
8. Every physical header-field start must have a non-empty ASCII token-style name immediately followed by `:`.
9. Every physical field value is limited to HTAB, SP, and visible ASCII; C0 controls other than HTAB, DEL, and raw non-ASCII octets are rejected.
10. Any `Expect` field is rejected with canonical terminal 417 framing; the server emits no `100 Continue` response.
11. An otherwise-admitted request line must reconstruct exactly with one ASCII SP between its three tokens.
12. HEAD rejection remains bodyless while preserving representation `Content-Length`.
13. Rejected requests cannot process trailing pipelined bytes on the same connection.
14. Rejection releases bounded worker capacity.
15. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
16. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
17. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
18. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
19. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.5.
