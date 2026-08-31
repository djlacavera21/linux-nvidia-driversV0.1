# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6.6.6.3.3.1.1

`nvlx` v1.6.6.6.6.6.6.6.6.6.3.3.1.1 adds `Proxy-Authorization` credential-channel containment to the live HTTP surface. After the inherited framing, version, Host, request-target, header-syntax, `Expect`, Host-authority, request-line separator, percent-escape, canonical-CRLF, protocol-upgrade, `Trailer`, `TE`, `Proxy-Connection`, canonical `Connection` token-list, lifecycle-conflict, critical-nomination, duplicate-option, singleton-Connection-field, `Keep-Alive`, `HTTP2-Settings`, and WebSocket-metadata gates succeed, the server rejects any `Proxy-Authorization` request field or exact `proxy-authorization` Connection option before endpoint or runtime evaluation.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6.6.6.3.3.1.1 Proxy-Authorization credential-channel containment

- **Proxy credentials are terminal at the origin.** Any request `Proxy-Authorization` field is rejected through canonical `400 Request Rejected` framing.
- **Presence alone is sufficient.** Empty, Basic, Bearer, custom-scheme, and duplicated `Proxy-Authorization` fields are rejected without interpreting or logging credential material.
- **Connection nomination is also rejected.** An exact `proxy-authorization` Connection option is terminal, case-insensitively, even when no credential field is present.
- **Origin authorization remains unchanged.** A normal `Authorization` request field remains outside this rule and is admitted when all inherited gates accept it.
- **Substring lookalikes remain outside this rule.** Options such as `proxy-authorization-x` remain valid when otherwise admissible.
- **HTTP/1.0 and HTTP/1.1 are covered.** Proxy credential signaling is refused under either admitted request version.
- **Earlier gates retain precedence.** `Expect`, `Upgrade`, `HTTP2-Settings`, WebSocket metadata, `Keep-Alive`, malformed Connection lists, lifecycle conflicts, critical nomination, duplicate options, repeated Connection fields, `TE`, and `Proxy-Connection` still run before this layer.
- **The canonical Expect contract remains intact.** A request that also carries `Expect` is rejected by the earlier `417 Request Rejected` gate and emits no interim `100 Continue` response.
- **Proxy-Authorization failures use canonical terminal 400 framing.** Rejection closes the connection so trailing bytes cannot become a pipelined follow-on request.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without sending the rejection body.
- **Runtime/endpoint evaluation remains isolated.** Proxy credential material cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Rejection releases its bounded worker slot.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v16666666663311`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, canonical origin-form request-target containment, obsolete folded-header rejection, strict request-header field-name grammar, strict request-header field-value octets, request-expectation rejection, strict HTTP/1.1 Host authority syntax, canonical request-line separator containment, malformed percent-escape rejection, canonical CRLF request/header line endings, protocol-upgrade containment, request `Trailer` declaration containment, request `TE` negotiation containment, `Proxy-Connection` containment, canonical `Connection` token-list containment, `Connection` lifecycle conflict containment, critical `Connection`-option nomination containment, duplicate `Connection`-option containment, singleton `Connection`-field containment, request `Keep-Alive` field containment, `HTTP2-Settings` request containment, WebSocket handshake-metadata containment, then `Proxy-Authorization` credential-channel containment.

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
18. Requests that advertise both `close` and `keep-alive` across canonical Connection fields are terminally rejected.
19. `Connection` options may not nominate `host`, `content-length`, `transfer-encoding`, `trailer`, `expect`, or `connection` as hop-by-hop fields.
20. Each remaining `Connection` option may appear only once across all Connection fields, case-insensitively.
21. At most one physical `Connection` header field may remain after all inherited gates succeed.
22. Any physical `Keep-Alive` request field is terminally rejected; the `Connection: keep-alive` option remains governed by inherited lifecycle policy.
23. Any physical `HTTP2-Settings` request field or exact `http2-settings` Connection option is terminally rejected.
24. Any request field whose name begins with `Sec-WebSocket-`, case-insensitively, is terminally rejected.
25. Any physical `Proxy-Authorization` request field or exact `proxy-authorization` Connection option is terminally rejected; ordinary `Authorization` remains outside this rule.
26. HEAD rejection remains bodyless while preserving representation `Content-Length`.
27. Rejected requests cannot process trailing pipelined bytes on the same connection.
28. Rejection releases bounded worker capacity.
29. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
30. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
31. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
32. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
33. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.6.6.3.3.1.1.
