# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.3

`nvlx` v1.6.6.6.6.3 removes Python/BaseHTTP parser reason-phrase fingerprinting from the live transport. Parser failures keep their original numeric status while using one stable status phrase across Python 3.11, 3.12, and 3.13.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.3 canonical parser status lines

- **One stable parser reason phrase.** Contained parser failures now emit `Request Rejected` instead of framework-defined phrases such as `Bad Request`, `Request-URI Too Long`, `Request Header Fields Too Large`, or `HTTP Version Not Supported`.
- **Numeric parser status is preserved.** Malformed syntax remains `400`, oversized request lines remain `414`, header overflow remains `431`, and unsupported HTTP versions remain `505`.
- **Cross-version wire parity is structural.** Every contained parser failure begins with `HTTP/1.0 <code> Request Rejected` on supported Python versions.
- **Parser bodies remain fixed and non-reflective.** The body is still exactly `request rejected\n`; request text, parser explanations, and oversized request material are not returned.
- **Parser failures remain terminal.** `Connection: close` and handler `close_connection=True` still prevent a failed parse from reaching a later pipelined request.
- **Framing remains byte-accurate.** Parser errors retain `Server: nvlx`, `text/plain; charset=utf-8`, `Cache-Control: no-store`, and exact `Content-Length`.
- **Explicit method behavior is unchanged.** Unsupported methods on exact live resources still use `405 Method Not Allowed` with `Allow: GET, HEAD`; unknown resources retain resource-aware `404` behavior.
- **Successful endpoint reasons are unchanged.** Normal live responses continue to use their established standard status phrases such as `200 OK`.
- **Canonical bodyless request framing remains unchanged.** The v1.6.6.6.6.1 `Content-Length: 0` and `Transfer-Encoding` rules remain authoritative.
- **Live endpoint semantics are unchanged.** `/livez`, `/readyz`, and `/metrics` retain unified GET/HEAD dispatch, readiness `200/503`, metrics success/`500`, HEAD parity, and typed diagnosis propagation.
- **The live operator now uses `http_v166663`.** The live runtime remains `runtime_v1664`.
- **Checkpoint, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation semantics are unchanged.**

## Parser containment contract

For contained framework parser failures with status `400`, `414`, `431`, or `505`, the server now emits:

- status line `HTTP/1.0 <code> Request Rejected`;
- fixed `request rejected\n` plaintext representation;
- `Server: nvlx`;
- `Content-Type: text/plain; charset=utf-8`;
- `Cache-Control: no-store`;
- exact representation `Content-Length`;
- `Connection: close`.

The numeric status remains meaningful while the reason phrase is deliberately product-owned and invariant. This is a transport fingerprinting/containment change only; accepted request parsing and endpoint logic are unchanged.

## Safety invariants

1. Parser-generated `400/414/431/505` responses use the exact stable `Request Rejected` reason phrase.
2. Parser errors never expose framework-defined reason phrases or parser-supplied request details.
3. Parser failures remain connection-terminal and cannot process a pipelined follow-on request.
4. v1.6.6.6.6.2 cross-version HTTP/1.0 response framing remains intact.
5. v1.6.6.6.6.1 canonical zero-length framing remains unchanged.
6. v1.6.6.6.5 terminal unsupported-method transport remains unchanged.
7. Unified GET/HEAD dispatch, readiness `200/503`, metrics success/`500`, and HEAD parity remain unchanged.
8. Typed-provider symmetry and all v1.6.6.x diagnosis validation remain unchanged.
9. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.3.
