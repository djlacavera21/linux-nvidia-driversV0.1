"""Readiness/liveness decisions for the live operator."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Health:
    live: bool
    ready: bool
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)

def evaluate(*, process_ok: bool=True, api_reachable: bool, leader: bool, inventory_fresh: bool) -> Health:
    live=bool(process_ok)
    reasons=[]
    if not api_reachable: reasons.append("kubernetes API unreachable")
    if not leader: reasons.append("standby replica")
    if not inventory_fresh: reasons.append("inventory stale")
    return Health(live,live and api_reachable and leader and inventory_fresh,tuple(reasons))
