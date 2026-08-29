"""Approval lifetime and revocation checks layered on v1 approvals."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from .approvals import Approval, ExecutionPlan, execution_allowed

@dataclass(frozen=True)
class ApprovalStatus:
    allowed: bool
    reasons: tuple[str, ...]
    expires_at: str
    revoked: bool
    def to_dict(self): return asdict(self)


def evaluate(plan: ExecutionPlan, approval: Approval, *, ttl_seconds: int=1800, revoked: bool=False, now: datetime | None=None) -> ApprovalStatus:
    if ttl_seconds < 60: raise ValueError("ttl_seconds must be >= 60")
    now = now or datetime.now(timezone.utc)
    approved_at = datetime.fromisoformat(approval.approved_at.replace("Z", "+00:00"))
    expires = approved_at + timedelta(seconds=ttl_seconds)
    ok,reasons = execution_allowed(plan,approval)
    reasons=list(reasons)
    if revoked: reasons.append("approval revoked")
    if now >= expires: reasons.append("approval expired")
    return ApprovalStatus(ok and not reasons,tuple(reasons),expires.isoformat().replace("+00:00","Z"),revoked)
