"""Monotonic persistence guard for leadership fencing state."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .leadership_v155 import FenceToken

@dataclass(frozen=True)
class PersistDecision:
    allowed: bool
    action: str
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)

def assess(previous: FenceToken | None, candidate: FenceToken, *, reacquired: bool=False) -> PersistDecision:
    if candidate.epoch < 0:
        raise ValueError("candidate epoch must be >= 0")
    if not candidate.holder or not candidate.lease_resource_version:
        raise ValueError("candidate token fields must be non-empty")
    if previous is None:
        return PersistDecision(True,"persist-initial",())
    if candidate.epoch < previous.epoch:
        return PersistDecision(False,"reject-rollback",("candidate leadership epoch is older than persisted epoch",))
    if candidate.epoch == previous.epoch and candidate.holder != previous.holder:
        return PersistDecision(False,"reject-epoch-collision",("lease holder changed without fencing epoch advance",))
    if candidate == previous:
        return PersistDecision(False,"noop",("candidate fencing token already persisted",))
    if reacquired and candidate.epoch <= previous.epoch:
        return PersistDecision(False,"reject-stale-reacquire",("reacquired authority must advance the fencing epoch",))
    if candidate.epoch > previous.epoch:
        return PersistDecision(True,"persist-new-epoch",())
    return PersistDecision(True,"persist-renewal",())
