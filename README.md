# nvlx: Linux-NVIDIA-Driver v1.6.5.7

`nvlx` v1.6.5.7 minimizes HTTP server fingerprinting by replacing Python's default `BaseHTTP/... Python/...` response header with a stable product-only `Server: nvlx` token across health, readiness, metrics, exporter-failure and unknown-path responses.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.5.7 HTTP server fingerprint minimization

- **Python runtime details are no longer exposed in the Server header.** The HTTP handler now returns `Server: nvlx` instead of the `BaseHTTPRequestHandler` default that includes BaseHTTP and Python version information.
- **The product token is deliberately versionless.** The response header identifies the service without disclosing the installed nvlx or interpreter version.
- **All response classes are covered.** `/livez` `200`, `/readyz` `200` and `503`, `/metrics` `200`, exporter-failure `500`, and unknown-path `404` responses use the same minimized server fingerprint.
- **Health and readiness semantics are unchanged.** Liveness, authoritative readiness evaluation, Lease freshness, NVIDIA preflight and checkpoint readiness behavior are untouched.
- **Prometheus semantics are unchanged.** Successful `/metrics` responses retain schema-closed Prometheus text format 0.0.4 output.
- **Exporter fault containment is unchanged.** Metrics renderer failures still return the static `metrics unavailable` `500` response without leaking exception details or partial exposition.
- **HTTP cache and framing contracts are unchanged.** Live-state text responses retain `Cache-Control: no-store` and byte-accurate UTF-8 `Content-Length`; unknown-path `404` keeps its previous empty-body framing behavior.
- **Checkpoint semantics are unchanged.** Per-call receipts, transport-ambiguity classification, reconciliation accounting, rollback fencing and Lease-epoch rules retain their established behavior.
- **No RBAC expansion.** This release changes only HTTP identification metadata, regression coverage, package metadata and documentation.

## HTTP identification contract

All responses emitted by the nvlx health server now use:

`Server: nvlx`

The header intentionally omits:

1. the Python interpreter version;
2. the `BaseHTTP` implementation version;
3. the installed nvlx package version.

Existing status codes, response bodies, content types, cache policy and payload framing remain unchanged.

## Safety invariants

1. HTTP responses do not expose `Python/` or `BaseHTTP` version fingerprints.
2. The stable server identity is exactly `nvlx` across `200`, `503`, `500` and `404` response classes.
3. v1.6.5.6 exporter fault containment remains unchanged.
4. v1.6.5.5 byte-accurate HTTP framing remains unchanged.
5. v1.6.5.4 no-store live-state caching remains unchanged.
6. v1.6.5.3 metric-schema closure remains unchanged.
7. v1.6.5.2 reconciliation telemetry remains unchanged.
8. v1.6.5.1 transport-ambiguity classification remains unchanged.
9. v1.6.5 per-call checkpoint receipt proof remains unchanged.
10. No new Kubernetes mutation path or RBAC permission is introduced.
11. NVIDIA driver/GPU Operator resources remain read-only in v1.6.5.7.
