# nvlx: Linux-NVIDIA-Driver v1.6.5.9

`nvlx` v1.6.5.9 closes the remaining Prometheus scrape source-reread gap by capturing readiness gates, reconcile totals and checkpoint telemetry into one frozen `MetricsSnapshot` before rendering begins.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.5.9 frozen metrics snapshot closure

- **One frozen source object drives each successful scrape.** `/metrics` captures a `MetricsSnapshot` containing the established `ReadinessSnapshot`, reconcile totals and every exported checkpoint counter/gauge before invoking the renderer.
- **The renderer no longer receives live runtime or stats objects.** `_render_metrics_snapshot()` accepts only the frozen snapshot, preventing source mutations after capture from changing values inside the same rendered response.
- **Mutable telemetry is read once per capture.** Reconcile totals and checkpoint values are dereferenced during snapshot construction and are not read again by the renderer.
- **Readiness ordering remains authoritative.** The existing readiness snapshot still evaluates runtime readiness first and captures post-evaluation leadership, API, inventory, preflight, checkpoint and termination gates.
- **Capture failures are fault-contained.** Snapshot construction now shares the same deterministic `/metrics` error boundary as rendering, so a failing telemetry accessor returns the static `500 metrics unavailable` response without leaking exception details.
- **Readiness remains independent.** A metrics-only capture failure does not alter `/readyz` behavior.
- **Prometheus exposition remains unchanged.** Metric names, HELP/TYPE metadata, ordering, normalization, content type and successful response body semantics are preserved.
- **HTTP hardening remains intact.** `Server: nvlx`, no-store caching, byte-accurate UTF-8 framing and framework-error containment are unchanged.
- **Checkpoint semantics are unchanged.** Per-call receipts, transport-ambiguity classification, reconciliation accounting, rollback fencing and Lease-epoch rules retain their established behavior.
- **No RBAC expansion.** This release changes metrics capture/render plumbing, tests, package metadata and documentation only.

## Snapshot contract

For one `/metrics` request, nvlx now performs these steps in order:

1. evaluate and capture the established readiness state;
2. capture reconcile totals and exported checkpoint telemetry;
3. freeze those values in `MetricsSnapshot`;
4. render Prometheus text from that object only;
5. emit the completed response.

This is a single-request source-capture boundary, not a global lock over the controller runtime. It prevents renderer-time rereads and mixed values caused by source mutation after capture while preserving the controller's existing concurrency model.

## Safety invariants

1. Prometheus rendering does not dereference live runtime or stats fields after `MetricsSnapshot` has been created.
2. Snapshot values remain immutable for the lifetime of a scrape.
3. Capture-time and render-time exceptions both return the existing static `metrics unavailable` response.
4. `/readyz` remains independent from metrics capture failures.
5. Successful metric names, values, HELP/TYPE metadata, ordering and normalization remain compatible with v1.6.5.8.
6. v1.6.5.8 framework-error containment remains unchanged.
7. v1.6.5.7 server fingerprint minimization remains unchanged.
8. v1.6.5.6 exporter fault containment remains unchanged.
9. v1.6.5.5 byte-accurate framing and v1.6.5.4 no-store caching remain unchanged.
10. v1.6.5.3 metric-schema closure and v1.6.5.x checkpoint semantics remain unchanged.
11. No new Kubernetes mutation path or RBAC permission is introduced.
12. NVIDIA driver/GPU Operator resources remain read-only in v1.6.5.9.
