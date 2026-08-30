# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6

`nvlx` v1.6.6.6.6 makes the live GET/HEAD request-body contract explicit. Exact `/livez`, `/readyz`, and `/metrics` requests are bodyless: zero `Content-Length` remains valid, while nonzero, malformed, duplicated `Content-Length` or any `Transfer-Encoding` is rejected before runtime diagnosis or metrics evaluation.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6 bodyless live requests

- **Live GET/HEAD requests are explicitly bodyless.** Exact `/livez`, `/readyz`, and `/metrics` requests accept no request body framing beyond an optional single `Content-Length: 0`.
- **Nonzero `Content-Length` fails closed.** Body-bearing live GET/HEAD requests return deterministic `400 request rejected\n` and close the connection.
- **Malformed or duplicated lengths are rejected.** Empty, non-decimal, comma-combined, or repeated `Content-Length` fields never reach endpoint logic.
- **Any `Transfer-Encoding` is rejected.** The live health/metrics surface does not accept chunked or alternate request-body framing.
- **Rejection happens before runtime evaluation.** Invalid `/readyz` and `/metrics` body framing cannot invoke readiness diagnosis, checkpoint observation, or metrics capture/rendering.
- **HEAD error framing remains representation-correct.** Invalid HEAD requests return the same `400` metadata and representation `Content-Length` as GET while emitting zero response-body bytes.
- **Body-framing rejection is terminal.** Responses set `Connection: close` and handler `close_connection=True`, preventing unread payload bytes from becoming a following request.
- **Unknown paths retain their existing resource contract.** The bodyless policy applies only to exact live resources; unknown, query-bearing, and trailing-slash targets keep the established `404` behavior.
- **Unsupported-method behavior remains unchanged.** v1.6.6.6.5 terminal `405`/resource-aware `404` rejection remains authoritative for methods other than GET/HEAD.
- **Unified GET/HEAD dispatch remains unchanged.** Valid bodyless live requests continue through the same v1.6.6.6.2 representation resolver.
- **Typed-provider symmetry remains intact.** Metrics-only and readiness-only diagnosis providers keep the established strict propagation and validation rules.
- **The live operator now uses `http_v16666`.** The live runtime remains `runtime_v1664`.
- **Checkpoint semantics are unchanged.** Receipt proof, digest validation, ambiguity recovery, reconciliation accounting, rollback fencing, replay floors, and Lease-epoch behavior are untouched.
- **No RBAC expansion.** No new Kubernetes mutation path is introduced.

## Bodyless request contract

For exact `/livez`, `/readyz`, and `/metrics` GET/HEAD requests:

- no `Transfer-Encoding` header is permitted;
- zero or one `Content-Length` header is permitted;
- when present, `Content-Length` must be a valid nonnegative decimal representation of exactly `0`;
- all other request-body framing is rejected before endpoint evaluation.

A rejected live GET request returns:

- HTTP `400`;
- fixed `request rejected\n` body;
- `Content-Type: text/plain; charset=utf-8`;
- `Cache-Control: no-store`;
- exact `Content-Length`;
- `Connection: close`;
- stable `Server: nvlx`.

A rejected live HEAD request returns the same status and headers, including the GET representation length, but no response-body bytes.

## Safety invariants

1. Exact live GET/HEAD resources are bodyless by contract.
2. Invalid body framing is rejected before readiness or metrics evaluation.
3. `Transfer-Encoding` is never accepted on the live observability surface.
4. Duplicate or malformed `Content-Length` never reaches endpoint logic.
5. Rejected body-framed requests close the connection before any following request can be parsed.
6. Zero-length valid requests retain the established GET/HEAD behavior.
7. Unknown-path resource identity and `404` behavior remain unchanged.
8. v1.6.6.6.5 terminal unsupported-method transport remains unchanged.
9. v1.6.6.6.4 resource-aware method identity remains unchanged.
10. Unified GET/HEAD dispatch, readiness `200/503`, and metrics success/`500` containment remain unchanged.
11. v1.6.6.6 partial typed-provider symmetry remains unchanged.
12. v1.6.6.5 readiness propagation into metrics fallback remains unchanged.
13. v1.6.6.4 effective-leadership validation remains active.
14. v1.6.6.3 logical readiness validation remains unchanged.
15. v1.6.6.2 typed metric value-domain validation remains unchanged.
16. v1.6.6.1 strict diagnosis typing remains unchanged.
17. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
18. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.
