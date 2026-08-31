# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6.6.6.3.3.1.2.3.4.5.6

`nvlx` v1.6.6.6.6.6.6.6.6.6.3.3.1.2.3.4.5.6 adds `X-Client-IP` Connection-nomination containment to the live HTTP surface. After the inherited framing, version, Host, request-target, header-syntax, `Expect`, Host-authority, request-line separator, percent-escape, canonical-CRLF, protocol-upgrade, `Trailer`, `TE`, `Proxy-Connection`, canonical `Connection` token-list, lifecycle-conflict, critical-nomination, duplicate-option, singleton-Connection-field, `Keep-Alive`, `HTTP2-Settings`, WebSocket-metadata, `Proxy-Authorization`, `Authorization` nomination, `Cookie` nomination, `Forwarded` nomination, `X-Forwarded-For` nomination, `X-Forwarded-Host` nomination, `X-Forwarded-Proto` nomination, `X-Forwarded-Port` nomination, `X-Forwarded-Prefix` nomination, `X-Forwarded-Ssl` nomination, `X-Forwarded-Server` nomination, `X-Forwarded-Uri` nomination, `X-Original-URI` nomination, `X-Original-URL` nomination, `X-Rewrite-URL` nomination, `X-Forwarded-Scheme` nomination, and `X-Real-IP` nomination gates succeed, the server rejects any exact `x-client-ip` Connection option before endpoint or runtime evaluation while continuing to admit ordinary `X-Client-IP` fields.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6.6.6.3.3.1.2.3.4.5.6 X-Client-IP Connection-nomination containment

