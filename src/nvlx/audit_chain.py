"""Tamper-evident JSON audit chain for controller decisions."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import json


def _canon(v: dict) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"))

@dataclass(frozen=True)
class ChainedRecord:
    sequence: int
    previous_hash: str
    payload: dict
    record_hash: str
    def to_dict(self): return asdict(self)


def append(previous: ChainedRecord | None, payload: dict) -> ChainedRecord:
    seq = 1 if previous is None else previous.sequence + 1
    prev = "0" * 64 if previous is None else previous.record_hash
    material = {"sequence": seq, "previous_hash": prev, "payload": payload}
    digest = sha256(_canon(material).encode()).hexdigest()
    return ChainedRecord(seq, prev, dict(payload), digest)


def verify(records: list[ChainedRecord]) -> tuple[bool, tuple[str, ...]]:
    reasons=[]; previous=None
    for record in records:
        expected=append(previous,record.payload)
        if record.sequence != expected.sequence: reasons.append(f"sequence mismatch at {record.sequence}")
        if record.previous_hash != expected.previous_hash: reasons.append(f"previous hash mismatch at {record.sequence}")
        if record.record_hash != expected.record_hash: reasons.append(f"record hash mismatch at {record.sequence}")
        previous=record
    return (not reasons, tuple(reasons))
