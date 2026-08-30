"""Real Kubernetes list/watch/status runtime for nvlx 1.6.x."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import signal, threading
from .k8s_api_v16 import KubeClient, ApiError, ApiResponse
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
        except Exception: ok=False
        self.stats.leader=ok
        return ok

    @staticmethod
    def _status_from_plan(plan: dict) -> dict:
        return {k:v for k,v in plan.items() if k in {"phase","observed_generation","canary_wave","conditions"}}

    @staticmethod
    def _response_meta(response: ApiResponse | None, expected_name: str="") -> dict | None:
        if response is None or not isinstance(response.body,dict): return None
        meta=response.body.get("metadata")
        if not isinstance(meta,dict): return None
        rv=meta.get("resourceVersion")
        if not isinstance(rv,str) or not rv.strip(): return None
        if expected_name:
            name=meta.get("name")
            if name is not None and name != expected_name: return None
        return meta

    def _event(self, obj: dict, reason: str, note: str) -> bool:
        meta=obj.get("metadata",{}); name=meta.get("name",""); uid=meta.get("uid","")
        if not name or not uid or self.stats.terminating or not self._leader(): return False
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
        event={"apiVersion":"events.k8s.io/v1","kind":"Event","metadata":{"generateName":f"nvlx-{name}-","namespace":self.namespace},"eventTime":now,"reportingController":"nvlx.io/operator","reportingInstance":self.identity,"action":"Reconcile","reason":reason,"note":note[:1024],"type":"Normal","regarding":{"apiVersion":"nvlx.io/v1alpha1","kind":"GPUFleet","name":name,"uid":uid}}
        try:
            response=self.client.create_event(self.namespace,event)
            return self._response_meta(response) is not None
        except ApiError: return False

    def _patch_status(self, obj: dict, status: dict) -> bool:
        meta=obj.get("metadata",{}); name=meta.get("name",""); rv=meta.get("resourceVersion","")
        for _ in range(2):
            if not self._leader(): return False
            try:
                response=self.client.patch_status(name,rv,status)
                return self._response_meta(response,name) is not None
            except ApiError as e:
                if e.status not in {409,412}: raise
                if not self._leader(): return False
                fresh=self.client.get_fleet(name).body
                if not isinstance(fresh,dict): return False
                fresh_meta=fresh.get("metadata")
                if not isinstance(fresh_meta,dict): return False
                rv=fresh_meta.get("resourceVersion","")
                if not isinstance(rv,str) or not rv: return False
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
            response=self.client.patch_finalizers(meta.get("name",""),meta.get("resourceVersion",""),remaining)
            return self._response_meta(response,meta.get("name","")) is not None
        except ApiError as e:
            if e.status in {409,412,404,410}: return False
            raise

    def reconcile_object(self, obj: dict, *, event_type: str="MODIFIED") -> str:
        self.stats.reconcile_total += 1
        if not isinstance(obj,dict): self.stats.reconcile_failures += 1; return "invalid"
        meta=obj.get("metadata")
        if not isinstance(meta,dict): self.stats.reconcile_failures += 1; return "invalid"
        name=meta.get("name",""); rv=meta.get("resourceVersion","")
        if not isinstance(name,str) or not name or not isinstance(rv,str) or not rv: self.stats.reconcile_failures += 1; return "invalid"
        try: generation=int(meta.get("generation",0) or 0)
        except (TypeError,ValueError): self.stats.reconcile_failures += 1; return "invalid"
        if generation < 0: self.stats.reconcile_failures += 1; return "invalid"
        self.stats.last_resource_version=rv
        if meta.get("deletionTimestamp"):
            return "finalized" if self._finalize(obj) else "finalizer-hold"
        if not self._leader(): return "standby"
        annotations=meta.get("annotations") or {}
        allowed=isinstance(annotations,dict) and annotations.get("nvlx.io/approved")=="true"
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
        body=listing.body
        if not isinstance(body,dict): raise RuntimeError("GPUFleet list body must be an object")
        metadata=body.get("metadata")
        if not isinstance(metadata,dict): raise RuntimeError("GPUFleet list metadata must be an object")
        rv=metadata.get("resourceVersion","")
        if not isinstance(rv,str) or not rv: raise RuntimeError("GPUFleet list did not return resourceVersion")
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
                        bookmark_meta=obj.get("metadata")
                        if isinstance(bookmark_meta,dict):
                            bookmark_rv=bookmark_meta.get("resourceVersion")
                            if isinstance(bookmark_rv,str) and bookmark_rv: self.stats.last_resource_version=bookmark_rv
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
