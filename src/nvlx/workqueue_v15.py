"""Bounded reconcile retry/backoff policy."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class QueueDecision:
    delay_seconds: int
    retry: bool
    dead_letter: bool
    def to_dict(self): return asdict(self)

def retry(attempt: int, *, base_seconds: int=2, max_seconds: int=300, max_attempts: int=8) -> QueueDecision:
    if attempt < 0: raise ValueError("attempt must be >=0")
    if attempt >= max_attempts: return QueueDecision(0,False,True)
    return QueueDecision(min(max_seconds,base_seconds*(2**attempt)),True,False)
