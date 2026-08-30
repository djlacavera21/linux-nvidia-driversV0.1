# nvlx: Linux-NVIDIA-Driver v1.6.6.6.4

`nvlx` v1.6.6.6.4 makes the explicit live HTTP method contract resource-aware. `/livez`, `/readyz`, and `/metrics` still advertise GET/HEAD on unsupported methods, while nonexistent targets now retain the same empty `404` contract regardless of method and do not disclose `Allow` metadata.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.4 resource-aware method contract

- **Known live resources keep explicit method rejection.** Unsupported methods on exact `/livez`, `/readyz`, and `/metrics` targets return deterministic `405 Method Not Allowed` with `Allow: GET, HEAD`.
- **Unknown resources no longer advertise live methods.** Unsupported methods sent to nonexistent paths return the same empty `404` used by GET/HEAD.
- **Resource identity is exact.** Query-bearing and trailing-slash targets remain distinct nonexistent resources because the existing GET/HEAD dispatcher treats them that way.
- **No method reflection.** Live `405` bodies remain fixed at `request rejected\n`; arbitrary method tokens and framework details are never reflected.
- **Unknown-target 404s remain minimal.** They carry no `Allow`, no live-state `Cache-Control`, and no representation `Content-Length`.
- **Unified GET/HEAD dispatch remains unchanged.** v1.6.6.6.2 is still authoritative for successful live requests, readiness `200/503`, metrics success/`500`, and HEAD body suppression.
- **Typed-provider symmetry remains intact.** Metrics-only and readiness-only diagnosis providers keep the established strict propagation and validation rules.
- **The live operator now uses `http_v16664`.** The live runtime remains `runtime_v1664`.
- **Checkpoint semantics are unchanged.** Receipt proof, digest validation, ambiguity recovery, reconciliation accounting, rollback fencing, replay floors, and Lease-epoch behavior are untouched.
- **No RBAC expansion.** No new Kubernetes mutation path is introduced.

## Resource-aware rejection contract

For an unsupported method targeting `/livez`, `/readyz`, or `/metrics`, the adapter returns:

- HTTP `405 Method Not Allowed`;
- `Allow: GET, HEAD`;
- `Content-Type: text/plain; charset=utf-8`;
- `Cache-Control: no-store`;
- exact `Content-Length` for `request rejected\n`;
- stable `Server: nvlx`.

For an unsupported method targeting any other path, the adapter mirrors the established unknown-resource contract:

- HTTP `404`;
- empty body;
- no `Allow` header;
- no live-state cache or representation-length metadata.

## Safety invariants

1. Only exact live resources advertise the GET/HEAD method contract.
2. Unsupported methods on live resources remain deterministic, non-cacheable, and non-reflective.
3. Unsupported methods on nonexistent resources match the empty unknown-path `404` contract.
4. Query strings and trailing slashes do not implicitly alias live resources.
5. Unified GET/HEAD dispatch from v1.6.6.6.2 remains unchanged.
6. Metrics success and deterministic `500 metrics unavailable` containment remain unchanged.
7. v1.6.6.6 partial typed-provider symmetry remains unchanged.
8. v1.6.6.5 readiness propagation into metrics fallback remains unchanged.
9. v1.6.6.4 effective-leadership validation remains active.
10. v1.6.6.3 logical readiness validation remains unchanged.
11. v1.6.6.2 typed metric value-domain validation remains unchanged.
12. v1.6.6.1 strict diagnosis typing remains unchanged.
13. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
14. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.4.
