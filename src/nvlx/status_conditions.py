"""Kubernetes-style status condition helpers for GPUFleet resources."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

@dataclass(frozen=True)
class Condition:
    type: str
    status: str
    reason: str
    message: str
    observed_generation: int
    last_transition_time: str
    def to_dict(self): return asdict(self)

def make(type: str, status: bool, reason: str, message: str, observed_generation: int) -> Condition:
    if observed_generation < 0: raise ValueError("observed_generation must be >=0")
    return Condition(type,"True" if status else "False",reason,message,observed_generation,datetime.now(timezone.utc).isoformat().replace("+00:00","Z"))

def summarize(*, ready: bool, progressing: bool, degraded: bool, generation: int, message: str="") -> list[dict]:
    return [
      make("Ready",ready,"Ready" if ready else "NotReady",message or ("fleet ready" if ready else "fleet not ready"),generation).to_dict(),
      make("Progressing",progressing,"Reconciling" if progressing else "Stable","reconciliation in progress" if progressing else "no rollout in progress",generation).to_dict(),
      make("Degraded",degraded,"SafetyGate" if degraded else "Healthy","safety gate blocked progression" if degraded else "no degradation detected",generation).to_dict(),
    ]
