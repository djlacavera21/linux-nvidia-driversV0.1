"""Stable status fingerprints to suppress redundant Kubernetes status writes."""
from __future__ import annotations
import hashlib, json

_DROP_KEYS={
    "lastTransitionTime","eventTime","deprecatedLastTimestamp","deprecatedFirstTimestamp",
    "last_transition_time","event_time","deprecated_last_timestamp","deprecated_first_timestamp",
}

def _stable(value):
    if isinstance(value,dict):
        return {k:_stable(v) for k,v in sorted(value.items()) if k not in _DROP_KEYS and k != "event"}
    if isinstance(value,list): return [_stable(v) for v in value]
    if isinstance(value,tuple): return [_stable(v) for v in value]
    return value

def fingerprint(status: dict) -> str:
    canonical=json.dumps(_stable(status),sort_keys=True,separators=(",",":"),default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()

def changed(status: dict, previous_fingerprint: str|None) -> tuple[bool,str]:
    current=fingerprint(status)
    return current != (previous_fingerprint or ""), current
