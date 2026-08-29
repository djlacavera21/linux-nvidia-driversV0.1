"""Graceful shutdown and leadership-loss gate for live operator mutations."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class ShutdownDecision:
    accepting_work: bool
    ready: bool
    action: str
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)

def evaluate(*, terminating: bool, active_mutation: bool, leadership_valid: bool=True) -> ShutdownDecision:
    if not leadership_valid:
        if active_mutation:
            return ShutdownDecision(False,False,"fence-drain",("leadership lost; block all further mutation writes and drain in-flight work",))
        return ShutdownDecision(False,False,"standby",("leadership lost; mutation authority revoked",))
    if not terminating:
        return ShutdownDecision(True,True,"serve",())
    if active_mutation:
        return ShutdownDecision(False,False,"drain",("termination requested; finish active mutation before exit",))
    return ShutdownDecision(False,False,"exit",("termination requested; no active mutation remains",))
