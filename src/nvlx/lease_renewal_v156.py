"""Lease renewal outcome classification for restart-safe leader fencing."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class RenewalDecision:
    action: str
    leadership_valid: bool
    retry: bool
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)


def classify(status_code: int, *, holder_unchanged: bool, resource_version_unchanged: bool) -> RenewalDecision:
    if status_code in {200,201} and holder_unchanged:
        return RenewalDecision("renewed",True,False,())
    if status_code in {409,412} or not resource_version_unchanged:
        return RenewalDecision("relist-fence",False,True,("lease changed concurrently",))
    if status_code==404:
        return RenewalDecision("lost",False,False,("lease disappeared",))
    if status_code==429 or 500 <= status_code <= 599:
        return RenewalDecision("retry-fenced",False,True,("renewal uncertain; mutations fenced",))
    if not holder_unchanged:
        return RenewalDecision("handoff",False,False,("lease holder changed",))
    return RenewalDecision("fence",False,False,("lease renewal failed",))
