# nvlx: Linux-NVIDIA-Driver v1.6.6.6.2

`nvlx` v1.6.6.6.2 makes GET/HEAD parity structural instead of duplicated. Both methods now resolve `/livez`, `/readyz`, and `/metrics` through one versioned dispatcher, differing only in whether the resolved representation body is written.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.2 unified GET/HEAD dispatch

- **One live request resolver.** GET and HEAD now share the same path-to-representation resolution for `/livez`, `/readyz`, and `/metrics`.
- **Parity is structural.** Status, content type, `Cache-Control: no-store`, stable `Server: nvlx`, and representation `Content-Length` come from the same resolved response object for both methods.
- **Only body transmission differs.** GET writes the resolved UTF-8 payload; HEAD writes zero response-body bytes.
- **Ready/not-ready behavior is unchanged.** `/readyz` still returns `200 ready\n` or `503 not ready\n` from the established strict typed readiness boundary.
- **Metrics behavior is unchanged.** Successful `/metrics` still renders the frozen Prometheus snapshot; failures remain the deterministic `500 metrics unavailable\n` contract.
- **Unknown paths remain unchanged.** GET and HEAD both retain the established empty `404` response outside the live-state helper contract.
- **Typed-provider symmetry remains intact.** Metrics-only and readiness-only typed providers retain the v1.6.6.6/v1.6.6.5 propagation rules and strict validation.
- **The live operator now uses `http_v16662`.** The live runtime remains `runtime_v1664`.
- **Historical modules remain immutable.** The structural dispatcher is layered in a new versioned HTTP module.
- **Checkpoint semantics are unchanged.** Receipt proof, digest validation, ambiguity recovery, reconciliation accounting, rollback fencing, replay floors, and Lease-epoch behavior are untouched.
- **No RBAC expansion.** No new Kubernetes mutation path is introduced.

## Unified request contract

For `/livez`, `/readyz`, and `/metrics`, the server first resolves exactly one representation containing:

- HTTP status;
- UTF-8 representation body;
- content type.

The same send path then applies `Cache-Control: no-store`, stable server identity, and byte-accurate `Content-Length`. GET writes the representation body; HEAD does not.

This removes the separate GET and HEAD routing implementations introduced during incremental hardening and prevents future endpoint-policy changes from updating one method while accidentally leaving the other behind.

## Safety invariants

1. GET and HEAD use the same live representation resolver.
2. HEAD never writes live-state response bytes.
3. GET retains the exact established response bodies.
4. Ready `200` and not-ready `503` semantics remain unchanged.
5. Metrics success and deterministic failure containment remain unchanged.
6. Unknown GET/HEAD paths retain the empty `404` contract.
7. v1.6.6.6 partial typed-provider symmetry remains unchanged.
8. v1.6.6.5 readiness propagation into metrics fallback remains unchanged.
9. v1.6.6.4 effective-leadership validation remains active.
10. v1.6.6.3 logical readiness validation remains unchanged.
11. v1.6.6.2 typed metric value-domain validation remains unchanged.
12. v1.6.6.1 strict diagnosis typing remains unchanged.
13. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
14. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.2.
