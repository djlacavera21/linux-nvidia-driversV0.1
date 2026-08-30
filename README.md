# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6.4

`nvlx` v1.6.6.6.6.6.6.6.4 repairs the v1.6.6.6.6.6.6.6.3 canonical `417 Request Rejected` contract and adds strict HTTP/1.1 Host authority syntax containment. After the inherited body-framing, version, singleton Host, request-target, header syntax, and `Expect` gates succeed, the required HTTP/1.1 Host value must be an unambiguous operational authority before endpoint or runtime evaluation.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6.4 Host authority containment

- **The v1.6.6.6.6.6.6.6.3 417 wire contract is repaired.** Rejected `Expect` fields now call the inherited canonical error writer directly, producing `HTTP/1.0 417 Request Rejected`, fixed body framing, `Connection: close`, and no interim `100 Continue` response.
- **HTTP/1.1 Host values now require a conservative authority form.** Common DNS/Kubernetes-style names, IPv4 literals, bracketed IPv6 literals, and optional decimal ports are admitted.
- **Kubernetes-style names remain compatible.** Hyphens, underscores, dots, and an optional final root dot are accepted within bounded labels.
- **IPv6 must be bracketed.** Forms such as `[::1]` and `[2001:db8::1]:8443` are admitted; raw `::1`, malformed brackets, zone identifiers, and invalid literals are rejected.
- **Ports are explicit decimal values from 1 through 65535.** Empty, signed, non-numeric, zero, oversized, and out-of-range ports are rejected.
- **URI/userinfo ambiguity is rejected.** Host values containing `@`, scheme syntax, slash, backslash, query, fragment, or internal whitespace are terminally rejected.
- **Invalid dotted-numeric spellings do not fall through to reg-name interpretation.** A malformed value such as `999.1.1.1` is rejected.
- **HTTP/1.0 compatibility is intentionally unchanged.** This release validates the required HTTP/1.1 Host authority and leaves optional HTTP/1.0 Host semantics untouched.
- **Earlier gates retain precedence.** Body framing, exact version admission, Host cardinality, request-target syntax, obsolete folding, field-name/value syntax, and `Expect` containment still run before this final authority gate.
- **Host authority failures use canonical terminal 400 framing.** Rejected bytes cannot become a pipelined follow-on request.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without sending the rejection body.
- **Runtime/endpoint evaluation remains isolated.** Invalid Host authorities cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Rejection releases its bounded worker slot.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v166666664`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, canonical origin-form request-target containment, obsolete folded-header rejection, strict request-header field-name grammar, strict request-header field-value octets, request-expectation rejection, then strict HTTP/1.1 Host authority syntax.

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
11. HEAD rejection remains bodyless while preserving representation `Content-Length`.
12. Rejected requests cannot process trailing pipelined bytes on the same connection.
13. Rejection releases bounded worker capacity.
14. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
15. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
16. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
17. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
18. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.4.
