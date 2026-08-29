"""Explicit controller state schema migrations."""
from __future__ import annotations
from dataclasses import dataclass, asdict

CURRENT_STATE_VERSION=2

@dataclass(frozen=True)
class MigrationResult:
    state: dict
    migrated: bool
    from_version: int
    to_version: int
    def to_dict(self): return asdict(self)


def migrate(state: dict) -> MigrationResult:
    data=dict(state)
    version=int(data.get("state_version",1))
    original=version
    if version > CURRENT_STATE_VERSION:
        raise ValueError("state was written by a newer nvlx controller")
    if version == 1:
        data.setdefault("last_reconcile_id",None)
        data.setdefault("leader_identity",None)
        data["state_version"]=2
        version=2
    return MigrationResult(data,original != version,original,version)
