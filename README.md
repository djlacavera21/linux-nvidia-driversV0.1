# nvlx: Linux-NVIDIA-Driver v1.6.6.1

`nvlx` v1.6.6.1 hardens the runtime-owned typed observability boundary introduced in v1.6.6 by rejecting malformed diagnosis field types instead of accepting Python truthiness or implicit metric coercion.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.1 strict diagnosis contract validation

- **Typed readiness fields are now strict booleans.** `ReadinessDiagnosis` rejects strings, integers and other truthy/falsy values for controller, API, leadership, inventory, preflight, checkpoint and termination gates.
- **Typed metrics fields are now strict integers.** `MetricsDiagnosis` rejects stringified numbers, floats and booleans for exported reconcile/checkpoint telemetry.
- **Nested diagnosis shape is validated.** Built-in `MetricsDiagnosis` requires a real `ReadinessDiagnosis`, preventing malformed nested readiness objects from being accepted by the runtime contract.
- **HTTP independently validates diagnosis-shaped objects.** Custom runtimes that expose `readiness_diagnosis()` or `metrics_diagnosis()` cannot bypass the contract merely by returning objects with similarly named attributes.
- **No permissive truthiness at the typed boundary.** Values such as `"false"` no longer become readiness `True` through Python's `bool()` conversion.
- **Malformed readiness diagnoses fail closed.** `/readyz` returns the established `503 not ready` response and does not fall back to live runtime internals once a runtime has opted into the diagnosis API.
- **Malformed metrics diagnoses remain fault-contained.** `/metrics` returns the established static `500 metrics unavailable` response without reflecting validation details or rereading legacy state.
- **Legacy compatibility remains.** Runtimes that do not expose diagnosis methods continue through the historical readiness/metrics fallback unchanged.
- **Prometheus and HTTP contracts remain unchanged for valid diagnoses.** Metric names, normalization, HELP/TYPE metadata, `Server: nvlx`, no-store caching and byte-accurate framing are preserved.
- **Checkpoint semantics are unchanged.** Receipt proof, canonical digest validation, ambiguity recovery, reconciliation accounting, rollback fencing, replay floors and Lease-epoch behavior are untouched.
- **No RBAC expansion.** This release changes typed validation, HTTP diagnosis adaptation, tests, package metadata and documentation only.

## Validation boundary

The v1.6.6.1 runtime-owned path now treats the diagnosis API as an explicit schema rather than a duck-typed convenience interface:

1. built-in diagnosis dataclasses validate their field types when constructed;
2. the HTTP adapter independently validates diagnosis-shaped objects returned by custom runtimes;
3. a runtime that implements a diagnosis method but returns an invalid object is treated as a broken diagnosis provider, not silently downgraded to the legacy path;
4. readiness therefore fails closed and metrics use the existing bounded exporter failure response.

The historical fallback remains available only to runtimes that do not advertise the diagnosis methods.

## Safety invariants

1. Typed readiness fields must be exact Python `bool` values.
2. Typed exported metric fields must be exact Python `int` values; `bool` is not accepted as an integer metric value.
3. Truthy strings such as `"false"` cannot authorize readiness.
4. Malformed typed readiness diagnoses do not trigger legacy runtime fallback.
5. Malformed typed metrics diagnoses do not trigger live-state rereads and remain inside the static `500 metrics unavailable` boundary.
6. Valid v1.6.6 runtime-owned diagnosis objects preserve the same `/readyz` and `/metrics` output as before.
7. Legacy/custom runtimes without diagnosis methods remain supported through the established fallback.
8. v1.6.6 single authoritative readiness evaluation and no-double-checkpoint evaluation remain unchanged.
9. All v1.6.5.x checkpoint receipt, reconciliation and persistence semantics remain unchanged.
10. No new Kubernetes mutation path or RBAC permission is introduced.
11. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.1.
