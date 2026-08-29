"""Progressive canary promotion for GPU fleet changes."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class CanaryDecision:
    promote: bool
    next_wave: int
    reasons: tuple[str, ...]
    def to_dict(self): return asdict(self)

def evaluate(*, current_wave: int, total_waves: int, healthy_fraction: float, min_healthy_fraction: float=0.99, diagnostics_passed: bool=True, security_passed: bool=True, quarantined: int=0, circuit_open: bool=False) -> CanaryDecision:
    reasons=[]
    if current_wave < 0 or total_waves < 1 or current_wave >= total_waves: reasons.append("invalid wave state")
    if healthy_fraction < min_healthy_fraction: reasons.append("healthy-node fraction below threshold")
    if not diagnostics_passed: reasons.append("diagnostics failed")
    if not security_passed: reasons.append("security gate failed")
    if quarantined > 0: reasons.append("quarantined nodes present")
    if circuit_open: reasons.append("fleet circuit breaker open")
    if reasons: return CanaryDecision(False,current_wave,tuple(reasons))
    return CanaryDecision(True,min(current_wave+1,total_waves),())
