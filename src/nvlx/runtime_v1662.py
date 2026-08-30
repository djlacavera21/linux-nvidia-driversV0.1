"""Typed diagnosis value-domain validation for nvlx 1.6.6.2."""
from __future__ import annotations

from dataclasses import dataclass

from .nvidia_checkpoint_v1651 import LeaseCheckpointStore
from .runtime_v166 import (
    MetricsDiagnosis as MetricsDiagnosisV166,
    ReadinessDiagnosis,
    Runtime as RuntimeV166,
)


_METRIC_FIELDS = (
    "reconcile_total",
    "reconcile_failures",
    "checkpoint_writes",
    "checkpoint_idempotent_acks",
    "checkpoint_reconciled_commits",
    "checkpoint_rollbacks",
    "checkpoint_transaction_mismatches",
    "checkpoint_failures",
    "checkpoint_restore_attempts",
    "checkpoint_restore_successes",
    "checkpoint_sequence",
    "checkpoint_epoch",
)


def _validate_metric_domain(diagnosis) -> None:
    for name in _METRIC_FIELDS:
        if getattr(diagnosis, name) < 0:
            raise ValueError(f"{name} must be nonnegative")

    if diagnosis.reconcile_failures > diagnosis.reconcile_total:
        raise ValueError("reconcile_failures cannot exceed reconcile_total")
    if diagnosis.checkpoint_restore_successes > diagnosis.checkpoint_restore_attempts:
        raise ValueError(
            "checkpoint_restore_successes cannot exceed checkpoint_restore_attempts"
        )
    if diagnosis.checkpoint_reconciled_commits > (
        diagnosis.checkpoint_writes + diagnosis.checkpoint_idempotent_acks
    ):
        raise ValueError(
            "checkpoint_reconciled_commits cannot exceed accepted checkpoint commits"
        )


@dataclass(frozen=True)
class MetricsDiagnosis(MetricsDiagnosisV166):
    """Strict typed metrics diagnosis with nonnegative and relational invariants."""

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_metric_domain(self)


class Runtime(RuntimeV166):
    """Produce only domain-valid runtime-owned metrics diagnoses."""

    def metrics_diagnosis(self) -> MetricsDiagnosis:
        diagnosis = super().metrics_diagnosis()
        return MetricsDiagnosis(
            readiness=diagnosis.readiness,
            reconcile_total=diagnosis.reconcile_total,
            reconcile_failures=diagnosis.reconcile_failures,
            checkpoint_writes=diagnosis.checkpoint_writes,
            checkpoint_idempotent_acks=diagnosis.checkpoint_idempotent_acks,
            checkpoint_reconciled_commits=diagnosis.checkpoint_reconciled_commits,
            checkpoint_rollbacks=diagnosis.checkpoint_rollbacks,
            checkpoint_transaction_mismatches=diagnosis.checkpoint_transaction_mismatches,
            checkpoint_failures=diagnosis.checkpoint_failures,
            checkpoint_restore_attempts=diagnosis.checkpoint_restore_attempts,
            checkpoint_restore_successes=diagnosis.checkpoint_restore_successes,
            checkpoint_sequence=diagnosis.checkpoint_sequence,
            checkpoint_epoch=diagnosis.checkpoint_epoch,
        )


__all__ = [
    "Runtime",
    "LeaseCheckpointStore",
    "ReadinessDiagnosis",
    "MetricsDiagnosis",
]
