# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.6.3

`nvlx` v1.6.6.6.6.6.3 bounds concurrent live HTTP request admission before request threads are created. The health server now has a finite worker-slot budget, so a burst of slow or idle clients cannot grow request-thread count without bound.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.6.3 bounded live HTTP admission

- **Concurrent handler admission is bounded.** The live server permits 32 request threads by default.
- **Saturation is rejected before parsing.** When all request slots are occupied, new connections are closed at the transport boundary without spawning a request worker or invoking endpoint/runtime logic.
- **HEAD semantics stay coherent.** Saturation does not emit a method-blind HTTP body before the request has been parsed; accepted GET/HEAD requests retain their established contracts.
- **Capacity is always released.** Worker slots are returned after normal responses, parser rejection, client-abort containment, timeout handling, and other request-thread completion paths.
- **Thread-start failures do not leak capacity.** Admission acquired before worker creation is released if request-thread startup itself fails.
- **Capacity validation is strict.** Embedded callers may override `max_concurrent_requests`, but it must be an exact positive integer; booleans, floats, strings, zero, and negative values are rejected.
- **Ingress-idle timeout remains intact.** v1.6.6.6.6.6.2 still applies a 5-second request-read timeout to accepted sockets.
- **Completed response contracts are unchanged.** `/livez`, `/readyz`, `/metrics`, parser `400/414/431/505`, resource `404`, method `405`, metrics `500`, GET/HEAD parity, and exact framing are unchanged for admitted requests.
- **The live operator now uses `http_v1666663`.** The live runtime remains `runtime_v1664`.
- **Checkpoint persistence, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation behavior are unchanged.**

## Admission contract

`HealthServer(..., max_concurrent_requests=32)` uses a bounded semaphore to reserve one slot before `ThreadingHTTPServer` creates a request thread. When no slot is available, the accepted socket is immediately shut down and closed without parsing bytes from the request.

This preserves the strongest useful boundary: excess clients consume neither an application request thread nor readiness/metrics evaluation, while admitted clients continue to use the existing parser, timeout, logging, and client-abort containment stack.

## Safety invariants

1. Live request-thread count cannot exceed the configured admission capacity.
2. Saturated connections never reach endpoint or runtime logic.
3. Saturation rejection is transport-level and non-reflective.
4. Every admitted worker returns its slot on completion.
5. Capacity is returned if worker creation fails before the request thread starts.
6. The v1.6.6.6.6.6.2 ingress read timeout remains active for admitted requests.
7. v1.6.6.6.6.6.1 server-level expected-abort traceback containment remains unchanged.
8. v1.6.6.6.6.6 handler-level response-write/final-cleanup containment remains unchanged.
9. Canonical parser status lines, bodyless framing, resource-aware `404/405`, unified GET/HEAD dispatch, and typed diagnosis propagation remain unchanged.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.6.3.
