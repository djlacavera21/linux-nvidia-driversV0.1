# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.2

`nvlx` v1.6.6.6.6.2 makes framework-generated HTTP parser errors deterministic and terminal. Malformed request syntax, oversized request lines, header-overflow errors, and unsupported HTTP versions now use the same fixed plaintext containment style as the hardened live endpoint transport and explicitly close the connection.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.2 terminal parser-error containment

- **Parser errors never reflect request details.** Framework messages such as bad request syntax, oversized request-line descriptions, header parser diagnostics, and HTTP-version text are not returned to clients.
- **Covered parser statuses are explicit.** Inherited parser-generated `400`, `414`, `431`, and `505` responses are rewritten to the fixed `request rejected\n` representation.
- **Parser errors are connection-terminal.** Every contained parser error sets `Connection: close` and handler `close_connection=True`.
- **Parser response framing is cross-version deterministic.** Python 3.11/3.12 parser failures that would otherwise remain in HTTP/0.9 response mode are normalized to HTTP/1.0 response framing before the terminal error is emitted.
- **Following pipelined requests cannot survive a parse failure.** Once parsing fails, no later request is eligible to run on the same socket.
- **Framing remains byte-accurate.** Parser-error responses use `text/plain; charset=utf-8`, `Cache-Control: no-store`, exact `Content-Length`, and stable `Server: nvlx`.
- **Existing live request guards remain authoritative.** Canonical `Content-Length: 0`, `Transfer-Encoding` rejection, bodyless GET/HEAD rules, and the v1.6.6.6.6.1 framing contract are unchanged.
- **Method rejection remains unchanged.** Unsupported methods on exact live resources still return terminal `405 Method Not Allowed` with `Allow: GET, HEAD`; unknown resources retain their resource-aware `404` behavior.
- **Live endpoint semantics are unchanged.** `/livez`, `/readyz`, and `/metrics` retain unified GET/HEAD dispatch, readiness `200/503`, metrics success/`500`, HEAD parity, and typed diagnosis propagation.
- **The live operator now uses `http_v166662`.** The live runtime remains `runtime_v1664`.
- **Checkpoint, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation semantics are unchanged.**

## Parser containment contract

For framework parser failures with status `400`, `414`, `431`, or `505`, the live server returns:

- the original status code;
- fixed `request rejected\n` plaintext representation;
- `Content-Type: text/plain; charset=utf-8`;
- `Cache-Control: no-store`;
- exact representation `Content-Length`;
- `Connection: close`;
- stable `Server: nvlx`.

The parser-supplied message and explanation arguments are ignored. Parser-error response framing is normalized to the server's HTTP/1.0 wire baseline before emission so supported Python versions expose the same status/header/body contract. This is a transport-containment change only; accepted request parsing and all endpoint logic remain unchanged.

## Safety invariants

1. Parser-generated `400/414/431/505` responses are fixed-body and non-reflective.
2. Parser failures are always terminal for the current connection.
3. Parser-error status and headers are emitted consistently on Python 3.11, 3.12, and 3.13.
4. A malformed request cannot be followed by a processed pipelined request on the same socket.
5. v1.6.6.6.6.1 canonical zero-length framing remains unchanged.
6. v1.6.6.6.5 terminal unsupported-method transport remains unchanged.
7. Unified GET/HEAD dispatch, readiness `200/503`, metrics success/`500`, and HEAD parity remain unchanged.
8. Typed-provider symmetry and all v1.6.6.x diagnosis validation remain unchanged.
9. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.2.
