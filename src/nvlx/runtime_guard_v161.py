"""Runtime hardening helpers for nvlx 1.6.1."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class WatchDecision:
    action: str
    retry: bool
    reason: str

def classify_watch_line(value) -> WatchDecision:
    if not isinstance(value, dict):
        return WatchDecision("ignore-malformed", False, "watch event is not an object")
    event_type=str(value.get("type") or "").strip().upper()
    if not event_type:
        return WatchDecision("ignore-malformed", False, "watch event type is missing")
    if event_type=="ERROR":
        obj=value.get("object") if isinstance(value.get("object"),dict) else {}
        try: code=int(obj.get("code",0) or 0)
        except (TypeError,ValueError): code=0
        if code==410: return WatchDecision("relist", True, "watch resourceVersion expired")
        if code in {408,425,429} or 500 <= code <= 599:
            return WatchDecision("reconnect", True, f"transient watch error {code}")
        return WatchDecision("watch-error", False, f"non-retryable watch error {code}")
    if event_type in {"ADDED","MODIFIED","DELETED","BOOKMARK"}:
        return WatchDecision(event_type.lower(), False, "valid watch event")
    return WatchDecision("ignore-unknown", False, f"unknown watch event type {event_type}")

def reconnect_delay(attempt: int, *, base: float=1.0, maximum: float=30.0) -> float:
    if isinstance(attempt,bool) or not isinstance(attempt,int) or attempt < 0:
        raise ValueError("attempt must be a nonnegative integer")
    if base <= 0 or maximum <= 0 or base > maximum:
        raise ValueError("invalid reconnect bounds")
    return min(maximum, base * (2 ** attempt))
