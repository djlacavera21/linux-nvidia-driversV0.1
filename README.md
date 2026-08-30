# nvlx: Linux-NVIDIA-Driver v1.6.6.6.1

`nvlx` v1.6.6.6.1 adds HTTP `HEAD` parity for the live observability surface while preserving the v1.6.6.6 typed-provider symmetry and all existing runtime/checkpoint safety contracts.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.6.6.1 HEAD parity

- **`HEAD /livez` now mirrors `GET /livez`.** It returns the same `200`, content type, `Cache-Control: no-store`, `Server: nvlx`, and representation `Content-Length`, but never emits the `ok\n` body.
- **`HEAD /readyz` now mirrors readiness GET semantics.** Ready `200` and not-ready `503` statuses, headers, and representation lengths match GET while the response body remains empty.
- **`HEAD /metrics` evaluates the same frozen metrics path.** Successful responses preserve Prometheus text-format metadata and the GET representation length without returning exposition bytes.
- **Metrics failure containment is preserved for HEAD.** Capture/render failures return the same deterministic `500` metadata and `Content-Length` for `metrics unavailable\n`, with no body and no exception leakage.
- **Unknown HEAD paths mirror GET's empty `404`.** They remain outside the live-state no-store/content-length helper contract.
- **Historical GET behavior is unchanged.** The new behavior is layered in `http_v16661`; prior HTTP modules remain immutable.
- **Typed-provider symmetry is unchanged.** Metrics-only providers still supply readiness through `metrics_diagnosis().readiness` when no dedicated readiness provider exists, and dedicated readiness remains preferred when both are present.
- **The live operator now uses `http_v16661`.** The live runtime remains `runtime_v1664`.
- **Checkpoint semantics are unchanged.** Receipt proof, canonical digest validation, ambiguity recovery, reconciliation accounting, rollback fencing, replay floors, and Lease-epoch behavior are untouched.
- **No RBAC expansion.** No new Kubernetes mutation path is introduced.

## HEAD contract

For `/livez`, `/readyz`, and `/metrics`, HEAD returns the same representation metadata that GET would return for the same state:

- identical HTTP status;
- identical `Content-Type`;
- identical `Cache-Control`;
- identical stable `Server: nvlx` token;
- `Content-Length` equal to the corresponding GET payload byte length;
- zero response-body bytes.

The metrics endpoint still performs capture/render validation for HEAD so a failed exporter cannot be presented as a successful representation.

## Safety invariants

1. HEAD never writes a live-state response body.
2. HEAD status and representation headers match GET for successful and failed live-state endpoints.
3. Prometheus HEAD responses preserve `text/plain; version=0.0.4; charset=utf-8`.
4. Metrics HEAD failures remain deterministic and non-cacheable.
5. Unknown HEAD paths use the existing empty `404` contract.
6. v1.6.6.6 partial typed-provider symmetry remains unchanged.
7. v1.6.6.5 typed readiness propagation into metrics fallback remains unchanged.
8. v1.6.6.4 effective-leadership validation remains active.
9. v1.6.6.3 logical readiness validation remains unchanged.
10. v1.6.6.2 typed metric value-domain validation remains unchanged.
11. v1.6.6.1 strict diagnosis typing remains unchanged.
12. All v1.6.5.x checkpoint receipt, reconciliation, and persistence semantics remain unchanged.
13. NVIDIA driver/GPU Operator resources remain read-only in v1.6.6.6.1.
