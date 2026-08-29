"""Durable fencing-token persistence for restart-safe leadership validation."""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import json, os, tempfile
from .leadership_v155 import FenceToken


def save(path: str | Path, token: FenceToken) -> None:
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=target.name+".",dir=str(target.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(asdict(token),f,sort_keys=True,separators=(",",":")); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,target)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def load(path: str | Path) -> FenceToken | None:
    target=Path(path)
    if not target.exists(): return None
    data=json.loads(target.read_text(encoding="utf-8"))
    keys=set(data)
    if keys != {"holder","epoch","lease_resource_version"}: raise ValueError("invalid persisted fencing token schema")
    token=FenceToken(str(data["holder"]),int(data["epoch"]),str(data["lease_resource_version"]))
    if not token.holder or token.epoch < 0 or not token.lease_resource_version: raise ValueError("invalid persisted fencing token values")
    return token
