# nvlx: Linux-NVIDIA-Driver v1.6.6.6.5

`nvlx` v1.6.6.6.5 makes unsupported-method rejection terminal at the HTTP transport boundary. The resource-aware `405`/`404` behavior from v1.6.6.6.4 remains intact, but rejected requests now explicitly close their connection so unread request-body bytes cannot be interpreted as a subsequent request.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.5 terminal method rejection

- **Rejected methods explicitly close the connection.** Known live-resource `405` responses and unknown-resource method `404` responses now send `Connection: close` and set the handler's connection state terminal.
- **Unread request bodies cannot desynchronize a following request.** The server does not consume unsupported-method bodies; instead it guarantees that no later request is parsed on that socket.
- **Known live resources keep the existing method contract.** Exact `/livez`, `/readyz`, and `/metrics` targets still return deterministic `405 Method Not Allowed`, `Allow: GET, HEAD`, fixed `request rejected\n`, `Cache-Control: no-store`, byte-accurate `Content-Length`, and `Server: nvlx`.
- **Unknown targets keep the minimal `404` contract.** They remain empty and expose no `Allow`, live-state cache metadata, or representation length; the only added transport signal is `Connection: close` for unsupported methods.
- **Arbitrary method tokens remain non-reflective.** Request method text and framework diagnostics are never copied into the response body.
- **GET and HEAD are unchanged.** The unified dispatcher from v1.6.6.6.2 continues to serve supported requests without forced connection closure.
- **Resource identity remains exact.** Query-bearing and trailing-slash targets are still nonexistent unless explicitly routed.
- **Typed-provider symmetry remains intact.** Metrics-only and readiness-only diagnosis providers keep the established strict propagation and validation rules.
- **The live operator now uses `http_v16665`.** The live runtime remains `runtime_v1664`.
- **Checkpoint semantics are unchanged.** Receipt proof, digest validation, ambiguity recovery, reconciliation accounting, rollback fencing, replay floors, and Lease-epoch behavior are untouched.
- **No RBAC expansion.** No new Kubernetes mutation path is introduced.

## Terminal rejection contract

For an unsupported method targeting a known live resource, the adapter returns the established `405` response plus:

- `Connection: close`;
- handler `close_connection=True`.

For an unsupported method targeting an unknown resource, the adapter returns the established empty `404` plus `Connection: close` and closes the socket after the response.

This is a containment rule, not request-body parsing. The implementation deliberately avoids reading or trusting unsupported request bodies and instead terminates the transport after rejection.

## Safety invariants

1. Unsupported methods never remain eligible for another request on the same connection.
2. Body-bearing rejected requests cannot poison or desynchronize a following request.
3. Only exact live resources advertise `Allow: GET, HEAD`.
4. Unsupported methods on nonexistent resources remain empty `404` responses.
5. Supported GET/HEAD transport behavior remains unchanged.
6. Unified GET/HEAD dispatch, readiness `200/503`, and metrics success/`500` containment remain unchanged.
7. v1.6.6.6 partial typed-provider symmetry remains unchanged.
8. v1.6.6.5 readiness propagation into metrics fallback remains unchanged.
9. v1.6.6.4 effective-leadership validation remains active.
10. v1.6.6.3 logical readiness validation remains unchanged.
11. v1.6.6.2 typed metric value-domain validation remains unchanged.
12. v1.6.6.1 strict diagnosis typing remains unchanged.
13. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
14. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.5.
