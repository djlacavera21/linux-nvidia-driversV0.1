"""Production change-window policy for disruptive GPU operations."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

@dataclass(frozen=True)
class ChangeWindow:
    start_hour_utc: int
    end_hour_utc: int
    emergency_override: bool = False
    def to_dict(self): return asdict(self)

def allowed(window: ChangeWindow, now: datetime | None = None) -> tuple[bool, tuple[str, ...]]:
    if not 0 <= window.start_hour_utc <= 23 or not 0 <= window.end_hour_utc <= 23:
        return False, ("change-window hours must be 0..23",)
    if window.emergency_override:
        return True, ("emergency override active",)
    hour=(now or datetime.now(timezone.utc)).astimezone(timezone.utc).hour
    start,end=window.start_hour_utc,window.end_hour_utc
    inside=(start <= hour < end) if start < end else (hour >= start or hour < end)
    return inside, (() if inside else ("outside approved change window",))
