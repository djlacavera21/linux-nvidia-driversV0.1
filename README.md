# nvlx: Linux-NVIDIA-Driver v1.6.6.5

`nvlx` v1.6.6.5 closes the partial typed-provider gap between readiness and Prometheus rendering. If a runtime opts into `readiness_diagnosis()` but still uses legacy metric counters, `/metrics` now reuses that strict typed readiness result instead of rereading raw `ready()`/stats/private readiness state.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.5 typed-readiness propagation into metrics fallback

- **Typed readiness now propagates into the legacy metric-value path.** A runtime with `readiness_diagnosis()` but no `metrics_diagnosis()` no longer gets its readiness portion rebuilt from raw runtime state during `/metrics`.
- **No silent typed-to-legacy readiness fallback.** The metrics path strictly validates the supplied readiness diagnosis; malformed typed readiness enters the established static `500 metrics unavailable` containment path.
- **Full typed metrics remain preferred.** Runtimes with `metrics_diagnosis()` continue to use the existing frozen typed metrics snapshot and do not perform a second readiness-diagnosis call.
- **Legacy metric-value compatibility is preserved.** Runtimes without `metrics_diagnosis()` still use historical metric counter/gauge collection and normalization; the change affects only how readiness is sourced when a typed readiness provider exists.
- **Legacy runtimes remain unchanged.** Runtimes with neither typed diagnosis method continue through the historical readiness and metrics fallback.
- **The v1.6.6.4 effective-leadership guard remains active.** Partial typed readiness consumed by `/metrics` still passes through the live `http_v1664` guard, so impossible `leader=True` combinations remain fail-closed.
- **No duplicate readiness evaluation on the full typed path.** A valid `metrics_diagnosis()` remains sufficient for one scrape.
- **HTTP transport contracts are unchanged.** `Server: nvlx`, no-store caching, exact UTF-8 framing, deterministic framework-error handling and exporter fault containment remain intact.
- **Checkpoint semantics are unchanged.** Receipt proof, canonical digest validation, ambiguity recovery, reconciliation accounting, rollback fencing, replay floors and Lease-epoch behavior are untouched.
- **No RBAC expansion.** This release changes the shared HTTP metrics fallback, tests, package metadata, CI and documentation only.

## Partial typed-provider contract

For `/readyz`, a runtime that implements `readiness_diagnosis()` already opts into the strict typed readiness boundary.

v1.6.6.5 makes `/metrics` honor the same choice when `metrics_diagnosis()` is absent:

`typed readiness provider + legacy metric values -> typed readiness + legacy metric values`

It no longer becomes:

`typed readiness provider + legacy metric values -> raw readiness reread + legacy metric values`

If the typed readiness diagnosis is malformed, `/metrics` fails closed rather than rebuilding readiness from mutable runtime internals.

## Safety invariants

1. Full typed `metrics_diagnosis()` remains the preferred frozen Prometheus source.
2. A readiness-only typed provider is reused by `/metrics` and is never silently replaced with raw readiness state.
3. Malformed readiness-only typed diagnoses cannot reach Prometheus rendering.
4. The legacy metric-value path retains historical normalization for runtimes without typed metrics diagnoses.
5. Runtimes with no diagnosis methods retain the established compatibility path.
6. v1.6.6.4 effective-leadership validation remains active on typed readiness.
7. v1.6.6.3 logical readiness validation remains unchanged.
8. v1.6.6.2 typed metric nonnegative and relational invariants remain unchanged.
9. v1.6.6.1 strict diagnosis type validation remains unchanged.
10. All v1.6.5.x checkpoint receipt, reconciliation and persistence semantics remain unchanged.
11. No new Kubernetes mutation path or RBAC permission is introduced.
12. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.5.
