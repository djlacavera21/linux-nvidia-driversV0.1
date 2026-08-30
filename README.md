# nvlx: Linux-NVIDIA-Driver v1.6.6.6.6.4

`nvlx` v1.6.6.6.6.4 closes the remaining BaseHTTP request-reflection gap by making the live server's default stderr logging bounded and server-owned across Python 3.11, 3.12, and 3.13. Request lines, paths, query strings, malformed parser text, arbitrary method tokens, and terminal control characters are no longer written to the default live HTTP log stream.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.6.4 non-reflective HTTP logging

- **Raw request lines are no longer logged.** Live access logging records only a bounded server-owned status marker such as `nvlx http status=200`.
- **Malformed parser input is not reflected to stderr.** Parser failures retain their numeric status in the safe log marker without including rejected request material.
- **Arbitrary methods are not logged verbatim.** Method rejections preserve their wire-level `405`/`404` behavior while omitting the request method token from logs.
- **Paths and queries are omitted.** Successful, rejected, and unknown-resource requests do not place request targets into the default handler log stream.
- **Control-character behavior is cross-version deterministic.** The server does not depend on Python-version-specific BaseHTTP stderr scrubbing.
- **Log size is bounded by construction.** Long or attacker-controlled request targets cannot amplify default stderr output.
- **Canonical parser wire behavior is unchanged.** Parser `400/414/431/505` responses still use `HTTP/1.0 <code> Request Rejected`, the fixed `request rejected\n` body, exact framing, and `Connection: close`.
- **Explicit method behavior is unchanged.** Exact live resources still use `405 Method Not Allowed` with `Allow: GET, HEAD`; unknown resources retain resource-aware `404` behavior.
- **Live endpoint semantics are unchanged.** `/livez`, `/readyz`, and `/metrics` retain unified GET/HEAD dispatch, readiness `200/503`, metrics success/`500`, HEAD parity, and typed diagnosis propagation.
- **The live operator now uses `http_v166664`.** The live runtime remains `runtime_v1664`.
- **Checkpoint, Prometheus schema, RBAC, readiness policy, and NVIDIA mutation semantics are unchanged.**

## Safe logging contract

The live handler's default stderr surface now emits only server-owned lines:

- request responses: `nvlx http status=<code>` where `<code>` is a validated HTTP status or `-`;
- generic handler errors: `nvlx http error`;
- generic handler messages: `nvlx http event`.

No raw request line, method, target, query string, parser explanation, or client-controlled formatting argument is interpolated into those lines. This is a logging-containment change only; HTTP response semantics and runtime behavior are unchanged.

## Safety invariants

1. Request-controlled text never enters the live handler's default stderr access/error log lines.
2. Parser failures log only their validated numeric status and retain canonical v1.6.6.6.6.3 wire responses.
3. Long request targets cannot grow the default live HTTP log line.
4. Control-character safety is identical on Python 3.11, 3.12, and 3.13.
5. v1.6.6.6.6.3 canonical parser status lines remain unchanged.
6. v1.6.6.6.6.1 canonical zero-length framing and v1.6.6.6.5 terminal method rejection remain unchanged.
7. Unified GET/HEAD dispatch, readiness `200/503`, metrics success/`500`, and HEAD parity remain unchanged.
8. Typed-provider symmetry and all v1.6.6.x diagnosis validation remain unchanged.
9. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.6.4.
