# nvlx: Linux-NVIDIA-Driver v1.5

`nvlx` v1.5 turns the Kubernetes-native 1.4 API contract into a **live-operator execution model**. The new layer models watch cursors, relists, optimistic concurrency, bounded workqueue retries, strict field ownership and readiness/liveness decisions without weakening the existing approval-bound runtime.

> [!IMPORTANT]
> The operator owns status and its protective finalizer—not arbitrary `GPUFleet.spec` fields. Driver/GPU Operator changes remain subject to the existing approval, maintenance, preflight, rollout, circuit, health/SLO, PSIRT, rollback and audit gates.

## v1.5 live operator

- **Watch/relist semantics.** `ADDED`, `MODIFIED`, `DELETED` events reconcile; `BOOKMARK` checkpoints the cursor; expired/error watches force a relist.
- **Optimistic status patches.** Controller patch plans require `resourceVersion` and never request force ownership.
- **Bounded workqueue.** Exponential retry is capped and transitions to a dead-letter/operator-review state after the configured attempt budget.
- **Field ownership.** The controller may mutate its status fields and `metadata.finalizers`; arbitrary desired-state spec mutation is rejected.
- **Operator planner.** Watch events map through the 1.4 reconcile contract into status-patch/relist/hold/checkpoint plans.
- **Health model.** Liveness tracks process health; readiness additionally requires Kubernetes API reachability, active leadership and fresh inventory.
- **1.4 retained.** `GPUFleet` CRD, conditions, finalizer, Events API and admission policy remain the Kubernetes API surface.

## Operator commands

```bash
nvlx-k8s operator-plan prod \
  --event-type MODIFIED \
  --resource-version 12 \
  --generation 3 \
  --allowed --runtime-action execute

nvlx-k8s operator-plan prod --event-type ERROR --resource-version 12 --generation 3
nvlx-k8s queue-retry 2
nvlx-k8s ownership-check status.phase metadata.finalizers
nvlx-k8s health --api-reachable --leader --inventory-fresh
```

## Safety invariants

1. Missing `resourceVersion` blocks controller-owned status patching.
2. Expired or failed watches relist instead of continuing from an unsafe cursor.
3. Unsupported watch events fail closed.
4. Controller field ownership excludes arbitrary desired-state spec mutation.
5. Retry loops are bounded; repeated failures require operator review.
6. Standby replicas are live but not ready to mutate fleet state.
7. Stale inventory makes the leader unready for mutation.
8. All v0.1-v1.4 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM and provenance safeguards remain in force.
