"""Bounded reconcile retry/backoff policy."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib

@dataclass(frozen=True)
class QueueDecision:
    delay_seconds: int
    retry: bool
    dead_letter: bool
    reason: str
    def to_dict(self): return asdict(self)

def retry(attempt: int, *, base_seconds: int=2, max_seconds: int=300, max_attempts: int=8, jitter_key: str|None=None) -> QueueDecision:
    if attempt < 0: raise ValueError("attempt must be >= 0")
    if base_seconds < 1: raise ValueError("base_seconds must be >= 1")
    if max_seconds < base_seconds: raise ValueError("max_seconds must be >= base_seconds")
    if max_attempts < 1: raise ValueError("max_attempts must be >= 1")
    if attempt >= max_attempts:
        return QueueDecision(0,False,True,"retry budget exhausted")
    raw=min(max_seconds,base_seconds*(2**attempt))
    if jitter_key:
        window=max(1,min(raw//4,30))
        digest=hashlib.sha256(f"{jitter_key}:{attempt}".encode()).digest()
        raw=min(max_seconds,raw+(int.from_bytes(digest[:2],"big") % (window+1)))
        return QueueDecision(raw,True,False,"bounded exponential backoff with deterministic jitter")
    return QueueDecision(raw,True,False,"bounded exponential backoff")
