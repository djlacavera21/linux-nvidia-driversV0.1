# nvlx: Linux-NVIDIA-Driver v1.6.5.6

`nvlx` v1.6.5.6 hardens Prometheus exporter failure handling so schema or rendering faults produce a deterministic HTTP 500 response instead of escaping the request handler or emitting a partial scrape.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.5.6 Prometheus exporter fault containment

- **Renderer failures now fail closed over HTTP.** Exceptions raised while constructing `/metrics` are contained and returned as `500` with the static body `metrics unavailable`.
- **No partial exposition is emitted.** The Prometheus body is rendered completely before any response bytes are written, so a failed render cannot leak a truncated HELP/TYPE/sample stream.
- **Internal exception details are not exposed.** The failure body is fixed and does not include schema diagnostics, runtime state, checkpoint data, stack traces or exception text.
- **Failure responses keep live-state transport guarantees.** The `500` response is `text/plain; charset=utf-8`, `Cache-Control: no-store`, and carries byte-accurate `Content-Length`.
- **Successful metrics responses are unchanged.** `/metrics` still returns `200` with `text/plain; version=0.0.4; charset=utf-8`, no-store caching, exact framing and the existing schema-closed exposition.
- **Readiness remains independent.** A metrics renderer failure does not alter `/readyz` status, readiness evaluation, Lease freshness, NVIDIA preflight or checkpoint readiness semantics.
- **Schema closure remains authoritative.** Missing, extra, reordered or invalid metric metadata can still raise internally; v1.6.5.6 only makes that failure externally deterministic and bounded.
- **HTTP framing remains intact.** v1.6.5.5 byte-accurate UTF-8 `Content-Length` behavior is preserved.
- **Checkpoint semantics are unchanged.** Per-call receipts, ambiguity classification, reconciliation accounting, rollback fencing and Lease-epoch rules retain their established behavior.
- **No RBAC expansion.** This release changes metrics error handling, tests, package metadata and documentation only.

## Metrics failure contract

When the exporter succeeds, `/metrics` retains its established Prometheus 0.0.4 response. When the exporter raises an ordinary exception before exposition is available, nvlx now returns:

1. HTTP `500`;
2. `Content-Type: text/plain; charset=utf-8`;
3. `Cache-Control: no-store`;
4. exact UTF-8 `Content-Length`;
5. the fixed body `metrics unavailable\n`.

The underlying exception text is intentionally not copied into the HTTP response.

## Safety invariants

1. Prometheus renderer failures never emit a partial exposition body.
2. Renderer exception details and runtime/checkpoint state are not exposed in the failure response.
3. Metrics failures do not change readiness or liveness behavior.
4. Successful `/metrics` names, values, HELP/TYPE metadata, ordering and normalization remain unchanged.
5. v1.6.5.5 byte-accurate HTTP framing remains unchanged.
6. v1.6.5.4 no-store live-state caching remains unchanged.
7. v1.6.5.3 metric-schema closure remains unchanged.
8. v1.6.5.2 reconciliation telemetry remains unchanged.
9. v1.6.5.1 transport-ambiguity classification remains unchanged.
10. v1.6.5 per-call checkpoint receipt proof remains unchanged.
11. No new Kubernetes mutation path or RBAC permission is introduced.
12. NVIDIA driver/GPU Operator resources remain read-only in v1.6.5.6.
