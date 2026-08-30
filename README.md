# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.1

`nvlx` v1.6.6.6.6.1 canonicalizes the explicit zero-length framing accepted by the live GET/HEAD surface. Exact `/livez`, `/readyz`, and `/metrics` requests remain bodyless, but when `Content-Length` is present the only accepted field value is exactly `0`.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.1 canonical zero-length framing

- **Only exact `Content-Length: 0` is accepted.** Alternate zero encodings such as `00`, `000`, signed forms, hexadecimal-looking forms, or comma-joined values are rejected.
- **No length header remains valid.** Bodyless live GET/HEAD requests do not need to send `Content-Length`.
- **Duplicate lengths remain invalid.** Even repeated canonical zero fields retain the v1.6.6.6.6 fail-closed behavior.
- **Any `Transfer-Encoding` remains invalid.** Chunked or alternate request-body framing never reaches the live endpoint logic.
- **Rejection precedes runtime evaluation.** Noncanonical framing on `/readyz` or `/metrics` cannot invoke readiness diagnosis, checkpoint observation, metrics capture, or rendering.
- **Rejection remains terminal.** Invalid live framing returns deterministic `400 request rejected\n`, sets `Connection: close`, and prevents a following request from being parsed on that connection.
- **HEAD remains bodyless.** Invalid HEAD requests return the same status and representation metadata as GET but no response-body bytes.
- **Unknown paths retain the existing `404` contract.** The canonical framing rule applies only to exact live resources.
- **Unsupported-method behavior remains unchanged.** v1.6.6.6.5 terminal resource-aware `405`/`404` rejection remains authoritative for methods other than GET/HEAD.
- **The live operator now uses `http_v166661`.** The live runtime remains `runtime_v1664`.
- **Checkpoint, RBAC, readiness, metrics schema, and NVIDIA mutation semantics are unchanged.**

## Canonical framing contract

For exact `/livez`, `/readyz`, and `/metrics` GET/HEAD requests:

- `Transfer-Encoding` is forbidden;
- zero or one `Content-Length` field is permitted;
- when present, the parsed field value must be exactly the ASCII string `0`;
- all other request-body framing fails closed before endpoint evaluation.

This narrows representation syntax only. It does not change the successful live endpoint representations, readiness policy, Prometheus schema, typed diagnosis contracts, checkpoint receipts/reconciliation, or Kubernetes mutation scope.

## Safety invariants

1. Exact live GET/HEAD resources remain bodyless.
2. The only explicit accepted length is canonical `Content-Length: 0`.
3. Noncanonical zero spellings never reach endpoint logic.
4. Invalid live framing remains deterministic, non-reflective, and terminal.
5. Valid GET/HEAD, readiness `200/503`, metrics success/`500`, and HEAD parity remain unchanged.
6. Unknown-resource `404` identity remains unchanged.
7. v1.6.6.6.5 terminal unsupported-method transport remains unchanged.
8. v1.6.6.6 typed-provider symmetry and all v1.6.6.x diagnosis validation remain unchanged.
9. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.1.
