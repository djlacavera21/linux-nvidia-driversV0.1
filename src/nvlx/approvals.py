"""Approval-bound execution plan fingerprints."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib, json, secrets

@dataclass(frozen=True)
class ExecutionPlan:
    operation: str
    target: str
    steps: tuple[str, ...]
    config_fingerprint: str
    fingerprint: str
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class Approval:
    approval_id: str
    plan_fingerprint: str
    approved_by: str
    approved_at: str
    expires_at: str = ""
    def to_dict(self): return asdict(self)

def make_plan(operation: str, target: str, steps: list[str]|tuple[str,...], config_fingerprint: str) -> ExecutionPlan:
    payload={"operation":operation,"target":target,"steps":list(steps),"config_fingerprint":config_fingerprint}
    fp=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
    return ExecutionPlan(operation,target,tuple(steps),config_fingerprint,fp)

def approve(plan: ExecutionPlan, approved_by: str) -> Approval:
    if not approved_by.strip(): raise ValueError("approved_by is required")
    return Approval("apr-"+secrets.token_hex(8),plan.fingerprint,approved_by.strip(),datetime.now(timezone.utc).isoformat())

def execution_allowed(plan: ExecutionPlan, approval: Approval|None) -> tuple[bool, tuple[str,...]]:
    reasons=[]
    if approval is None: reasons.append("approval missing")
    elif approval.plan_fingerprint != plan.fingerprint: reasons.append("approval does not match current plan fingerprint")
    return (not reasons, tuple(reasons))
