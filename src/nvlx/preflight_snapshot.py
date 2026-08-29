"""Immutable preflight snapshot for approval and execution revalidation."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib, json

@dataclass(frozen=True)
class PreflightSnapshot:
    captured_at: str
    fingerprint: str
    facts: dict
    def to_dict(self): return asdict(self)

def capture(facts: dict) -> PreflightSnapshot:
    canonical=json.dumps(facts,sort_keys=True,separators=(",", ":"),default=str)
    return PreflightSnapshot(datetime.now(timezone.utc).isoformat(),hashlib.sha256(canonical.encode()).hexdigest(),dict(facts))

def unchanged(snapshot: PreflightSnapshot, current_facts: dict) -> bool:
    return capture(current_facts).fingerprint == snapshot.fingerprint
