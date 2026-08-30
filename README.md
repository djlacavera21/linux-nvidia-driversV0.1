# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.4

`nvlx` v1.6.6.6.6.6.4 adds an absolute request-line/header deadline to the live HTTP server. The existing 5-second socket timeout remains an idle timeout; this release closes the slow-trickle gap by bounding the total time allowed to finish request-line and header parsing even when bytes keep arriving.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.4 absolute header deadline

- **Request-line and header parsing now has a total deadline.** The default is 5 seconds from the beginning of request parsing.
- **Byte trickling cannot hold a worker indefinitely.** Sending individual bytes faster than the idle timeout no longer bypasses ingress bounds.
- **The deadline is parsing-only.** It is canceled immediately after request-line/header parsing completes, before readiness, metrics, or response work begins.
- **Worker slots are recovered.** A header-deadline expiration closes only that connection and releases its bounded admission slot.
- **The server remains usable immediately afterward.** Fresh probes retain the established wire contracts.
- **Configuration remains bounded and validated.** `request_header_deadline_seconds` follows the same finite-positive validation domain as the existing request timeout.
- **The 5-second idle timeout remains intact.** Slow silent clients are still handled by the inherited ingress-idle protection.
- **The 32-request admission bound remains intact.** Saturated connections continue to be rejected before parsing/runtime evaluation.
- **Completed response behavior is unchanged.** GET/HEAD parity, parser `400/414/431/505`, resource `404`, method `405`, metrics `500`, canonical framing, non-reflective logging, and client-abort containment remain unchanged.
- **The live operator now uses `http_v1666664`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Ingress timing model

The live server now has two independent ingress timing controls:

1. `request_timeout_seconds` — idle timeout between socket reads, default 5 seconds.
2. `request_header_deadline_seconds` — absolute total deadline for request-line/header parsing, default 5 seconds.

The absolute deadline is canceled as soon as headers are completely parsed. Runtime evaluation and response generation are therefore not subject to this ingress watchdog.

## Safety invariants

1. A silent partial request cannot hold a worker indefinitely.
2. A byte-trickle partial request cannot hold a worker indefinitely.
3. Header-deadline expiration affects only the associated connection.
4. Bounded admission capacity is recovered after deadline expiration.
5. Runtime/readiness/metrics work is not terminated merely because it takes longer than the ingress header deadline.
6. Saturated connections never reach endpoint/runtime logic.
7. Existing client-abort, parser-error, logging, and body-framing containment remains unchanged.
8. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
9. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.4.
