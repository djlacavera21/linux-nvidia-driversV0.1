"""Durable, generation-aware controller state."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path

_STATES={"idle","planned","awaiting-approval","approved","executing","succeeded","failed","blocked"}
@dataclass(frozen=True)
class ControllerState:
    generation: int
    phase: str
    config_fingerprint: str
    plan_fingerprint: str = ""
    approval_id: str = ""
    updated_at: str = ""
    message: str = ""
    def to_dict(self): return asdict(self)

def new_state(config_fingerprint: str) -> ControllerState:
    return ControllerState(1,"idle",config_fingerprint,updated_at=datetime.now(timezone.utc).isoformat())

def transition(state: ControllerState, phase: str, *, plan_fingerprint: str|None=None, approval_id: str|None=None, message: str="") -> ControllerState:
    if phase not in _STATES: raise ValueError(f"invalid phase: {phase}")
    allowed={"idle":{"planned","blocked"},"planned":{"awaiting-approval","approved","blocked"},"awaiting-approval":{"approved","blocked"},"approved":{"executing","blocked"},"executing":{"succeeded","failed"},"failed":{"planned","blocked"},"succeeded":{"planned","idle"},"blocked":{"planned","idle"}}
    if phase not in allowed.get(state.phase,set()): raise ValueError(f"invalid transition {state.phase}->{phase}")
    return ControllerState(state.generation+1,phase,state.config_fingerprint,plan_fingerprint if plan_fingerprint is not None else state.plan_fingerprint,approval_id if approval_id is not None else state.approval_id,datetime.now(timezone.utc).isoformat(),message)

def save(path: Path, state: ControllerState) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(state.to_dict(),sort_keys=True,indent=2)+"\n")
    tmp.replace(path)

def load(path: Path) -> ControllerState:
    d=json.loads(path.read_text()); return ControllerState(**d)
