"""Fleet canary and upgrade-wave planning."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import math

@dataclass(frozen=True)
class UpgradeWave:
    index:int; nodes:tuple[str,...]; canary:bool
    def to_dict(self): return asdict(self)

def plan_waves(nodes:list[str], *, canary_count:int=1, wave_size:int=5)->tuple[UpgradeWave,...]:
    unique=sorted(set(nodes))
    if canary_count<1 or wave_size<1: raise ValueError("canary_count and wave_size must be >= 1")
    if not unique: return ()
    canaries=tuple(unique[:min(canary_count,len(unique))]); waves=[UpgradeWave(0,canaries,True)]
    rest=unique[len(canaries):]
    for i in range(math.ceil(len(rest)/wave_size)):
        chunk=tuple(rest[i*wave_size:(i+1)*wave_size])
        if chunk: waves.append(UpgradeWave(i+1,chunk,False))
    return tuple(waves)

def advancement_allowed(*, qualified:bool, diagnostics_passed:bool, security_gate_passed:bool, quarantined:int=0)->tuple[bool,tuple[str,...]]:
    reasons=[]
    if not qualified: reasons.append("node qualification failed")
    if not diagnostics_passed: reasons.append("DCGM diagnostics failed")
    if not security_gate_passed: reasons.append("security gate failed")
    if quarantined: reasons.append(f"{quarantined} node(s) quarantined")
    return not reasons,tuple(reasons)
