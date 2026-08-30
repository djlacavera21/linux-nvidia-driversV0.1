"""Runtime-owned typed observability diagnosis for nvlx 1.6.6."""
from __future__ import annotations

from dataclasses import dataclass
import time

from .nvidia_checkpoint_v1651 import LeaseCheckpointStore
from .runtime_v1652 import Runtime as RuntimeV1652


def _require_bool(name: str, value) -> None:
    if type(value) is not bool:
        raise TypeError(f"{name} must be bool")


def _require_int(name: str, value) -> None:
    if type(value) is not int:
        raise TypeError(f"{name} must be int")


@dataclass(frozen=True)
class ReadinessDiagnosis:
    """One authoritative readiness decision plus its post-evaluation gate state."""

    controller_ready: bool
    api_reachable: bool
    leader: bool
    leadership_fresh: bool
    inventory_fresh: bool
    nvidia_preflight_ready: bool
    checkpoint_ready: bool
    terminating: bool

    def __post_init__(self) -> None:
        for name in (
            "controller_ready",
            "api_reachable",
            "leader",
            "leadership_fresh",
            "inventory_fresh",
            "nvidia_preflight_ready",
            "checkpoint_ready",
            "terminating",
        ):
            _require_bool(name, getattr(self, name))


@dataclass(frozen=True)
class MetricsDiagnosis:
    """One frozen set of runtime-owned source values for Prometheus rendering."""

    readiness: ReadinessDiagnosis
    reconcile_total: int
    reconcile_failures: int
    checkpoint_writes: int
    checkpoint_idempotent_acks: int
    checkpoint_reconciled_commits: int
    checkpoint_rollbacks: int
    checkpoint_transaction_mismatches: int
    checkpoint_failures: int
    checkpoint_restore_attempts: int
    checkpoint_restore_successes: int
    checkpoint_sequence: int
    checkpoint_epoch: int

    def __post_init__(self) -> None:
        if not isinstance(self.readiness, ReadinessDiagnosis):
            raise TypeError("readiness must be ReadinessDiagnosis")
        for name in (
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
        ):
            _require_int(name, getattr(self, name))


class Runtime(RuntimeV1652):
    """Own readiness and metrics diagnosis instead of leaking runtime internals to HTTP."""

    def _observe_leadership_fresh(
        self,
        *,
        api_reachable: bool,
        leader: bool,
        terminating: bool,
    ) -> bool:
        if not api_reachable:
            return False
        if terminating or not leader:
            return False

        verified = getattr(self, "_leader_verified_monotonic", None)
        window = getattr(self, "leader_fresh_seconds", None)
        if verified is None or window is None:
            return leader

        try:
            verified = float(verified)
            window = float(window)
            age = time.monotonic() - verified
        except (TypeError, ValueError, OverflowError):
            return False
        return bool(verified > 0 and window > 0 and 0 <= age <= window)

    def _observe_checkpoint_ready(self) -> bool:
        """Observe checkpoint readiness without invoking the gate a second time."""
        store = getattr(self, "nvidia_checkpoint_store", None)
        if store is None:
            return True
        return bool(
            getattr(self, "nvidia_checkpoint_loaded", False)
            and not getattr(self, "nvidia_checkpoint_epoch_stale", True)
        )

    def readiness_diagnosis(self) -> ReadinessDiagnosis:
        """Evaluate authoritative readiness once, then capture the resulting gate state."""
        try:
            controller_ready = bool(self.ready())
        except Exception:
            controller_ready = False

        s = self.stats
        api_reachable = bool(getattr(s, "api_reachable", False))
        leader = bool(getattr(s, "leader", False))
        inventory_fresh = bool(getattr(s, "inventory_fresh", False))
        terminating = bool(getattr(s, "terminating", False))
        nvidia_preflight_ready = bool(getattr(self, "nvidia_preflight_ok", True))
        leadership_fresh = self._observe_leadership_fresh(
            api_reachable=api_reachable,
            leader=leader,
            terminating=terminating,
        )
        checkpoint_ready = self._observe_checkpoint_ready()

        return ReadinessDiagnosis(
            controller_ready=controller_ready,
            api_reachable=api_reachable,
            leader=leader,
            leadership_fresh=leadership_fresh,
            inventory_fresh=inventory_fresh,
            nvidia_preflight_ready=nvidia_preflight_ready,
            checkpoint_ready=checkpoint_ready,
            terminating=terminating,
        )

    def metrics_diagnosis(self) -> MetricsDiagnosis:
        """Capture every exported mutable source under runtime ownership."""
        readiness = self.readiness_diagnosis()
        s = self.stats
        return MetricsDiagnosis(
            readiness=readiness,
            reconcile_total=s.reconcile_total,
            reconcile_failures=s.reconcile_failures,
            checkpoint_writes=getattr(self, "nvidia_checkpoint_writes", 0),
            checkpoint_idempotent_acks=getattr(
                self, "nvidia_checkpoint_idempotent_acks", 0
            ),
            checkpoint_reconciled_commits=getattr(
                self, "nvidia_checkpoint_reconciled_commits", 0
            ),
            checkpoint_rollbacks=getattr(self, "nvidia_checkpoint_rollbacks", 0),
            checkpoint_transaction_mismatches=getattr(
                self, "nvidia_checkpoint_transaction_mismatches", 0
            ),
            checkpoint_failures=getattr(self, "nvidia_checkpoint_failures", 0),
            checkpoint_restore_attempts=getattr(
                self, "nvidia_checkpoint_restore_attempts", 0
            ),
            checkpoint_restore_successes=getattr(
                self, "nvidia_checkpoint_restore_successes", 0
            ),
            checkpoint_sequence=getattr(self, "nvidia_checkpoint_sequence", 0),
            checkpoint_epoch=getattr(self, "nvidia_checkpoint_epoch", 0),
        )


__all__ = [
    "Runtime",
    "LeaseCheckpointStore",
    "ReadinessDiagnosis",
    "MetricsDiagnosis",
]
