# nvlx: Linux-NVIDIA-Driver v1.6.5.4

`nvlx` v1.6.5.4 hardens the live HTTP health and telemetry surface so liveness, readiness and Prometheus responses cannot be reused from an intermediary cache while preserving all established status, body and readiness semantics.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.5.4 live-state HTTP cache hardening

- **Live state is explicitly non-cacheable.** `/livez`, `/readyz` and `/metrics` now return `Cache-Control: no-store` on their normal response paths.
- **Both readiness outcomes are covered.** Ready `200` and not-ready `503` responses carry the same no-store contract so stale readiness cannot be replayed by an intermediary.
- **Health content types are explicit.** `/livez` and `/readyz` now return `text/plain; charset=utf-8` and encode their bodies as UTF-8.
- **Prometheus content type is preserved.** `/metrics` remains `text/plain; version=0.0.4; charset=utf-8` while also becoming non-cacheable.
- **Bodies and status codes are unchanged.** `/livez` remains `200` with `ok`, `/readyz` remains `200 ready` or `503 not ready`, and `/metrics` remains `200` with the established exposition body.
- **Unknown-path behavior is unchanged.** Existing `404` behavior remains outside the live-state response helper.
- **Readiness evaluation is unchanged.** Atomic post-evaluation readiness snapshots, Lease freshness diagnostics and checkpoint readiness semantics are untouched.
- **Prometheus schema closure is unchanged.** The immutable `MetricSpec` registry and fail-fast sample completeness checks from v1.6.5.3 remain intact.
- **Checkpoint recovery telemetry is unchanged.** Reconciled commit accounting and all v1.6.5.x receipt/reconciliation rules retain their previous meanings.
- **No RBAC expansion.** This release changes HTTP response metadata, tests, package metadata and documentation only.

## HTTP contract

The live-state endpoints now expose these cache/content-type guarantees:

1. `/livez`: `200`, `text/plain; charset=utf-8`, `Cache-Control: no-store`;
2. `/readyz`: `200` or `503`, `text/plain; charset=utf-8`, `Cache-Control: no-store`;
3. `/metrics`: `200`, `text/plain; version=0.0.4; charset=utf-8`, `Cache-Control: no-store`.

No response-body or readiness-policy change is required for existing Kubernetes probes or Prometheus scrapers.

## Safety invariants

1. Live liveness, readiness and metrics responses are explicitly non-cacheable.
2. Ready and not-ready responses use the same cache-prevention policy.
3. Health bodies are explicitly UTF-8 text without changing their existing bytes or status codes.
4. Prometheus exposition version, charset, metric names, values, HELP/TYPE metadata and ordering are unchanged.
5. v1.6.5.3 metric-schema closure remains unchanged.
6. v1.6.5.2 reconciliation telemetry remains unchanged.
7. v1.6.5.1 transport-ambiguity classification remains unchanged.
8. v1.6.5 per-call checkpoint receipt proof remains unchanged.
9. No new Kubernetes mutation path or RBAC permission is introduced.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.5.4.
