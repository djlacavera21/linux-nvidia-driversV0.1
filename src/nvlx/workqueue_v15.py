"""Bounded reconcile retry/backoff policy."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class QueueDecision:
    delay_seconds: int
    retry: bool
    dead_letter: bool
    reason: str
    def to_dict(self): return asdict(self)

def retry(attempt: int, *, base_seconds: int=2, max_seconds: int=300, max_attempts: int=8) -> QueueDecision:
    if attempt < 0: raise ValueError("attempt must be >= 0")
    if base_seconds < 1: raise ValueError("base_seconds must be >= 1")
    if max_seconds < base_seconds: raise ValueError("max_seconds must be >= base_seconds")
    if max_attempts < 1: raise ValueError("max_attempts must be >= 1")
    if attempt >= max_attempts:
        return QueueDecision(0,False,True,"retry budget exhausted")
    return QueueDecision(min(max_seconds,base_seconds*(2**attempt)),True,False,"bounded exponential backoff")
