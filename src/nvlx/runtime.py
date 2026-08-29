"""Bounded production reconciliation loop primitives."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid

@dataclass(frozen=True)
class ReconcileTick:
    reconcile_id: str
    observed_generation: int
    desired_generation: int
    leader: bool
    action: str
    reason: str
    at: str
    def to_dict(self): return asdict(self)


def tick(*, observed_generation: int, desired_generation: int, leader: bool, blocked: bool=False) -> ReconcileTick:
    if observed_generation < 0 or desired_generation < 0:
        raise ValueError("generations must be >= 0")
    now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    rid=str(uuid.uuid4())
    if not leader:
        return ReconcileTick(rid,observed_generation,desired_generation,False,"standby","not lease holder",now)
    if blocked:
        return ReconcileTick(rid,observed_generation,desired_generation,True,"hold","safety gate blocked reconciliation",now)
    if observed_generation >= desired_generation:
        return ReconcileTick(rid,observed_generation,desired_generation,True,"noop","desired generation already observed",now)
    return ReconcileTick(rid,observed_generation,desired_generation,True,"reconcile","desired generation is newer",now)
