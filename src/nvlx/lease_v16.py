"""Kubernetes Lease acquisition/renewal with optimistic CAS fencing."""
from __future__ import annotations
from datetime import datetime, timezone
from urllib import parse
from .k8s_api_v16 import KubeClient, ApiError, ApiResponse

class LeaseElector:
    def __init__(self, client: KubeClient, identity: str, *, namespace="nvlx-system", name="nvlx-controller", duration_seconds=30, max_clock_skew_seconds=5):
        if not isinstance(identity,str) or not identity.strip(): raise ValueError("identity required")
        if isinstance(duration_seconds,bool) or not isinstance(duration_seconds,int) or duration_seconds < 10:
            raise ValueError("lease duration must be an integer >= 10 seconds")
        if isinstance(max_clock_skew_seconds,bool) or not isinstance(max_clock_skew_seconds,int) or max_clock_skew_seconds < 0:
            raise ValueError("max_clock_skew_seconds must be a non-negative integer")
        self.client=client; self.identity=identity; self.namespace=namespace; self.name=name; self.duration=duration_seconds
        self.max_clock_skew_seconds=max_clock_skew_seconds

    @property
    def path(self):
        return f"/apis/coordination.k8s.io/v1/namespaces/{parse.quote(self.namespace,safe='')}/leases/{parse.quote(self.name,safe='')}"

    @staticmethod
    def _now(): return datetime.now(timezone.utc)
    @staticmethod
    def _stamp(dt): return dt.isoformat().replace("+00:00","Z")

    def _fresh(self, spec: dict, now) -> bool:
        if not isinstance(spec,dict) or not isinstance(now,datetime) or now.tzinfo is None: return False
        stamp=spec.get("renewTime") or spec.get("acquireTime")
        if not isinstance(stamp,str) or not stamp: return False
        try:
            then=datetime.fromisoformat(stamp.replace("Z","+00:00"))
            duration=int(spec.get("leaseDurationSeconds") or self.duration)
        except (ValueError,TypeError,OverflowError): return False
        if then.tzinfo is None or duration <= 0: return False
        try:
            future_skew=(then-now).total_seconds()
            age=(now-then).total_seconds()
        except (TypeError,OverflowError): return False
        if future_skew > self.max_clock_skew_seconds: return False
        return age < duration

    def _verified_ours(self, response: ApiResponse | None) -> bool:
        if response is None or not isinstance(response.body,dict): return False
        meta=response.body.get("metadata"); spec=response.body.get("spec")
        if not isinstance(meta,dict) or not isinstance(spec,dict): return False
        rv=meta.get("resourceVersion")
        if not isinstance(rv,str) or not rv.strip(): return False
        if spec.get("holderIdentity") != self.identity: return False
        try:
            if int(spec.get("leaseDurationSeconds")) != self.duration: return False
            transitions=int(spec.get("leaseTransitions") or 0)
        except (TypeError,ValueError): return False
        if transitions < 0: return False
        return self._fresh(spec,self._now())

    def ensure_leader(self) -> bool:
        now=self._now()
        try:
            response=self.client.request_json("GET",self.path)
            lease=response.body
        except ApiError as e:
            if e.status != 404: return False
            body={"apiVersion":"coordination.k8s.io/v1","kind":"Lease","metadata":{"name":self.name,"namespace":self.namespace},"spec":{"holderIdentity":self.identity,"leaseDurationSeconds":self.duration,"acquireTime":self._stamp(now),"renewTime":self._stamp(now),"leaseTransitions":0}}
            try:
                created=self.client.request_json("POST",self.path.rsplit("/",1)[0],body)
                return self._verified_ours(created)
            except ApiError: return False
        if not isinstance(lease,dict): return False
        meta=lease.get("metadata"); spec=lease.get("spec")
        if not isinstance(meta,dict) or not isinstance(spec,dict): return False
        holder=spec.get("holderIdentity") or ""
        if not isinstance(holder,str): return False
        fresh=self._fresh(spec,now)
        if holder not in {"",self.identity} and fresh: return False
        try: transitions=int(spec.get("leaseTransitions") or 0)
        except (TypeError,ValueError): return False
        if transitions < 0: return False
        if holder != self.identity: transitions += 1
        new_spec={"holderIdentity":self.identity,"leaseDurationSeconds":self.duration,"renewTime":self._stamp(now),"leaseTransitions":transitions}
        if not spec.get("acquireTime") or holder != self.identity: new_spec["acquireTime"]=self._stamp(now)
        rv=meta.get("resourceVersion")
        if not isinstance(rv,str) or not rv.strip(): return False
        body={"metadata":{"resourceVersion":rv},"spec":new_spec}
        try:
            updated=self.client.request_json("PATCH",self.path,body,content_type="application/merge-patch+json")
            return self._verified_ours(updated)
        except ApiError: return False
