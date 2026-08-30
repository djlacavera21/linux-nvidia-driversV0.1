# nvlx: Linux-NVIDIA-Driver v1.5.9

`nvlx` v1.5.9 is a ninth stabilization patch for the live Kubernetes operator. It adds sequenced fencing checkpoints on top of the existing monotonic epoch and integrity controls so an older but otherwise valid persisted snapshot cannot silently re-enter the controller mutation path.

> [!IMPORTANT]
> Sequence numbers are an additional safety signal, not standalone authority. A controller still requires integrity-valid persisted state, live Lease holder/epoch/resourceVersion/freshness validation, monotonic fencing checks, and an acceptable sequence checkpoint before controller-owned mutation is allowed.

## v1.5.9 fixes

- **Sequenced fencing checkpoints.** Initial persisted authority starts at sequence `1`; subsequent authority changes must advance the sequence by exactly one.
- **Replay detection.** A changed fencing token presented at the already-persisted sequence is rejected as `reject-sequence-replay`.
- **Sequence rollback protection.** A candidate sequence lower than persisted state is rejected as `reject-sequence-rollback`.
- **Gap protection.** Sequence jumps larger than one are rejected as `reject-sequence-gap` rather than being silently accepted.
- **Redundant-advance protection.** An unchanged fencing token cannot advance the sequence, preventing checkpoint drift unrelated to authority changes.
- **Reacquisition preservation.** Reacquired leadership still has to satisfy v1.5.8's newer-epoch requirement before its next sequence can persist.
- **Trusted-floor check.** Startup can compare a persisted sequence against an independently retained minimum and surface `replay-detected` when the disk snapshot predates that checkpoint.
- **1.5.8 retained.** Monotonic epochs, same-epoch holder collision rejection, integrity envelopes, rollback-aware recovery, live Lease revalidation, renewal-race fencing and stale-leader blocking remain active.

## Safety invariants

1. Fencing checkpoint sequences never move backward.
2. A token change cannot occur without exactly one sequence advance.
3. A sequence cannot advance when the fencing token is unchanged.
4. Sequence gaps are fail-closed rather than inferred through.
5. A persisted checkpoint older than an independently trusted minimum is treated as replayed state.
6. All v0.1-v1.5.8 approval, rollback, Secure Boot, DRA, fabric, health/SLO, PSIRT, quarantine, audit, SBOM and provenance safeguards remain in force.
