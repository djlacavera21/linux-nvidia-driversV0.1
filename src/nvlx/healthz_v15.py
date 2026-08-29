"""Readiness/liveness decisions for the live operator."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Health:
    live: bool
    ready: bool
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)

def evaluate(*, process_ok: bool=True, api_reachable: bool, leader: bool, inventory_fresh: bool, lease_fresh: bool=True) -> Health:
    live=bool(process_ok)
    reasons=[]
    if not live: reasons.append("operator process unhealthy")
    if not api_reachable: reasons.append("kubernetes API unreachable")
    if not leader: reasons.append("standby replica")
    if leader and not lease_fresh: reasons.append("leader lease stale")
    if not inventory_fresh: reasons.append("inventory stale")
    ready=live and api_reachable and leader and lease_fresh and inventory_fresh
    return Health(live,ready,tuple(reasons))
