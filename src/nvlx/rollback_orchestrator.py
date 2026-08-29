"""Approval-aware rollback orchestration for failed fleet executions."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .recovery import plan as recovery_plan

@dataclass(frozen=True)
class RollbackOrchestration:
    action: str
    automatic: bool
    steps: tuple[str, ...]
    reasons: tuple[str, ...]
    def to_dict(self): return asdict(self)

def plan(*, rollback_available: bool, security_failure: bool, state_uncertain: bool, failure_count: int, package_restore: bool=True, module_restore: bool=True, initramfs_refresh: bool=True) -> RollbackOrchestration:
    r=recovery_plan(rollback_available=rollback_available,security_failure=security_failure,state_uncertain=state_uncertain,failure_count=failure_count)
    if r.action != "rollback": return RollbackOrchestration(r.action,r.automatic,(),r.reasons)
    steps=[]
    if package_restore: steps.append("restore-package-state")
    if module_restore: steps.append("restore-module-snapshot")
    steps.append("depmod")
    if initramfs_refresh: steps.append("refresh-initramfs")
    steps.extend(("reboot-or-reload-under-maintenance-policy","boot-validate","health-slo-security-validate"))
    return RollbackOrchestration("rollback",r.automatic,tuple(steps),r.reasons)
