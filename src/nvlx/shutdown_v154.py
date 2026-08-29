"""Graceful shutdown gate for live operator mutations."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class ShutdownDecision:
    accepting_work: bool
    ready: bool
    action: str
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)

def evaluate(*, terminating: bool, active_mutation: bool) -> ShutdownDecision:
    if not terminating:
        return ShutdownDecision(True,True,"serve",())
    if active_mutation:
        return ShutdownDecision(False,False,"drain",("termination requested; finish active mutation before exit",))
    return ShutdownDecision(False,False,"exit",("termination requested; no active mutation remains",))
