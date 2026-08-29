"""Fail-closed startup recovery for persisted leadership fencing state."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .leadership_v155 import FenceToken, validate

@dataclass(frozen=True)
class RecoveryDecision:
    allowed: bool
    action: str
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)

def assess(token: FenceToken | None, *, current_holder: str, current_epoch: int, current_resource_version: str, lease_fresh: bool=True) -> RecoveryDecision:
    if current_epoch < 0: raise ValueError("current_epoch must be >= 0")
    if token is None:
        return RecoveryDecision(False,"reacquire",("no persisted fencing token",))
    if current_epoch < token.epoch:
        return RecoveryDecision(False,"rollback-detected",("live leadership epoch is older than persisted epoch",))
    if current_epoch > token.epoch:
        return RecoveryDecision(False,"reacquire",("persisted fencing token is from an older leadership epoch",))
    decision=validate(token,current_holder=current_holder,current_epoch=current_epoch,current_resource_version=current_resource_version,lease_fresh=lease_fresh)
    if not decision.allowed:
        return RecoveryDecision(False,"revalidate",decision.reasons)
    return RecoveryDecision(True,"restore",())
