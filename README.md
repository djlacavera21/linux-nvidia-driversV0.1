# nvlx: Linux-NVIDIA-Driver v1.6.6

`nvlx` v1.6.6 moves readiness and Prometheus source diagnosis into the live runtime itself, so the HTTP layer presents typed runtime-owned snapshots instead of reaching into private readiness/checkpoint fields.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6 runtime-owned typed observability diagnosis

- **The runtime now owns readiness diagnosis.** `runtime_v166.Runtime.readiness_diagnosis()` returns a frozen `ReadinessDiagnosis` containing the authoritative readiness result plus API, leadership, Lease freshness, inventory, NVIDIA preflight, checkpoint and termination gates.
- **The runtime now owns metrics source capture.** `metrics_diagnosis()` returns a frozen `MetricsDiagnosis` containing the readiness diagnosis, reconcile totals and all exported checkpoint telemetry.
- **Authoritative readiness is evaluated once per diagnosis.** The existing `ready()` chain remains authoritative and is invoked once before the post-evaluation gate state is captured.
- **Checkpoint diagnosis no longer invokes the checkpoint gate twice.** After authoritative readiness has evaluated `_checkpoint_ready()`, the runtime observes loaded/stale checkpoint state directly for diagnostics instead of calling the gate again.
- **HTTP becomes presentation-oriented for the live runtime.** `/readyz` and `/metrics` prefer runtime-owned diagnosis methods and normalize only their returned typed values; the live path no longer requires direct HTTP knowledge of Lease timestamps, checkpoint internals or runtime stats.
- **Legacy runtime compatibility remains.** Existing HTTP readiness/metrics helpers remain as a fallback for older or custom runtimes that do not implement the v1.6.6 diagnosis contract.
- **Frozen scrape behavior remains intact.** Prometheus rendering still occurs from one immutable capture and never rereads live sources during rendering.
- **Existing transport hardening remains intact.** `Server: nvlx`, no-store caching, byte-accurate UTF-8 framing, deterministic exporter `500` handling and framework-error containment are unchanged.
- **Checkpoint semantics are unchanged.** Per-call commit receipts, canonical digest proof, transport-ambiguity recovery, reconciliation telemetry, rollback fencing, replay floors and Lease-epoch validation retain their established behavior.
- **No RBAC expansion.** This release changes observability ownership, operator runtime wiring, tests, package metadata and documentation only.

## Runtime diagnosis contract

The v1.6.6 live runtime exposes two immutable objects:

1. `ReadinessDiagnosis` — one authoritative readiness decision and the resulting diagnostic gate state;
2. `MetricsDiagnosis` — that readiness diagnosis plus the complete set of exported reconcile/checkpoint source values for one scrape.

The HTTP server consumes those objects without consulting the live runtime again. Older runtimes continue through the historical compatibility path.

## Safety invariants

1. The established runtime `ready()` chain remains the authoritative serving decision.
2. One runtime-owned readiness diagnosis invokes authoritative readiness once.
3. Checkpoint readiness diagnostics do not re-run `_checkpoint_ready()` after the authoritative decision.
4. The v1.6.6 live HTTP path does not require direct access to private Lease/checkpoint fields or live stats after receiving a diagnosis object.
5. Metrics rendering remains isolated from live source rereads.
6. Legacy/custom runtimes without diagnosis methods remain supported through the established fallback.
7. Prometheus metric names, values, HELP/TYPE metadata, ordering and normalization remain unchanged.
8. v1.6.5.9 frozen metrics capture and v1.6.5.8 framework-error containment remain unchanged.
9. All v1.6.5.x checkpoint receipt, reconciliation and persistence semantics remain unchanged.
10. No new Kubernetes mutation path or RBAC permission is introduced.
11. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.
