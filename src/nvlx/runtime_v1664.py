"""Effective-leadership diagnosis closure for nvlx 1.6.6.4."""
from __future__ import annotations

from dataclasses import dataclass

from .nvidia_checkpoint_v1651 import LeaseCheckpointStore
from .runtime_v1663 import (
    MetricsDiagnosis,
    ReadinessDiagnosis as ReadinessDiagnosisV1663,
    Runtime as RuntimeV1663,
)


def _validate_effective_leader_domain(diagnosis) -> None:
    if diagnosis.leader and (
        not diagnosis.api_reachable or diagnosis.terminating
    ):
        raise ValueError(
            "effective leadership requires API reachability and non-termination"
        )


@dataclass(frozen=True)
class ReadinessDiagnosis(ReadinessDiagnosisV1663):
    """Typed readiness diagnosis with effective-leader consistency."""

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_effective_leader_domain(self)


class Runtime(RuntimeV1663):
    """Normalize torn effective-leadership observations toward not-ready."""

    def readiness_diagnosis(self) -> ReadinessDiagnosis:
        diagnosis = super().readiness_diagnosis()
        effective_leader = bool(
            diagnosis.leader
            and diagnosis.api_reachable
            and not diagnosis.terminating
        )
        leadership_fresh = bool(
            diagnosis.leadership_fresh and effective_leader
        )
        controller_ready = bool(
            diagnosis.controller_ready and effective_leader
        )
        return ReadinessDiagnosis(
            controller_ready=controller_ready,
            api_reachable=diagnosis.api_reachable,
            leader=effective_leader,
            leadership_fresh=leadership_fresh,
            inventory_fresh=diagnosis.inventory_fresh,
            nvidia_preflight_ready=diagnosis.nvidia_preflight_ready,
            checkpoint_ready=diagnosis.checkpoint_ready,
            terminating=diagnosis.terminating,
        )


__all__ = [
    "Runtime",
    "LeaseCheckpointStore",
    "ReadinessDiagnosis",
    "MetricsDiagnosis",
]
