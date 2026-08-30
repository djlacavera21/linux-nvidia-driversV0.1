# nvlx: Linux-NVIDIA-Driver v1.6.6.6

`nvlx` v1.6.6.6 closes the reciprocal partial typed-provider gap between readiness and Prometheus diagnostics. A runtime that exposes `metrics_diagnosis()` but no dedicated `readiness_diagnosis()` now supplies `/readyz` from the strict typed readiness nested inside its metrics diagnosis instead of falling back to raw `ready()`/stats/private readiness state.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6 metrics-owned readiness propagation

- **Metrics-only typed providers now drive `/readyz`.** When `readiness_diagnosis()` is absent but `metrics_diagnosis()` exists, the live HTTP adapter exposes `metrics_diagnosis().readiness` through the established strict readiness boundary.
- **Dedicated readiness remains preferred.** Runtimes that expose both diagnosis methods continue to use `readiness_diagnosis()` for `/readyz`; the metrics provider is not called for that endpoint.
- **Malformed metrics-owned readiness fails closed.** Invalid or contradictory nested readiness produces the existing `503 not ready` response and never falls back to raw runtime state.
- **Endpoint isolation is preserved.** `/readyz` validates only the nested readiness object. Invalid unrelated metric fields can still make `/metrics` return `500 metrics unavailable` without suppressing a valid readiness result.
- **The full typed metrics path remains frozen.** `/metrics` continues to prefer `metrics_diagnosis()` and validates the existing strict metric type/value domains.
- **Readiness-only providers keep v1.6.6.5 behavior.** Their typed readiness continues to propagate into the legacy metric-value path.
- **Purely legacy runtimes remain unchanged.** Runtimes with neither diagnosis method continue through the historical readiness and metric fallbacks.
- **The live operator now uses `http_v1666`.** The live runtime remains `runtime_v1664`; no runtime policy or persistence layer changes are required.
- **HTTP transport contracts are unchanged.** `Server: nvlx`, no-store caching, exact UTF-8 framing, deterministic framework-error handling and exporter fault containment remain intact.
- **Checkpoint semantics are unchanged.** Receipt proof, canonical digest validation, ambiguity recovery, reconciliation accounting, rollback fencing, replay floors and Lease-epoch behavior are untouched.
- **No RBAC expansion.** This release changes the versioned HTTP adapter, operator wiring, tests, package metadata, CI and documentation only.

## Partial typed-provider symmetry

After v1.6.6.6 the HTTP layer treats either typed diagnosis surface as authoritative for the readiness object it exposes:

`readiness_diagnosis() -> /readyz and readiness portion of legacy /metrics`

`metrics_diagnosis().readiness -> /readyz when no dedicated readiness provider exists`

A dedicated readiness provider always wins when both methods exist.

The readiness endpoint intentionally does not validate unrelated metric counters. This keeps health-serving state independent from exporter-only field failures while retaining strict typed readiness validation.

## Safety invariants

1. Dedicated `readiness_diagnosis()` remains the preferred `/readyz` source.
2. A metrics-only typed provider supplies `/readyz` from `metrics_diagnosis().readiness` and is never silently replaced with raw readiness state.
3. Malformed metrics-owned readiness fails closed to `503 not ready`.
4. `/readyz` does not reject valid readiness solely because unrelated typed metric fields are malformed.
5. Full `metrics_diagnosis()` remains the preferred frozen Prometheus source.
6. Readiness-only typed providers retain v1.6.6.5 metrics propagation behavior.
7. Purely legacy runtimes retain the established compatibility path.
8. v1.6.6.4 effective-leadership validation remains active on typed readiness.
9. v1.6.6.3 logical readiness validation remains unchanged.
10. v1.6.6.2 typed metric nonnegative and relational invariants remain unchanged.
11. v1.6.6.1 strict diagnosis type validation remains unchanged.
12. All v1.6.5.x checkpoint receipt, reconciliation and persistence semantics remain unchanged.
13. No new Kubernetes mutation path or RBAC permission is introduced.
14. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.
