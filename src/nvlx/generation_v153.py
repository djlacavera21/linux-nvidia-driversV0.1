"""Generation guards for dropping stale GPUFleet reconcile events."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class GenerationDecision:
    action: str
    event_generation: int
    latest_generation: int
    stale: bool
    reasons: tuple[str, ...]
    def to_dict(self): return asdict(self)

def evaluate(event_generation: int, latest_generation: int) -> GenerationDecision:
    if event_generation < 0 or latest_generation < 0:
        raise ValueError("generations must be >= 0")
    if event_generation < latest_generation:
        return GenerationDecision("discard-stale", event_generation, latest_generation, True, ("event generation older than latest observed generation",))
    if event_generation > latest_generation:
        return GenerationDecision("advance", event_generation, event_generation, False, ())
    return GenerationDecision("current", event_generation, latest_generation, False, ())
