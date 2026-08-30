"""Real Kubernetes list/watch/status runtime for nvlx 1.6.x."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import signal, threading
from .k8s_api_v16 import KubeClient, ApiError
from .operator_v15 import plan as operator_plan
from .finalizer import decide as finalizer_decide
from .runtime_guard_v161 import classify_watch_line, reconnect_delay

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
    reconnects: int=0

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
        self.stats.leader=False
        self._stop.set()

    def install_signal_handlers(self):
        signal.signal(signal.SIGTERM,lambda *_: self.stop())
        signal.signal(signal.SIGINT,lambda *_: self.stop())

    def _leader(self) -> bool:
        if self.stats.terminating:
            self.stats.leader=False; return False
        try: ok=bool(self.leader_check())
        except Exception:
            ok=False
        self.stats.leader=ok
        return ok

    @staticmethod
    def _status_from_plan(plan: dict) -> dict:
        return {k:v for k,v in plan.items() if k in {"phase","observed_generation","canary_wave","conditions"}}

    def _event(self, obj: dict, reason: str, note: str):
        meta=obj.get("metadata",{}); name=meta.get("name",""); uid=meta.get("uid","")
        if not name or not uid or self.stats.terminating: return
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
                if not self._leader(): return False
                fresh=self.client.get_fleet(name).body or {}; rv=fresh.get("metadata",{}).get("resourceVersion","")
                if not rv: return False
        return False

    def _finalize(self, obj: dict) -> bool:
        meta=obj.get("metadata",{}); finalizers=list(meta.get("finalizers") or [])
        if PROTECTIVE_FINALIZER not in finalizers: return True
        annotations=meta.get("annotations") or {}; status=obj.get("status") or {}
        try: quarantined=int(status.get("quarantined_nodes",0) or 0)
        except (TypeError,ValueError): return False
        decision=finalizer_decide(deleting=True,rollback_pending=annotations.get("nvlx.io/rollback-pending")=="true",quarantined_nodes=quarantined,active_execution=annotations.get("nvlx.io/active-execution")=="true",status_write_pending=False)
        if not decision.remove_finalizer or not self._leader(): return False
        remaining=[x for x in finalizers if x != PROTECTIVE_FINALIZER]
        try:
            self.client.patch_finalizers(meta.get("name",""),meta.get("resourceVersion",""),remaining); return True
        except ApiError as e:
            if e.status in {409,412,404,410}: return False
            raise

    def reconcile_object(self, obj: dict, *, event_type: str="MODIFIED") -> str:
        self.stats.reconcile_total += 1
        if not isinstance(obj,dict): self.stats.reconcile_failures += 1; return "invalid"
        meta=obj.get("metadata") or {}; name=meta.get("name",""); rv=str(meta.get("resourceVersion","") or "")
        try: generation=int(meta.get("generation",0) or 0)
        except (TypeError,ValueError): self.stats.reconcile_failures += 1; return "invalid"
        if not name or not rv or generation < 0: self.stats.reconcile_failures += 1; return "invalid"
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
        body=listing.body if isinstance(listing.body,dict) else {}; rv=str(body.get("metadata",{}).get("resourceVersion","") or "")
        if not rv: raise RuntimeError("GPUFleet list did not return resourceVersion")
        items=body.get("items",[])
        if not isinstance(items,list): raise RuntimeError("GPUFleet list items must be a list")
        for item in items:
            if self._stop.is_set(): return "stopped"
            self.reconcile_object(item,event_type="ADDED")
        self.stats.inventory_fresh=True; self.stats.last_resource_version=rv
        try:
            for event in self.client.watch_lines(self.client.watch_path(rv)):
                if self._stop.is_set(): return "stopped"
                decision=classify_watch_line(event)
                if decision.action in {"ignore-malformed","ignore-unknown"}: continue
                if decision.action in {"relist","reconnect","watch-error"}: return decision.action
                obj=event.get("object") or {}
                if decision.action=="bookmark":
                    if isinstance(obj,dict):
                        self.stats.last_resource_version=str(obj.get("metadata",{}).get("resourceVersion",self.stats.last_resource_version))
                    continue
                self.reconcile_object(obj,event_type=decision.action.upper())
            return "eof"
        except ApiError as e:
            self.stats.api_reachable=False
            if e.status==410: return "relist"
            if e.status==0 or e.status in {408,425,429} or 500 <= e.status <= 599: return "reconnect"
            raise

    def run_forever(self, *, max_backoff: float=30.0):
        if max_backoff <= 0: raise ValueError("max_backoff must be positive")
        self.install_signal_handlers(); attempt=0
        while not self._stop.is_set():
            try:
                result=self.list_and_watch_once()
                if result=="stopped": break
                if result in {"relist","reconnect","watch-error","eof"}:
                    self.stats.reconnects += 1
                    delay=reconnect_delay(attempt,maximum=max_backoff)
                    attempt=min(attempt+1,30)
                    if self._stop.wait(delay): break
                    continue
                attempt=0
            except Exception:
                self.stats.reconcile_failures += 1; self.stats.api_reachable=False; self.stats.reconnects += 1
                delay=reconnect_delay(attempt,maximum=max_backoff)
                attempt=min(attempt+1,30)
                if self._stop.wait(delay): break
