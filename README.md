# nvlx: Linux-NVIDIA-Driver v1.6.5.5

`nvlx` v1.6.5.5 hardens HTTP response framing for live health and Prometheus endpoints by declaring the exact UTF-8 payload byte length while preserving all existing status, body, cache, readiness and checkpoint semantics.

> [!IMPORTANT]
> NVIDIA driver/GPU Operator resources remain read-only. The operator still mutates only nvlx-owned GPUFleet status/finalizers plus its existing Lease and Events.

## v1.6.5.5 HTTP response framing hardening

- **Live responses now declare exact payload length.** `/livez`, `/readyz` and `/metrics` return `Content-Length` computed from the already-encoded UTF-8 response bytes.
- **Byte length, not character count, is authoritative.** Multibyte UTF-8 payloads are framed from `len(payload)` after encoding, preventing character-count drift.
- **Both readiness outcomes are covered.** Ready `200` and not-ready `503` responses carry correct framing metadata.
- **Prometheus framing is explicit.** `/metrics` retains `text/plain; version=0.0.4; charset=utf-8`, `Cache-Control: no-store`, and now declares the exact exposition byte count.
- **Health framing is explicit.** `/livez` and `/readyz` retain `text/plain; charset=utf-8` and `Cache-Control: no-store` with exact payload lengths.
- **Bodies and status codes are unchanged.** Liveness, readiness and metrics response bytes retain their previous meanings.
- **Unknown-path behavior is unchanged.** Existing `404` handling remains outside the live-state text response helper and does not acquire the new framing metadata.
- **Readiness semantics are unchanged.** Atomic post-evaluation readiness snapshots, Lease freshness diagnostics and checkpoint readiness behavior are untouched.
- **Prometheus schema closure is unchanged.** The immutable `MetricSpec` registry and fail-fast sample completeness checks from v1.6.5.3 remain intact.
- **Checkpoint semantics are unchanged.** Per-call receipts, ambiguity classification, reconciliation accounting, rollback fencing and Lease-epoch rules retain their established behavior.
- **No RBAC expansion.** This release changes HTTP response framing, tests, package metadata and documentation only.

## HTTP contract

The live-state endpoints now expose these framing guarantees:

1. `/livez`: `200`, UTF-8 text, `Cache-Control: no-store`, exact `Content-Length`;
2. `/readyz`: `200` or `503`, UTF-8 text, `Cache-Control: no-store`, exact `Content-Length`;
3. `/metrics`: `200`, Prometheus text format 0.0.4, UTF-8, `Cache-Control: no-store`, exact `Content-Length`.

`Content-Length` is derived after UTF-8 encoding, so the declared size always matches the bytes written to the socket.

## Safety invariants

1. Declared `Content-Length` equals the exact UTF-8 payload bytes written for each live-state response.
2. Ready and not-ready readiness responses use the same framing and no-store policy.
3. Existing endpoint bodies, status codes, content types and cache headers remain unchanged from v1.6.5.4.
4. Unknown-path `404` behavior remains unchanged.
5. Prometheus metric names, values, HELP/TYPE metadata, ordering and normalization are unchanged.
6. v1.6.5.3 metric-schema closure remains unchanged.
7. v1.6.5.2 reconciliation telemetry remains unchanged.
8. v1.6.5.1 transport-ambiguity classification remains unchanged.
9. v1.6.5 per-call checkpoint receipt proof remains unchanged.
10. No new Kubernetes mutation path or RBAC permission is introduced.
11. NVIDIA driver/GPU Operator resources remain read-only in v1.6.5.5.
