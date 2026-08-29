"""Deterministic idempotency keys for reconciliation executions."""
from __future__ import annotations
import hashlib, json

def key(plan_fingerprint: str, target: str, generation: int) -> str:
    if not plan_fingerprint or not target or generation < 1:
        raise ValueError("plan fingerprint, target and positive generation are required")
    payload={"generation":generation,"plan_fingerprint":plan_fingerprint,"target":target}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
    return "exec-"+digest[:24]

def duplicate(candidate: str, completed: set[str] | tuple[str, ...] | list[str]) -> bool:
    return candidate in set(completed)
