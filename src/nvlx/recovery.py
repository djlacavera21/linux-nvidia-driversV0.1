"""Recovery decision contract for failed production executions."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class RecoveryPlan:
    action: str
    automatic: bool
    reasons: tuple[str, ...]
    def to_dict(self): return asdict(self)

def plan(*, rollback_available: bool, security_failure: bool, state_uncertain: bool, failure_count: int) -> RecoveryPlan:
    if security_failure:
        return RecoveryPlan("quarantine",False,("security failure requires operator review",))
    if state_uncertain:
        return RecoveryPlan("hold",False,("observed state is uncertain",))
    if rollback_available and failure_count <= 1:
        return RecoveryPlan("rollback",True,("bounded first failure with verified rollback",))
    if rollback_available:
        return RecoveryPlan("rollback",False,("repeated failure requires approval before rollback",))
    return RecoveryPlan("hold",False,("verified rollback unavailable",))
