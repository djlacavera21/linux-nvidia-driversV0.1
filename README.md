# nvlx: Linux-NVIDIA-Driver v1.6.6.6.3

`nvlx` v1.6.6.6.3 makes the live HTTP method contract explicit. `/livez`, `/readyz`, and `/metrics` remain GET/HEAD-only; unsupported methods now receive a deterministic `405 Method Not Allowed` response with `Allow: GET, HEAD` instead of falling through the framework's generic `501` path.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.3 explicit method contract

- **GET and HEAD are the advertised live methods.** Unsupported methods now return `405` with `Allow: GET, HEAD`.
- **Method rejection remains contained.** The response body is the fixed `request rejected\n` payload; request method names and framework diagnostics are never reflected.
- **Method errors are non-cacheable and byte-framed.** They retain `Content-Type: text/plain; charset=utf-8`, `Cache-Control: no-store`, exact UTF-8 `Content-Length`, and stable `Server: nvlx`.
- **Arbitrary method tokens are covered.** Framework-generated unsupported-method `501` responses are translated into the explicit live `405` contract.
- **GET/HEAD behavior is unchanged.** v1.6.6.6.2 unified dispatch remains authoritative for `/livez`, `/readyz`, `/metrics`, and unknown-path empty `404` behavior.
- **Typed-provider symmetry remains intact.** Metrics-only and readiness-only diagnosis providers keep the established strict propagation and validation rules.
- **The live operator now uses `http_v16663`.** The live runtime remains `runtime_v1664`.
- **Checkpoint semantics are unchanged.** Receipt proof, digest validation, ambiguity recovery, reconciliation accounting, rollback fencing, replay floors, and Lease-epoch behavior are untouched.
- **No RBAC expansion.** No new Kubernetes mutation path is introduced.

## Method rejection contract

For unsupported methods, the live adapter returns:

- HTTP `405 Method Not Allowed`;
- `Allow: GET, HEAD`;
- `Content-Type: text/plain; charset=utf-8`;
- `Cache-Control: no-store`;
- exact `Content-Length` for `request rejected\n`;
- stable `Server: nvlx`;
- no reflected method name, parser detail, Python version, or BaseHTTP implementation detail.

Malformed-request and other framework errors continue through the established contained error path; only framework unsupported-method `501` responses are translated to the explicit live method contract.

## Safety invariants

1. GET and HEAD remain the only supported live HTTP methods.
2. Unsupported methods return deterministic `405` with `Allow: GET, HEAD`.
3. Method names and framework diagnostics are never reflected in the rejection payload.
4. Unified GET/HEAD dispatch from v1.6.6.6.2 remains unchanged.
5. Unknown GET/HEAD paths retain the empty `404` contract.
6. Metrics success and deterministic `500 metrics unavailable` containment remain unchanged.
7. v1.6.6.6 partial typed-provider symmetry remains unchanged.
8. v1.6.6.5 readiness propagation into metrics fallback remains unchanged.
9. v1.6.6.4 effective-leadership validation remains active.
10. v1.6.6.3 logical readiness validation remains unchanged.
11. v1.6.6.2 typed metric value-domain validation remains unchanged.
12. v1.6.6.1 strict diagnosis typing remains unchanged.
13. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
14. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.3.
