"""Bound concurrent GPU-node disruption during fleet rollouts."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math

@dataclass(frozen=True)
class RolloutBudget:
    total_nodes: int
    max_unavailable: int
    currently_unavailable: int
    slots: int
    allowed: bool
    def to_dict(self): return asdict(self)

def evaluate(total_nodes: int, currently_unavailable: int, *, max_unavailable: int | None = None, max_unavailable_fraction: float = 0.1) -> RolloutBudget:
    if total_nodes < 1: raise ValueError("total_nodes must be >= 1")
    if currently_unavailable < 0: raise ValueError("currently_unavailable must be >= 0")
    cap=max_unavailable if max_unavailable is not None else max(1,math.floor(total_nodes*max_unavailable_fraction))
    if cap < 1: raise ValueError("max_unavailable must be >= 1")
    slots=max(0,cap-currently_unavailable)
    return RolloutBudget(total_nodes,cap,currently_unavailable,slots,slots > 0)
