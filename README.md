# nvlx: Linux-NVIDIA-Driver v1.6.5.3

`nvlx` v1.6.5.3 closes Prometheus exporter schema drift by replacing separately maintained HELP and TYPE metadata with one immutable metric schema and a fail-fast sample completeness check.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.5.3 Prometheus schema-closure hardening

- **One immutable schema now owns metric metadata.** Every exported series is defined by a single `MetricSpec` containing its Prometheus type and static HELP description.
- **HELP and TYPE cannot drift independently.** The historical counter set and HELP mapping remain available as derived compatibility views rather than separate sources of truth.
- **Rendered samples must exactly match the schema.** Missing, extra or reordered metric samples now fail closed before exposition rather than emitting a partially valid or silently inconsistent scrape.
- **Output order is schema-owned and deterministic.** The same established metric ordering is preserved, including the v1.6.5.2 reconciliation counter.
- **Metric metadata is validated at definition time.** Unsupported Prometheus types, empty HELP text and multiline HELP text are rejected.
- **Existing names, values and normalization behavior are unchanged.** All previous PromQL series names and integer normalization semantics remain compatible.
- **Checkpoint telemetry remains unchanged.** `nvlx_nvidia_checkpoint_reconciled_commits_total` remains a counter and retains its v1.6.5.2 acceptance semantics.
- **No runtime persistence change.** Per-call commit receipts, ambiguity classification, canonical digest verification, rollback fencing and Lease-epoch handling are unchanged.
- **No readiness or HTTP contract change.** Closed readiness snapshots and Prometheus UTF-8 text exposition remain intact.
- **No RBAC expansion.** This release changes exporter schema validation, tests, package metadata and documentation only.

## Schema contract

For every emitted sample, the exporter now requires exactly one immutable schema entry with:

1. a valid `counter` or `gauge` type;
2. one non-empty single-line HELP description;
3. a unique position in the deterministic exposition order.

Before rendering, the sample-name sequence must exactly equal the schema-name sequence. Any missing sample, unregistered sample or ordering drift raises an internal error instead of producing ambiguous Prometheus metadata.

## Safety invariants

1. Every exported metric remains represented exactly once in the schema.
2. HELP and TYPE metadata are generated exclusively from the same `MetricSpec` entry.
3. Missing, extra and reordered samples fail closed before exposition.
4. Existing metric names, numeric values, normalization and exposition order remain unchanged from v1.6.5.2.
5. `nvlx_nvidia_checkpoint_reconciled_commits_total` remains a Prometheus counter with unchanged meaning.
6. v1.6.5.2 reconciliation accounting remains unchanged.
7. v1.6.5.1 transport-ambiguity classification remains unchanged.
8. v1.6.5 per-call checkpoint receipt proof remains unchanged.
9. No new Kubernetes mutation path or RBAC permission is introduced.
10. NVIDIA driver/GPU Operator resources remain read-only in v1.6.5.3.
