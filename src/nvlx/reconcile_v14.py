"""Map runtime decisions into Kubernetes-native GPUFleet status and events."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .status_conditions import summarize
from .k8s_events import event

@dataclass(frozen=True)
class ReconcileResult:
    phase: str
    observed_generation: int
    canary_wave: int
    conditions: list[dict]
    event: dict
    requeue: bool
    def to_dict(self): return asdict(self)

def reconcile(name: str, *, generation: int, allowed: bool, runtime_action: str, runtime_reasons: tuple[str,...]|list[str], current_wave: int=0, promoted: bool=False) -> ReconcileResult:
    if generation < 0 or current_wave < 0: raise ValueError("generation and current_wave must be >=0")
    if not allowed:
        msg="; ".join(runtime_reasons) or "runtime safety gate blocked reconciliation"
        return ReconcileResult("Blocked",generation,current_wave,summarize(ready=False,progressing=False,degraded=True,generation=generation,message=msg),event(name,reason="ReconcileBlocked",note=msg,warning=True),True)
    wave=current_wave+1 if promoted else current_wave
    if runtime_action in {"noop","complete"}:
        return ReconcileResult("Ready",generation,wave,summarize(ready=True,progressing=False,degraded=False,generation=generation),event(name,reason="ReconcileComplete",note="desired fleet state observed"),False)
    return ReconcileResult("Progressing",generation,wave,summarize(ready=False,progressing=True,degraded=False,generation=generation),event(name,reason="ReconcileProgressing",note=f"runtime action {runtime_action}"),True)
