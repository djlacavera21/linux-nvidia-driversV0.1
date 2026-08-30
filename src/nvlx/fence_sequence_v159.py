"""Sequenced checkpoint guard for persisted leadership fencing state."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .leadership_v155 import FenceToken
from .fence_monotonic_v158 import assess as assess_token

@dataclass(frozen=True)
class SequenceDecision:
    allowed: bool
    action: str
    next_sequence: int
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)

def assess(previous_sequence: int | None, previous_token: FenceToken | None, candidate_sequence: int, candidate_token: FenceToken, *, reacquired: bool=False) -> SequenceDecision:
    if candidate_sequence < 0:
        raise ValueError("candidate sequence must be >= 0")
    if previous_sequence is None:
        if previous_token is not None:
            raise ValueError("previous token requires previous sequence")
        if candidate_sequence != 1:
            return SequenceDecision(False,"reject-initial-sequence",1,("initial persisted fence sequence must be 1",))
        token=assess_token(None,candidate_token,reacquired=reacquired)
        return SequenceDecision(token.allowed,"persist-initial" if token.allowed else token.action,1,token.reasons)
    if previous_sequence < 0:
        raise ValueError("previous sequence must be >= 0")
    if previous_token is None:
        raise ValueError("previous sequence requires previous token")
    if candidate_sequence < previous_sequence:
        return SequenceDecision(False,"reject-sequence-rollback",previous_sequence,("candidate fence sequence is older than persisted sequence",))
    if candidate_sequence == previous_sequence:
        if candidate_token == previous_token:
            return SequenceDecision(False,"noop",previous_sequence,("fence checkpoint already persisted",))
        return SequenceDecision(False,"reject-sequence-replay",previous_sequence,("fence token changed without sequence advance",))
    if candidate_sequence != previous_sequence + 1:
        return SequenceDecision(False,"reject-sequence-gap",previous_sequence + 1,("fence sequence must advance exactly once per authority change",))
    if candidate_token == previous_token:
        return SequenceDecision(False,"reject-redundant-advance",previous_sequence,("unchanged fencing token cannot advance sequence",))
    token=assess_token(previous_token,candidate_token,reacquired=reacquired)
    if not token.allowed:
        return SequenceDecision(False,token.action,previous_sequence,token.reasons)
    return SequenceDecision(True,"persist-next",candidate_sequence,())

def verify_floor(persisted_sequence: int, trusted_minimum: int) -> SequenceDecision:
    if persisted_sequence < 0 or trusted_minimum < 0:
        raise ValueError("sequence values must be >= 0")
    if persisted_sequence < trusted_minimum:
        return SequenceDecision(False,"replay-detected",trusted_minimum,("persisted fence sequence is older than trusted checkpoint",))
    return SequenceDecision(True,"sequence-current",persisted_sequence,())
