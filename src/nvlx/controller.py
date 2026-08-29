"""Production reconciliation planner for nvlx 1.0."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .approvals import ExecutionPlan, make_plan
from .config_v1 import ConfigReport
from .v1_compat import CompatibilityReport

@dataclass(frozen=True)
class ReconcilePlan:
    allowed: bool
    operation: str
    target: str
    plan: ExecutionPlan|None
    reasons: tuple[str,...]
    def to_dict(self):
        d=asdict(self)
        if self.plan is not None: d["plan"]=self.plan.to_dict()
        return d

def plan(config: ConfigReport, compat: CompatibilityReport, *, operation: str, target: str, steps: list[str]|tuple[str,...]) -> ReconcilePlan:
    reasons=[]
    if not config.valid: reasons.extend(config.errors)
    if not compat.compatible: reasons.extend(compat.errors)
    if operation in {"upgrade-gpu-operator","enable-dra"} and compat.allocation_mode=="dra" and not compat.computedomains_crd_ready:
        reasons.append("ComputeDomain CRDs are not ready")
    if reasons: return ReconcilePlan(False,operation,target,None,tuple(reasons))
    ep=make_plan(operation,target,steps,config.fingerprint)
    return ReconcilePlan(True,operation,target,ep,())
