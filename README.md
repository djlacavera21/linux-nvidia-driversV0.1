# nvlx: Linux-NVIDIA-Driver v1.6.5.8

`nvlx` v1.6.5.8 contains framework-generated HTTP error responses so unsupported methods no longer receive verbose `BaseHTTPRequestHandler` HTML or reflected parser/method diagnostics.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.5.8 HTTP framework-error containment

- **Framework errors are now deterministic plaintext.** Errors produced by `BaseHTTPRequestHandler` use the fixed body `request rejected\n` instead of generated HTML.
- **Unsupported methods no longer reflect request details.** The response does not echo method names, parser diagnostics, framework strings or exception details.
- **Existing status semantics are preserved.** Unsupported methods retain the framework's `501` status rather than being silently remapped.
- **HEAD remains bodyless.** Framework error responses to `HEAD` advertise the static error payload length but do not write response-body bytes.
- **Error transport is hardened.** Contained framework errors use `text/plain; charset=utf-8`, `Cache-Control: no-store`, exact UTF-8 `Content-Length`, and `Server: nvlx`.
- **Valid GET behavior is unchanged.** `/livez`, `/readyz` and `/metrics` retain their established bodies, status codes, readiness semantics and Prometheus contract.
- **Unknown GET paths are unchanged.** The explicit empty-body `404` path remains outside the framework error helper and keeps its previous framing behavior.
- **Exporter fault containment is unchanged.** Metrics renderer failures still return the static `metrics unavailable` `500` response with no partial exposition or exception leakage.
- **Server fingerprint minimization is unchanged.** Responses continue to omit `BaseHTTP`, Python and nvlx version details from the `Server` header.
- **Checkpoint semantics are unchanged.** Per-call receipts, ambiguity classification, reconciliation accounting, rollback fencing and Lease-epoch rules retain their established behavior.
- **No RBAC expansion.** This release changes only HTTP framework-error handling, tests, package metadata and documentation.

## Framework-error contract

For framework-generated errors such as an unsupported `POST`, `DELETE` or `HEAD` request, nvlx now provides a bounded response surface:

1. the framework-selected HTTP status remains authoritative;
2. `Content-Type: text/plain; charset=utf-8`;
3. `Cache-Control: no-store`;
4. exact UTF-8 `Content-Length`;
5. `Server: nvlx`;
6. fixed body `request rejected\n` for methods that permit a response body;
7. no reflected method text, HTML template, Python version, BaseHTTP version or internal diagnostic detail.

## Safety invariants

1. Framework-generated error bodies are static and do not include request or parser details.
2. Unsupported-method errors do not expose BaseHTTP or Python fingerprints.
3. HEAD framework errors do not write response-body bytes.
4. Existing valid GET endpoint semantics remain unchanged.
5. Existing unknown-path empty `404` behavior remains unchanged.
6. v1.6.5.7 `Server: nvlx` fingerprint minimization remains unchanged.
7. v1.6.5.6 exporter fault containment remains unchanged.
8. v1.6.5.5 byte-accurate HTTP framing remains unchanged.
9. v1.6.5.4 no-store live-state caching remains unchanged.
10. v1.6.5.3 metric-schema closure remains unchanged.
11. v1.6.5.2 reconciliation telemetry remains unchanged.
12. v1.6.5.1 transport-ambiguity classification remains unchanged.
13. v1.6.5 per-call checkpoint receipt proof remains unchanged.
14. No new Kubernetes mutation path or RBAC permission is introduced.
15. NVIDIA driver/GPU Operator resources remain read-only in v1.6.5.8.
