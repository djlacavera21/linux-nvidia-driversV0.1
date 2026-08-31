# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6.6.6.3.3.1.2.3.4.5.6.7.5.6.7.3

`nvlx` v1.6.6.6.6.6.6.6.6.6.3.3.1.2.3.4.5.6.7.5.6.7.3 adds `X-Envoy-Downstream-Service-Cluster` Connection-nomination containment to the live HTTP surface. After inherited ingress and proxy-metadata gates succeed, the server rejects an exact `x-envoy-downstream-service-cluster` Connection option before endpoint/runtime evaluation while continuing to admit ordinary `X-Envoy-Downstream-Service-Cluster` fields.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6.6.6.3.3.1.2.3.4.5.6.7.5.6.7.3 X-Envoy-Downstream-Service-Cluster Connection-nomination containment

- **Ordinary caller-cluster metadata remains admissible.** `X-Envoy-Downstream-Service-Cluster` is accepted when all inherited gates accept the request.
- **Hop-by-hop demotion is terminal.** Exact `x-envoy-downstream-service-cluster` Connection nomination receives canonical `400 Request Rejected` framing.
- **Matching is case-insensitive.** Mixed-case exact nominations are rejected.
- **Substring lookalikes remain outside this rule.** `x-envoy-downstream-service-cluster-x` remains valid when otherwise admissible.
- **Values remain opaque at this layer.** This containment examines only Connection option names. Envoy sanitizes this header on external requests; for internal requests it carries caller service-cluster metadata and should be treated as a caller-supplied hint rather than authenticated identity.
- **HTTP/1.0 and HTTP/1.1 are covered.**
- **Earlier gates retain precedence.** The complete inherited framing, credential, forwarding/client-address, Envoy timeout/retry/hedging, retriable-header/status, alt-stat, timeout-alt-response, timeout-retry-provenance, original-host, and upstream-stream-duration gates run before this layer.
- **Expect handling remains canonical.** Requests carrying `Expect` still terminate through the inherited `417 Request Rejected` path with no interim `100 Continue`.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without sending the rejection body.
- **Pipeline and runtime isolation remain intact.** Rejected requests cannot dispatch trailing pipelined bytes or invoke readiness/metrics evaluation.
- **Admission capacity recovers normally.** Rejection releases its bounded worker slot.
- **Ingress budgets are unchanged.** 8 KiB request line, 32 KiB aggregate headers, 32 fields, 5-second idle timeout, 5-second absolute header deadline, 32 concurrent requests.
- **The live operator now uses `http_v166666666633112345675673`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

1. `max_concurrent_requests` — default 32.
2. `request_timeout_seconds` — default 5 seconds.
3. `request_header_deadline_seconds` — default 5 seconds.
4. `max_request_line_bytes` — default 8192 bytes.
5. `max_request_header_bytes` — default 32768 bytes.
6. `max_request_header_fields` — default 32 fields.

Protocol invariants remain fail-closed in the inherited order: request framing and target syntax; header grammar and value-octet containment; `Expect`; upgrade/Trailer/TE/Proxy-Connection; canonical Connection parsing/lifecycle/critical nomination/duplication/singleton enforcement; Keep-Alive/HTTP2-Settings/WebSocket/Proxy-Authorization; Authorization/Cookie/Forwarded and forwarding/client-IP nomination containment; Envoy external/original/internal/attempt/decorator/timeout metadata; `X-Envoy-Retry-On`; `X-Envoy-Retry-Grpc-On`; `X-Envoy-Max-Retries`; `X-Envoy-Hedge-On-Per-Try-Timeout`; `X-Envoy-Retriable-Header-Names`; `X-Envoy-Retriable-Status-Codes`; `X-Envoy-Upstream-Alt-Stat-Name`; `X-Envoy-Upstream-Rq-Timeout-Alt-Response`; `X-Envoy-Is-Timeout-Retry`; `X-Envoy-Original-Host`; `X-Envoy-Upstream-Stream-Duration-Ms`; then `X-Envoy-Downstream-Service-Cluster`.

## Safety invariants

