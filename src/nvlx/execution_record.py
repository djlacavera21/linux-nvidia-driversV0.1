"""Execution records with explicit rollback-required outcomes."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

def _now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

@dataclass(frozen=True)
class ExecutionRecord:
    plan_fingerprint: str
    state: str
    started_at: str
    finished_at: str | None
    rollback_required: bool
    message: str | None
    def to_dict(self): return asdict(self)


def start(plan_fingerprint: str) -> ExecutionRecord:
    return ExecutionRecord(plan_fingerprint,"running",_now(),None,False,None)

def finish(record: ExecutionRecord, *, success: bool, message: str | None=None) -> ExecutionRecord:
    return ExecutionRecord(record.plan_fingerprint,"succeeded" if success else "failed",record.started_at,_now(),not success,message)
