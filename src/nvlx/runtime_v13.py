"""nvlx 1.3 integrated reconciliation gate evaluation."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from .change_window import ChangeWindow, allowed as window_allowed
from .circuit_breaker import evaluate as circuit_evaluate
from .idempotency import duplicate
from .rollout_budget import evaluate as budget_evaluate
from .preflight_snapshot import PreflightSnapshot, unchanged

@dataclass(frozen=True)
class RuntimeDecision:
    action: str
    allowed: bool
    reasons: tuple[str, ...]
    rollout_slots: int
    circuit_open: bool
    def to_dict(self): return asdict(self)

def decide(*, leader: bool, approval_valid: bool, window: ChangeWindow, preflight: PreflightSnapshot, current_facts: dict, execution_key: str, completed_keys: set[str]|tuple[str,...]|list[str], total_nodes: int, currently_unavailable: int, failure_count: int, security_failure: bool=False, now: datetime|None=None) -> RuntimeDecision:
    reasons=[]
    if not leader: reasons.append("not lease holder")
    if not approval_valid: reasons.append("approval invalid")
    win_ok,win_reasons=window_allowed(window,now); reasons.extend(win_reasons if not win_ok else ())
    if not unchanged(preflight,current_facts): reasons.append("preflight facts changed")
    if duplicate(execution_key,completed_keys): reasons.append("execution key already completed")
    budget=budget_evaluate(total_nodes,currently_unavailable)
    if not budget.allowed: reasons.append("rollout disruption budget exhausted")
    circuit=circuit_evaluate(failure_count,security_failure=security_failure)
    if circuit.open: reasons.append(circuit.reason)
    if reasons:
        action="quarantine" if security_failure else "hold"
        return RuntimeDecision(action,False,tuple(reasons),budget.slots,circuit.open)
    return RuntimeDecision("execute",True,(),budget.slots,circuit.open)
