# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.5

`nvlx` v1.6.6.6.6.5 makes the live HTTP logging sink strictly best-effort. A closed, missing, replaced, or failing stderr destination can no longer change endpoint status, framing, parser containment, or connection behavior.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.5 best-effort log-sink containment

- **Logging cannot break serving.** Exceptions raised by the stderr sink are contained inside the logging boundary and never escape into HTTP handling.
- **Closed or missing stderr is safe.** `OSError`, `BrokenPipeError`, `ValueError`, `AttributeError`, and other ordinary sink failures do not alter live responses.
- **Only ordinary exceptions are contained.** Process-control signals represented by `BaseException` subclasses remain outside this diagnostic containment boundary.
- **Successful GET/HEAD behavior is unchanged.** `/livez` continues to return `200`, and HEAD continues to preserve representation headers while suppressing the body.
- **Parser containment is unchanged.** Malformed requests retain canonical `HTTP/1.0 <code> Request Rejected` responses, fixed body, exact framing, and terminal `Connection: close`.
- **Method/resource containment is unchanged.** Exact live resources retain terminal `405 Method Not Allowed` with `Allow: GET, HEAD`; unknown resources retain resource-aware `404` behavior.
- **Metrics containment is unchanged.** Exporter/capture failures still return deterministic `500 metrics unavailable\n` even if logging is unavailable.
- **Non-reflective logging remains intact when the sink works.** The v1.6.6.6.6.4 bounded server-owned log markers are unchanged.
- **The live operator now uses `http_v166665`.** The live runtime remains `runtime_v1664`.
- **Checkpoint, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation semantics are unchanged.**

## Logging failure contract

The live handler still emits only bounded server-owned lines when stderr is healthy:

- `nvlx http status=<code>`;
- `nvlx http error`;
- `nvlx http event`.

If writing one of those lines raises an ordinary `Exception`, the logging attempt is discarded and request processing continues. No fallback log destination is attempted and no HTTP response field is changed because of a logging failure.

## Safety invariants

1. Diagnostic logging is never a prerequisite for serving `/livez`, `/readyz`, or `/metrics`.
2. Parser `400/414/431/505`, method `405`, unknown-resource `404`, and metrics `500` behavior do not depend on stderr availability.
3. HEAD body suppression and representation `Content-Length` remain unchanged when logging fails.
4. Request-controlled text still never enters the live handler's default log lines when logging succeeds.
5. v1.6.6.6.6.4 non-reflective bounded logging remains unchanged.
6. v1.6.6.6.6.3 canonical parser status lines remain unchanged.
7. v1.6.6.6.6.1 canonical zero-length framing and v1.6.6.6.5 terminal method rejection remain unchanged.
8. Typed-provider symmetry and all v1.6.6.x diagnosis validation remain unchanged.
9. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.5.
