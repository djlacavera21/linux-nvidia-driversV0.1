"""Kubernetes Event payload plans for controller decisions."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

@dataclass(frozen=True)
class EventPlan:
    type: str
    reason: str
    note: str
    action: str
    regarding_name: str
    def to_dict(self): return asdict(self)

def event(name: str, *, reason: str, note: str, action: str="Reconcile", warning: bool=False) -> dict:
    now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    return {"apiVersion":"events.k8s.io/v1","kind":"Event","metadata":{"generateName":f"{name}-","namespace":"nvlx-system"},"eventTime":now,"type":"Warning" if warning else "Normal","reason":reason,"note":note,"action":action,"regarding":{"apiVersion":"nvlx.io/v1alpha1","kind":"GPUFleet","name":name},"reportingController":"nvlx.io/controller","reportingInstance":"nvlx-controller"}
