"""Kubernetes-native maintenance policy rendered as a namespaced ConfigMap."""
from __future__ import annotations
import json

def render(*, namespace: str="nvlx-system", name: str="nvlx-maintenance-policy", start_hour_utc: int=2, end_hour_utc: int=5, emergency_override: bool=False) -> str:
    if not namespace or not name: raise ValueError("namespace and name are required")
    if not 0 <= start_hour_utc <= 23 or not 0 <= end_hour_utc <= 23: raise ValueError("hours must be 0..23")
    obj={
        "apiVersion":"v1","kind":"ConfigMap","metadata":{"name":name,"namespace":namespace,"labels":{"app.kubernetes.io/name":"nvlx-controller","nvlx.io/policy":"maintenance"}},
        "data":{"timezone":"UTC","startHourUTC":str(start_hour_utc),"endHourUTC":str(end_hour_utc),"emergencyOverride":"true" if emergency_override else "false"},
    }
    return json.dumps(obj,indent=2,sort_keys=True)+"\n"
