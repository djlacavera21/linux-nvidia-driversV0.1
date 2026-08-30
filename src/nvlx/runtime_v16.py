"""Real Kubernetes list/watch/status runtime for nvlx 1.6."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import signal, threading, time
from .k8s_api_v16 import KubeClient, ApiError
from .operator_v15 import plan as operator_plan
from .finalizer import decide as finalizer_decide

PROTECTIVE_FINALIZER="nvlx.io/fleet-protection"

@dataclass
class RuntimeStats:
    reconcile_total: int=0
    reconcile_failures: int=0
    last_resource_version: str=""
    api_reachable: bool=False
    leader: bool=False
    terminating: bool=False
    inventory_fresh: bool=False

@dataclass
class Runtime:
    client: KubeClient
    identity: str
    namespace: str="nvlx-system"
    leader_check: callable=lambda: True
    stats: RuntimeStats=field(default_factory=RuntimeStats)
    _stop: threading.Event=field(default_factory=threading.Event)

    def stop(self):
        self.stats.terminating=True
        self._stop.set()

    def install_signal_handlers(self):
        signal.signal(signal.SIGTERM,lambda *_: self.stop())
        signal.signal(signal.SIGINT,lambda *_: self.stop())

    def _leader(self) -> bool:
        ok=bool(self.leader_check()) and not self.stats.terminating
        self.stats.leader=ok
        return ok

    @staticmethod
    def _status_from_plan(plan: dict) -> dict:
        return {k:v for k,v in plan.items() if k in {"phase","observed_generation","canary_wave","conditions"}}

    def _event(self, obj: dict, reason: str, note: str):
        meta=obj.get("metadata",{}); name=meta.get("name",""); uid=meta.get("uid","")
        if not name or not uid: return
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
        event={"apiVersion":"events.k8s.io/v1","kind":"Event","metadata":{"generateName":f"nvlx-{name}-","namespace":self.namespace},"eventTime":now,"reportingController":"nvlx.io/operator","reportingInstance":self.identity,"action":"Reconcile","reason":reason,"note":note[:1024],"type":"Normal","regarding":{"apiVersion":"nvlx.io/v1alpha1","kind":"GPUFleet","name":name,"uid":uid}}
        try: self.client.create_event(self.namespace,event)
        except ApiError: pass

    def _patch_status(self, obj: dict, status: dict) -> bool:
        meta=obj.get("metadata",{}); name=meta.get("name",""); rv=meta.get("resourceVersion","")
        for _ in range(2):
            if not self._leader(): return False
            try:
                self.client.patch_status(name,rv,status); return True
            except ApiError as e:
                if e.status not in {409,412}: raise
                fresh=self.client.get_fleet(name).body or {}; rv=fresh.get("metadata",{}).get("resourceVersion","")
                if not rv: return False
        return False

    def _finalize(self, obj: dict) -> bool:
        meta=obj.get("metadata",{}); finalizers=list(meta.get("finalizers") or [])
        if PROTECTIVE_FINALIZER not in finalizers: return True
        annotations=meta.get("annotations") or {}; status=obj.get("status") or {}
        decision=finalizer_decide(deleting=True,rollback_pending=annotations.get("nvlx.io/rollback-pending")=="true",quarantined_nodes=int(status.get("quarantined_nodes",0) or 0),active_execution=annotations.get("nvlx.io/active-execution")=="true",status_write_pending=False)
        if not decision.remove_finalizer: return False
        if not self._leader(): return False
        remaining=[x for x in finalizers if x != PROTECTIVE_FINALIZER]
        try:
            self.client.patch_finalizers(meta.get("name",""),meta.get("resourceVersion",""),remaining); return True
        except ApiError as e:
            if e.status in {409,412}: return False
            raise

    def reconcile_object(self, obj: dict, *, event_type: str="MODIFIED") -> str:
        self.stats.reconcile_total += 1
        meta=obj.get("metadata") or {}; name=meta.get("name",""); rv=str(meta.get("resourceVersion","") or ""); generation=int(meta.get("generation",0) or 0)
        if not name or not rv: self.stats.reconcile_failures += 1; return "invalid"
        self.stats.last_resource_version=rv
        if meta.get("deletionTimestamp"):
            return "finalized" if self._finalize(obj) else "finalizer-hold"
        if not self._leader(): return "standby"
        annotations=meta.get("annotations") or {}
        allowed=annotations.get("nvlx.io/approved")=="true"
        p=operator_plan(name,event_type=event_type,resource_version=rv,generation=generation,allowed=allowed,runtime_action="execute" if allowed else "hold",mutation_fence_ok=True)
        if p.action=="patch-status" and p.reconcile:
            status=self._status_from_plan(p.reconcile)
            if self._patch_status(obj,status):
                self._event(obj,"Reconciled",f"GPUFleet status advanced to {status.get('phase','Unknown')}")
                return "patched"
            return "fenced"
        return p.action

    def list_and_watch_once(self) -> str:
        listing=self.client.list_fleets(); self.stats.api_reachable=True
        body=listing.body or {}; rv=str(body.get("metadata",{}).get("resourceVersion","") or "")
        if not rv: raise RuntimeError("GPUFleet list did not return resourceVersion")
        for item in body.get("items",[]):
            if self._stop.is_set(): return "stopped"
            self.reconcile_object(item,event_type="ADDED")
        self.stats.inventory_fresh=True; self.stats.last_resource_version=rv
        try:
            for event in self.client.watch_lines(self.client.watch_path(rv)):
                if self._stop.is_set(): return "stopped"
                et=(event.get("type") or "").upper(); obj=event.get("object") or {}
                if et=="ERROR":
                    code=int(obj.get("code",0) or 0)
                    return "relist" if code==410 else "watch-error"
                if et=="BOOKMARK":
                    self.stats.last_resource_version=str(obj.get("metadata",{}).get("resourceVersion",self.stats.last_resource_version)); continue
                self.reconcile_object(obj,event_type=et)
            return "eof"
        except ApiError as e:
            self.stats.api_reachable=False
            if e.status==410: return "relist"
            raise

    def run_forever(self, *, max_backoff: float=30.0):
        self.install_signal_handlers(); delay=1.0
        while not self._stop.is_set():
            try:
                result=self.list_and_watch_once(); delay=1.0
                if result=="stopped": break
            except Exception:
                self.stats.reconcile_failures += 1; self.stats.api_reachable=False
                if self._stop.wait(delay): break
                delay=min(max_backoff,delay*2)
