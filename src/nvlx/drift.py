"""Classify desired/observed fleet drift without mutating state."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class DriftReport:
    drifted: bool
    changed: tuple[str, ...]
    disruptive: tuple[str, ...]
    requires_approval: bool
    def to_dict(self): return asdict(self)

def classify(desired: dict, observed: dict) -> DriftReport:
    keys=sorted(set(desired)|set(observed))
    changed=tuple(k for k in keys if desired.get(k) != observed.get(k))
    disruptive_keys={"driver_version","gpu_operator_version","mig_strategy","dra_mode","fabric_manager_version","network_operator_version"}
    disruptive=tuple(k for k in changed if k in disruptive_keys)
    return DriftReport(bool(changed),changed,disruptive,bool(disruptive))