1. CPython legacy headerless parser representation is accepted only when it is an exact empty mapping.
2. HTTP/0.9 and unsupported/non-canonical HTTP/1.x requests are rejected before endpoint/runtime evaluation.
3. HTTP/1.1 requires exactly one valid non-empty Host authority.
4. Raw request targets must survive parsing unchanged and begin with exactly one `/`.
5. Absolute/authority/asterisk forms, fragments, backslashes, controls, and raw non-ASCII target bytes are rejected.
6. Percent escapes must contain exactly two ASCII hex digits.
7. Obsolete folded request headers are rejected.
8. Physical header names must use strict ASCII token grammar and be followed immediately by `:`.
9. Physical field values are limited to HTAB, SP, and visible ASCII.
10. Any `Expect` field is rejected with canonical terminal 417 framing and no `100 Continue`.
11. Request-line token separators must reconstruct canonically with single ASCII spaces.
12. Request/header lines and the blank terminator must use CRLF.
13. `Upgrade` fields and exact `upgrade` Connection tokens are rejected.
14. Request `Trailer` declarations are rejected.
15. Request `TE` fields and exact `te` Connection tokens are rejected.
16. `Proxy-Connection` fields and exact `proxy-connection` Connection tokens are rejected.
17. Remaining Connection fields must be non-empty comma-separated ASCII token lists.
18. Connection lifecycle conflicts between `close` and `keep-alive` are rejected.
19. Connection options may not nominate Host, Content-Length, Transfer-Encoding, Trailer, Expect, or Connection.
20. Remaining Connection options may appear only once case-insensitively.
21. At most one physical Connection field may remain after inherited gates succeed.
22. Physical Keep-Alive request fields are rejected.
23. HTTP2-Settings request fields and exact nominations are rejected.
24. `Sec-WebSocket-*` request fields are rejected.
25. Proxy-Authorization request fields and exact nominations are rejected.
26. Exact `authorization` nomination is rejected while ordinary Authorization remains admissible when otherwise valid.
27. Exact `cookie` nomination is rejected while ordinary Cookie remains admissible when otherwise valid.
28. Exact `forwarded` nomination is rejected while ordinary Forwarded remains admissible when otherwise valid.
29. Exact `x-forwarded-for` nomination is rejected.
30. Exact `x-forwarded-host` nomination is rejected.
31. Exact `x-forwarded-proto` nomination is rejected.
32. Exact `x-forwarded-port` nomination is rejected.
33. Exact `x-forwarded-prefix` nomination is rejected.
34. Exact `x-forwarded-ssl` nomination is rejected.
35. Exact `x-forwarded-server` nomination is rejected.
36. Exact `x-forwarded-uri` nomination is rejected.
37. Exact `x-original-uri` nomination is rejected.
38. Exact `x-original-url` nomination is rejected.
39. Exact `x-rewrite-url` nomination is rejected.
40. Exact `x-forwarded-scheme` nomination is rejected.
41. Exact `x-real-ip` nomination is rejected.
42. Exact `x-client-ip` nomination is rejected.
43. Exact `true-client-ip` nomination is rejected.
44. Exact `cf-connecting-ip` nomination is rejected.
45. Exact `x-cluster-client-ip` nomination is rejected.
46. Exact `fastly-client-ip` nomination is rejected.
47. Exact `fly-client-ip` nomination is rejected.
48. Exact `x-envoy-external-address` nomination is rejected.
49. Exact `x-envoy-original-dst-host` nomination is rejected.
50. Exact `x-envoy-original-path` nomination is rejected.
51. Exact `x-envoy-original-url` nomination is rejected.
52. Exact `x-envoy-internal` nomination is rejected.
53. Exact `x-envoy-attempt-count` nomination is rejected.
54. Exact `x-envoy-decorator-operation` nomination is rejected.
55. Exact `x-envoy-expected-rq-timeout-ms` nomination is rejected.
56. Exact `x-envoy-upstream-rq-timeout-ms` nomination is rejected.
57. Exact `x-envoy-upstream-rq-per-try-timeout-ms` nomination is rejected.
58. Exact `x-envoy-retry-on` nomination is rejected.
59. Exact `x-envoy-retry-grpc-on` nomination is rejected.
60. Exact `x-envoy-max-retries` nomination is rejected.
61. Exact `x-envoy-hedge-on-per-try-timeout` nomination is rejected.
62. Exact `x-envoy-retriable-header-names` nomination is rejected; ordinary `X-Envoy-Retriable-Header-Names` remains admissible when otherwise valid.
63. Exact `x-envoy-retriable-status-codes` nomination is rejected; ordinary `X-Envoy-Retriable-Status-Codes` remains admissible when otherwise valid.
64. Exact `x-envoy-upstream-alt-stat-name` nomination is rejected; ordinary `X-Envoy-Upstream-Alt-Stat-Name` remains admissible when otherwise valid.
65. Exact `x-envoy-upstream-rq-timeout-alt-response` nomination is rejected; ordinary `X-Envoy-Upstream-Rq-Timeout-Alt-Response` remains admissible when otherwise valid.
66. Exact `x-envoy-is-timeout-retry` nomination is rejected; ordinary `X-Envoy-Is-Timeout-Retry` remains admissible when otherwise valid.
67. Exact `x-envoy-original-host` nomination is rejected; ordinary `X-Envoy-Original-Host` remains admissible when otherwise valid.
68. Exact `x-envoy-upstream-stream-duration-ms` nomination is rejected; ordinary `X-Envoy-Upstream-Stream-Duration-Ms` remains admissible when otherwise valid.
69. Exact `x-envoy-downstream-service-cluster` nomination is rejected; ordinary `X-Envoy-Downstream-Service-Cluster` remains admissible when otherwise valid.
70. HEAD rejection remains bodyless while preserving representation `Content-Length`.
71. Rejected requests cannot process trailing pipelined bytes on the same connection.
72. Rejection releases bounded worker capacity.
73. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
74. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
75. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
76. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
77. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.6.6.3.3.1.2.3.4.5.6.7.5.6.7.3.
