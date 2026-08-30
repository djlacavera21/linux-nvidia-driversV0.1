"""Kubernetes Lease acquisition/renewal with optimistic CAS fencing."""
from __future__ import annotations
from datetime import datetime, timezone
from urllib import parse
from .k8s_api_v16 import KubeClient, ApiError

class LeaseElector:
    def __init__(self, client: KubeClient, identity: str, *, namespace="nvlx-system", name="nvlx-controller", duration_seconds=30):
        if not identity.strip(): raise ValueError("identity required")
        if duration_seconds < 10: raise ValueError("lease duration must be >= 10 seconds")
        self.client=client; self.identity=identity; self.namespace=namespace; self.name=name; self.duration=duration_seconds

    @property
    def path(self):
        return f"/apis/coordination.k8s.io/v1/namespaces/{parse.quote(self.namespace,safe='')}/leases/{parse.quote(self.name,safe='')}"

    @staticmethod
    def _now(): return datetime.now(timezone.utc)
    @staticmethod
    def _stamp(dt): return dt.isoformat().replace("+00:00","Z")

    def _fresh(self, spec: dict, now) -> bool:
        stamp=spec.get("renewTime") or spec.get("acquireTime")
        if not stamp: return False
        try: then=datetime.fromisoformat(stamp.replace("Z","+00:00"))
        except ValueError: return False
        return (now-then).total_seconds() < int(spec.get("leaseDurationSeconds") or self.duration)

    def ensure_leader(self) -> bool:
        now=self._now()
        try:
            lease=self.client.request_json("GET",self.path).body or {}
        except ApiError as e:
            if e.status != 404: return False
            body={"apiVersion":"coordination.k8s.io/v1","kind":"Lease","metadata":{"name":self.name,"namespace":self.namespace},"spec":{"holderIdentity":self.identity,"leaseDurationSeconds":self.duration,"acquireTime":self._stamp(now),"renewTime":self._stamp(now),"leaseTransitions":0}}
            try:
                self.client.request_json("POST",self.path.rsplit("/",1)[0],body); return True
            except ApiError: return False
        meta=lease.get("metadata") or {}; spec=lease.get("spec") or {}; holder=spec.get("holderIdentity") or ""
        fresh=self._fresh(spec,now)
        if holder not in {"",self.identity} and fresh: return False
        transitions=int(spec.get("leaseTransitions") or 0)
        if holder != self.identity: transitions += 1
        new_spec={"holderIdentity":self.identity,"leaseDurationSeconds":self.duration,"renewTime":self._stamp(now),"leaseTransitions":transitions}
        if not spec.get("acquireTime") or holder != self.identity: new_spec["acquireTime"]=self._stamp(now)
        body={"metadata":{"resourceVersion":meta.get("resourceVersion","")},"spec":new_spec}
        if not body["metadata"]["resourceVersion"]: return False
        try:
            self.client.request_json("PATCH",self.path,body,content_type="application/merge-patch+json"); return True
        except ApiError as e:
            if e.status in {409,412}: return False
            return False
