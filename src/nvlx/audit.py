"""Append-only JSONL audit records for governed fleet decisions."""
from __future__ import annotations
from dataclasses import asdict,dataclass
from datetime import datetime,timezone
import json
from pathlib import Path

@dataclass(frozen=True)
class AuditEvent:
    timestamp:str
    action:str
    target:str
    allowed:bool
    reasons:tuple[str,...]
    def to_dict(self): return asdict(self)

def event(action:str,target:str,allowed:bool,reasons:tuple[str,...]=())->AuditEvent:
    return AuditEvent(datetime.now(timezone.utc).isoformat(),action,target,allowed,reasons)

def append(path:Path,record:AuditEvent)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(),sort_keys=True)+"\n")
