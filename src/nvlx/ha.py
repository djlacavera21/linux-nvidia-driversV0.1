"""High-availability controller lease planning."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class LeasePlan:
    namespace: str
    name: str
    holder_identity: str
    lease_duration_seconds: int
    renew_deadline_seconds: int
    retry_period_seconds: int
    valid: bool
    errors: tuple[str,...]
    def to_dict(self): return asdict(self)

def plan(namespace="nvlx-system", name="nvlx-controller", holder_identity="controller-0", lease_duration_seconds=30, renew_deadline_seconds=20, retry_period_seconds=5):
    errors=[]
    if not namespace or not name or not holder_identity: errors.append("namespace, name, and holder_identity are required")
    if lease_duration_seconds < 10: errors.append("lease duration must be at least 10 seconds")
    if not (0 < retry_period_seconds < renew_deadline_seconds < lease_duration_seconds): errors.append("require retry < renew deadline < lease duration")
    return LeasePlan(namespace,name,holder_identity,lease_duration_seconds,renew_deadline_seconds,retry_period_seconds,not errors,tuple(errors))

def kubernetes_manifest(p: LeasePlan) -> dict:
    return {"apiVersion":"coordination.k8s.io/v1","kind":"Lease","metadata":{"name":p.name,"namespace":p.namespace},"spec":{"holderIdentity":p.holder_identity,"leaseDurationSeconds":p.lease_duration_seconds}}