- **X-Client-IP remains end-to-end.** A normal request `X-Client-IP` field remains admissible when all inherited gates accept it.
- **Hop-by-hop demotion is terminal.** An exact `x-client-ip` Connection option is rejected through canonical `400 Request Rejected` framing.
- **Matching is case-insensitive.** `Connection: X-Client-IP` and mixed-case variants are rejected.
- **Substring lookalikes remain outside this rule.** Options such as `x-client-ip-x` remain valid when otherwise admissible.
- **X-Client-IP values are opaque.** This layer examines only Connection option names and does not interpret, log, split, validate, normalize, or trust `X-Client-IP` values.
- **HTTP/1.0 and HTTP/1.1 are covered.** X-Client-IP nomination is refused under either admitted request version.
- **Earlier gates retain precedence.** `Expect`, `Upgrade`, `HTTP2-Settings`, WebSocket metadata, `Keep-Alive`, `Proxy-Authorization`, `Authorization` nomination, `Cookie` nomination, `Forwarded` nomination, `X-Forwarded-For` nomination, `X-Forwarded-Host` nomination, `X-Forwarded-Proto` nomination, `X-Forwarded-Port` nomination, `X-Forwarded-Prefix` nomination, `X-Forwarded-Ssl` nomination, `X-Forwarded-Server` nomination, `X-Forwarded-Uri` nomination, `X-Original-URI` nomination, `X-Original-URL` nomination, `X-Rewrite-URL` nomination, `X-Forwarded-Scheme` nomination, `X-Real-IP` nomination, malformed Connection lists, lifecycle conflicts, critical nomination, duplicate options, repeated Connection fields, `TE`, and `Proxy-Connection` still run before this layer.
- **The canonical Expect contract remains intact.** A request that also carries `Expect` is rejected by the earlier `417 Request Rejected` gate and emits no interim `100 Continue` response.
- **X-Client-IP-nomination failures use canonical terminal 400 framing.** Rejection closes the connection so trailing bytes cannot become a pipelined follow-on request.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without sending the rejection body.
- **Runtime/endpoint evaluation remains isolated.** X-Client-IP nomination cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Rejection releases its bounded worker slot.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v1666666666331123456`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, canonical origin-form request-target containment, obsolete folded-header rejection, strict request-header field-name grammar, strict request-header field-value octets, request-expectation rejection, strict HTTP/1.1 Host authority syntax, canonical request-line separator containment, malformed percent-escape rejection, canonical CRLF request/header line endings, protocol-upgrade containment, request `Trailer` declaration containment, request `TE` negotiation containment, `Proxy-Connection` containment, canonical `Connection` token-list containment, `Connection` lifecycle conflict containment, critical `Connection`-option nomination containment, duplicate `Connection`-option containment, singleton `Connection`-field containment, request `Keep-Alive` field containment, `HTTP2-Settings` request containment, WebSocket handshake-metadata containment, `Proxy-Authorization` credential-channel containment, `Authorization` Connection-nomination containment, `Cookie` Connection-nomination containment, `Forwarded` Connection-nomination containment, `X-Forwarded-For` Connection-nomination containment, `X-Forwarded-Host` Connection-nomination containment, `X-Forwarded-Proto` Connection-nomination containment, `X-Forwarded-Port` Connection-nomination containment, `X-Forwarded-Prefix` Connection-nomination containment, `X-Forwarded-Ssl` Connection-nomination containment, `X-Forwarded-Server` Connection-nomination containment, `X-Forwarded-Uri` Connection-nomination containment, `X-Original-URI` Connection-nomination containment, `X-Original-URL` Connection-nomination containment, `X-Rewrite-URL` Connection-nomination containment, `X-Forwarded-Scheme` Connection-nomination containment, `X-Real-IP` Connection-nomination containment, then `X-Client-IP` Connection-nomination containment.

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
25. Any physical `Proxy-Authorization` request field or exact `proxy-authorization` Connection option is terminally rejected; ordinary `Authorization` remains outside that rule.
26. An exact `authorization` Connection option is terminally rejected; an ordinary `Authorization` field remains end-to-end and admissible when otherwise valid.
27. An exact `cookie` Connection option is terminally rejected; an ordinary `Cookie` field remains end-to-end and admissible when otherwise valid.
28. An exact `forwarded` Connection option is terminally rejected; an ordinary `Forwarded` field remains end-to-end and admissible when otherwise valid.
29. An exact `x-forwarded-for` Connection option is terminally rejected; an ordinary `X-Forwarded-For` field remains end-to-end and admissible when otherwise valid.
30. An exact `x-forwarded-host` Connection option is terminally rejected; an ordinary `X-Forwarded-Host` field remains end-to-end and admissible when otherwise valid.
31. An exact `x-forwarded-proto` Connection option is terminally rejected; an ordinary `X-Forwarded-Proto` field remains end-to-end and admissible when otherwise valid.
32. An exact `x-forwarded-port` Connection option is terminally rejected; an ordinary `X-Forwarded-Port` field remains end-to-end and admissible when otherwise valid.
33. An exact `x-forwarded-prefix` Connection option is terminally rejected; an ordinary `X-Forwarded-Prefix` field remains end-to-end and admissible when otherwise valid.
34. An exact `x-forwarded-ssl` Connection option is terminally rejected; an ordinary `X-Forwarded-Ssl` field remains end-to-end and admissible when otherwise valid.
35. An exact `x-forwarded-server` Connection option is terminally rejected; an ordinary `X-Forwarded-Server` field remains end-to-end and admissible when otherwise valid.
36. An exact `x-forwarded-uri` Connection option is terminally rejected; an ordinary `X-Forwarded-Uri` field remains end-to-end and admissible when otherwise valid.
37. An exact `x-original-uri` Connection option is terminally rejected; an ordinary `X-Original-URI` field remains end-to-end and admissible when otherwise valid.
38. An exact `x-original-url` Connection option is terminally rejected; an ordinary `X-Original-URL` field remains end-to-end and admissible when otherwise valid.
39. An exact `x-rewrite-url` Connection option is terminally rejected; an ordinary `X-Rewrite-URL` field remains end-to-end and admissible when otherwise valid.
40. An exact `x-forwarded-scheme` Connection option is terminally rejected; an ordinary `X-Forwarded-Scheme` field remains end-to-end and admissible when otherwise valid.
41. An exact `x-real-ip` Connection option is terminally rejected; an ordinary `X-Real-IP` field remains end-to-end and admissible when otherwise valid.
42. An exact `x-client-ip` Connection option is terminally rejected; an ordinary `X-Client-IP` field remains end-to-end and admissible when otherwise valid.
43. HEAD rejection remains bodyless while preserving representation `Content-Length`.
44. Rejected requests cannot process trailing pipelined bytes on the same connection.
45. Rejection releases bounded worker capacity.
46. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
47. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
48. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
49. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
50. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.6.6.3.3.1.2.3.4.5.6.
