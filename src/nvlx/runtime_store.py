"""Persistent circuit/idempotency state for the production controller."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json, os, tempfile

@dataclass(frozen=True)
class RuntimeStore:
    state_version: int
    failure_count: int
    completed_execution_keys: tuple[str, ...]
    last_successful_generation: int
    def to_dict(self): return asdict(self)

def empty() -> RuntimeStore:
    return RuntimeStore(1,0,(),0)

def load(path: Path) -> RuntimeStore:
    if not path.exists(): return empty()
    d=json.loads(path.read_text())
    if int(d.get("state_version",0)) != 1: raise ValueError("unsupported runtime state version")
    return RuntimeStore(1,max(0,int(d.get("failure_count",0))),tuple(d.get("completed_execution_keys",())),max(0,int(d.get("last_successful_generation",0))))

def save(path: Path, state: RuntimeStore) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+".",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w") as f: json.dump(state.to_dict(),f,sort_keys=True,separators=(",",":")); f.write("\n")
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def record_success(state: RuntimeStore, execution_key: str, generation: int) -> RuntimeStore:
    keys=tuple(dict.fromkeys((*state.completed_execution_keys,execution_key)))
    return RuntimeStore(1,0,keys,max(state.last_successful_generation,generation))

def record_failure(state: RuntimeStore) -> RuntimeStore:
    return RuntimeStore(1,state.failure_count+1,state.completed_execution_keys,state.last_successful_generation)
