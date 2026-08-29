"""Fleet circuit breaker for bounded failure blast radius."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class CircuitState:
    failures: int
    threshold: int
    open: bool
    reason: str
    def to_dict(self): return asdict(self)

def evaluate(failures: int, threshold: int = 3, *, security_failure: bool = False) -> CircuitState:
    if threshold < 1: raise ValueError("threshold must be >= 1")
    if failures < 0: raise ValueError("failures must be >= 0")
    if security_failure:
        return CircuitState(failures,threshold,True,"security gate failure")
    opened=failures >= threshold
    return CircuitState(failures,threshold,opened,"failure threshold reached" if opened else "closed")
