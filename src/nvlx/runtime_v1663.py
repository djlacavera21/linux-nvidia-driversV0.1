"""Typed readiness logical-domain validation for nvlx 1.6.6.3."""
from __future__ import annotations

from dataclasses import dataclass

from .nvidia_checkpoint_v1651 import LeaseCheckpointStore
from .runtime_v166 import ReadinessDiagnosis as ReadinessDiagnosisV166
from .runtime_v1662 import MetricsDiagnosis, Runtime as RuntimeV1662


def _serving_gates_pass(diagnosis) -> bool:
    return bool(
        diagnosis.api_reachable
        and diagnosis.leader
        and diagnosis.leadership_fresh
        and diagnosis.inventory_fresh
        and diagnosis.nvidia_preflight_ready
        and diagnosis.checkpoint_ready
        and not diagnosis.terminating
    )


def _validate_readiness_domain(diagnosis) -> None:
    if diagnosis.leadership_fresh and (
        not diagnosis.api_reachable
        or not diagnosis.leader
        or diagnosis.terminating
    ):
        raise ValueError(
            "leadership_fresh requires API reachability, effective leadership and non-termination"
        )
    if diagnosis.controller_ready and not _serving_gates_pass(diagnosis):
        raise ValueError(
            "controller_ready requires every exported readiness gate to pass"
        )


@dataclass(frozen=True)
class ReadinessDiagnosis(ReadinessDiagnosisV166):
    """Strict typed readiness diagnosis with logical serving invariants."""

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_readiness_domain(self)


class Runtime(RuntimeV1662):
    """Produce logically consistent runtime-owned readiness diagnoses."""

    def readiness_diagnosis(self) -> ReadinessDiagnosis:
        diagnosis = super().readiness_diagnosis()
        controller_ready = bool(
            diagnosis.controller_ready and _serving_gates_pass(diagnosis)
        )
        return ReadinessDiagnosis(
            controller_ready=controller_ready,
            api_reachable=diagnosis.api_reachable,
            leader=diagnosis.leader,
            leadership_fresh=diagnosis.leadership_fresh,
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
