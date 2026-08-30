# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.6.6

`nvlx` v1.6.6.6.6.6.6.6 adds obsolete folded request-header (`obs-fold`) containment to the live HTTP surface. After the existing body-framing, request-version, Host, and canonical request-target gates succeed, the server now rejects any raw request-header continuation line beginning with space or tab. This prevents intermediary/parser disagreement over deprecated multiline header syntax before endpoint or runtime evaluation.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.6.6 obsolete folded-header containment

- **Obsolete header folding is rejected for every request header.** Any physical header continuation line beginning with SP or HTAB terminates through the canonical `400 Request Rejected` path.
- **Detection happens on raw header lines.** The new tracking reader observes continuation syntax before parsed header values can normalize or reinterpret it.
- **Normal inline whitespace remains compatible.** Horizontal tabs or spaces inside an ordinary header field value are not treated as continuation lines by this release.
- **HTTP/1.0 and HTTP/1.1 are covered.** The fold prohibition applies consistently after the existing exact request-version admission gate.
- **Existing Host containment keeps precedence.** Folded or otherwise ambiguous Host fields may still fail through the earlier HTTP/1.1 Host gate; generic folded headers are caught by the new final parser gate.
- **Body-framing and target gates keep precedence.** Invalid `Transfer-Encoding`/`Content-Length`, unsupported request versions, invalid HTTP/1.1 Host framing, and non-canonical request targets continue to fail closed before endpoint dispatch.
- **HEAD rejection remains bodyless.** Representation `Content-Length` is preserved without emitting the rejection body.
- **Fold rejection is terminal.** `Connection: close` prevents trailing bytes from becoming a second pipelined request.
- **Runtime/endpoint evaluation remains isolated.** Rejected folded headers cannot invoke readiness or metrics diagnosis.
- **Admission capacity recovers normally.** Fold rejection releases its bounded worker slot.
- **Existing ingress defenses remain intact.** The 8 KiB request-line budget, 32 KiB aggregate header budget, 32-field header cap, 5-second idle timeout, 5-second absolute header deadline, and 32-request admission cap are unchanged.
- **The live operator now uses `http_v16666666`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress resource model

The live server retains six independent quantitative ingress bounds:

1. `max_concurrent_requests` — admitted request workers, default 32.
2. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
3. `request_header_deadline_seconds` — absolute request-line/header parse deadline, default 5 seconds.
4. `max_request_line_bytes` — request-line byte budget, default 8192 bytes.
5. `max_request_header_bytes` — aggregate request-header byte budget, default 32768 bytes.
6. `max_request_header_fields` — request-header field-count budget, default 32 fields.

The quantitative budgets remain independent. Protocol invariants are enforced in a fail-closed chain: bodyless framing, exact HTTP/1.0 or HTTP/1.1 request version, HTTP/1.1 singleton Host framing, canonical origin-form request-target containment, then rejection of obsolete folded header lines.

## Safety invariants

1. CPython's legacy headerless parser representation is accepted only when it is an exact empty mapping.
2. HTTP/0.9 and unsupported/non-canonical HTTP/1.x requests remain terminally rejected before endpoint/runtime evaluation.
3. HTTP/1.1 requests require exactly one non-empty, non-folded, non-list-like Host field.
4. The raw request target must survive parsing unchanged and begin with exactly one `/`.
5. Absolute-form, authority-form, asterisk-form, fragments, backslashes, controls, and raw non-ASCII target bytes are rejected.
6. Any raw request-header continuation line beginning with SP or HTAB is rejected.
7. Fold rejection uses canonical terminal `400 Request Rejected` framing with `Connection: close`.
8. HEAD rejection remains bodyless while preserving representation `Content-Length`.
9. Rejected requests cannot process trailing pipelined bytes on the same connection.
10. Rejection releases bounded worker capacity.
11. Header field-count, aggregate header bytes, and request-line byte budgets remain independently enforced.
12. Silent and byte-trickle partial requests remain bounded by the inherited idle timeout and absolute parse deadline.
13. Existing client-abort, parser-error, logging, response-body, resource, and method containment remains unchanged.
14. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
15. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.6.6.
