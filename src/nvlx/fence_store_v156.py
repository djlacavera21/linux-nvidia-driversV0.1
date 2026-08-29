"""Durable fencing-token persistence with integrity verification."""
from __future__ import annotations
from pathlib import Path
import hashlib, hmac, json, os, tempfile
from .leadership_v155 import FenceToken

_FORMAT=2
_TOKEN_KEYS={"holder","epoch","lease_resource_version"}

def _token_dict(token: FenceToken) -> dict:
    return {"holder":token.holder,"epoch":token.epoch,"lease_resource_version":token.lease_resource_version}

def _digest(token_data: dict) -> str:
    raw=json.dumps(token_data,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

def _parse_token(data: dict) -> FenceToken:
    if set(data) != _TOKEN_KEYS: raise ValueError("invalid persisted fencing token schema")
    token=FenceToken(str(data["holder"]),int(data["epoch"]),str(data["lease_resource_version"]))
    if not token.holder or token.epoch < 0 or not token.lease_resource_version: raise ValueError("invalid persisted fencing token values")
    return token

def save(path: str | Path, token: FenceToken) -> None:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    token_data=_token_dict(token)
    envelope={"format":_FORMAT,"token":token_data,"sha256":_digest(token_data)}
    fd,tmp=tempfile.mkstemp(prefix=target.name+".",dir=str(target.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(envelope,f,sort_keys=True,separators=(",",":")); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,target)
        dirfd=os.open(str(target.parent),os.O_RDONLY)
        try: os.fsync(dirfd)
        finally: os.close(dirfd)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def load(path: str | Path) -> FenceToken | None:
    target=Path(path)
    if not target.exists(): return None
    data=json.loads(target.read_text(encoding="utf-8"))
    if set(data) == _TOKEN_KEYS:
        return _parse_token(data)  # legacy v1.5.6 state; re-saved as v2 after validation
    if set(data) != {"format","token","sha256"} or data.get("format") != _FORMAT:
        raise ValueError("invalid persisted fencing envelope")
    token_data=data.get("token")
    if not isinstance(token_data,dict) or not isinstance(data.get("sha256"),str):
        raise ValueError("invalid persisted fencing envelope values")
    if not hmac.compare_digest(_digest(token_data),data["sha256"]):
        raise ValueError("persisted fencing token integrity check failed")
    return _parse_token(token_data)
