"""Leadership fencing for mutation safety during Kubernetes Lease handoff."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class FenceToken:
    holder: str
    epoch: int
    lease_resource_version: str
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class FenceDecision:
    allowed: bool
    action: str
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)

def validate(token: FenceToken, *, current_holder: str, current_epoch: int, current_resource_version: str, lease_fresh: bool=True) -> FenceDecision:
    if token.epoch < 0 or current_epoch < 0:
        raise ValueError("fencing epochs must be >= 0")
    reasons=[]
    if not lease_fresh: reasons.append("leader lease stale")
    if token.holder != current_holder: reasons.append("lease holder changed")
    if token.epoch != current_epoch: reasons.append("leadership epoch changed")
    if token.lease_resource_version != current_resource_version: reasons.append("lease resourceVersion changed")
    if reasons: return FenceDecision(False,"fence",tuple(reasons))
    return FenceDecision(True,"mutate",())
