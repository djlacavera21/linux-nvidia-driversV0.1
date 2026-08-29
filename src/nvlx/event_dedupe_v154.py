"""Stable duplicate-event suppression for Kubernetes watch delivery."""
from __future__ import annotations
import hashlib, json

def fingerprint(*, event_type: str, resource_version: str, generation: int) -> str:
    if generation < 0: raise ValueError("generation must be >= 0")
    payload={"event_type":(event_type or "").strip().upper(),"generation":generation,"resource_version":(resource_version or "").strip()}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def duplicate(current_fingerprint: str, previous_fingerprint: str|None) -> bool:
    return bool(previous_fingerprint) and current_fingerprint == previous_fingerprint
