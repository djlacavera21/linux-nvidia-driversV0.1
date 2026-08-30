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
WATCH_CACHE_DEFAULT_LIMIT=4096
_LIST_SETTLED_RESULTS={"patched","status-noop","event-noop","checkpoint","finalized","deleted-observed","observe-delete"}

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
    duplicate_watch_events: int=0
    stale_generation_events: int=0
    relist_seeded_objects: int=0
    deleted_watch_events: int=0
    watch_cache_pruned: int=0
    watch_cache_evictions: int=0
    relist_deferred_objects: int=0
    status_conflict_recomputes: int=0
    status_conflict_fenced: int=0
    finalizer_conflict_recomputes: int=0
    finalizer_conflict_fenced: int=0

@dataclass
class Runtime:
    client: KubeClient
    identity: str
    namespace: str="nvlx-system"
    leader_check: callable=lambda: True
    stats: RuntimeStats=field(default_factory=RuntimeStats)
    watch_cache_limit: int=WATCH_CACHE_DEFAULT_LIMIT
    _stop: threading.Event=field(default_factory=threading.Event)
    _watch_seen: dict[str, tuple[str,str,int,str]]=field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.watch_cache_limit,bool) or not isinstance(self.watch_cache_limit,int) or self.watch_cache_limit <= 0:
            raise ValueError("watch_cache_limit must be a positive integer")

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
        if expected_name and meta.get("name") != expected_name: return None
        return meta

    @staticmethod
    def _object_identity_valid(obj: object) -> bool:
        if not isinstance(obj,dict): return False
        meta=obj.get("metadata")
        if not isinstance(meta,dict): return False
        name=meta.get("name"); uid=meta.get("uid"); rv=meta.get("resourceVersion")
        if not isinstance(name,str) or not name.strip(): return False
        if not isinstance(uid,str) or not uid.strip(): return False
        if not isinstance(rv,str) or not rv.strip(): return False
        generation=meta.get("generation",0)
        try: return int(generation or 0) >= 0
        except (TypeError,ValueError): return False

    @staticmethod
    def _watch_key(obj: dict) -> tuple[str,str,int,str]:
        meta=obj["metadata"]
        name=meta["name"]
        uid=meta["uid"]
        generation=int(meta.get("generation",0) or 0)
        rv=meta["resourceVersion"]
        return (name,uid,generation,rv)

    @staticmethod
    def _watch_cache_key(name: str, uid: str) -> str:
        return uid

    def _remember_watch_state(self, key: str, fingerprint: tuple[str,str,int,str]) -> None:
        if key not in self._watch_seen and len(self._watch_seen) >= self.watch_cache_limit:
            oldest=next(iter(self._watch_seen),None)
            if oldest is not None:
                self._watch_seen.pop(oldest,None)
                self.stats.watch_cache_evictions += 1
        self._watch_seen[key]=fingerprint

    def _prune_watch_state_from_list(self, items: list[dict]) -> None:
        present=set()
        for item in items:
            name,uid,_generation,_rv=self._watch_key(item)
            present.add(self._watch_cache_key(name,uid))
        stale=[key for key in self._watch_seen if key not in present]
        for key in stale:
            self._watch_seen.pop(key,None)
        self.stats.watch_cache_pruned += len(stale)

    def _seed_watch_state_from_list(self, items: list[dict]) -> None:
        for item in items:
            name,uid,generation,rv=self._watch_key(item)
            key=self._watch_cache_key(name,uid)
            self._remember_watch_state(key,("LIST",uid,generation,rv))
            self.stats.relist_seeded_objects += 1

    def _watch_event_disposition(self, obj: object, event_type: str) -> str:
        """Classify watch delivery without ordering opaque resourceVersion values."""
        if not self._object_identity_valid(obj): return "invalid"
        name,uid,generation,rv=self._watch_key(obj)
        key=self._watch_cache_key(name,uid)
        previous=self._watch_seen.get(key)
        if previous is not None:
            prev_type,prev_uid,prev_generation,prev_rv=previous
            same_state=(prev_uid==uid and prev_generation==generation and prev_rv==rv)
            if same_state:
                if event_type=="DELETED" and prev_type!="DELETED":
                    self._remember_watch_state(key,(event_type,uid,generation,rv))
                    self.stats.deleted_watch_events += 1
                    return "reconcile-delete"
                if event_type==prev_type or (event_type in {"ADDED","MODIFIED"} and prev_type in {"LIST","ADDED","MODIFIED"}):
                    self.stats.duplicate_watch_events += 1
                    return "duplicate"
            if prev_uid==uid and generation < prev_generation:
                self.stats.stale_generation_events += 1
                return "stale-generation"
        self._remember_watch_state(key,(event_type,uid,generation,rv))
        if event_type=="DELETED":
            self.stats.deleted_watch_events += 1
            return "reconcile-delete"
        return "reconcile"

    @classmethod
    def _status_response_verified(cls, response: ApiResponse | None, expected_meta: dict, expected_status: dict) -> bool:
        expected_name=expected_meta.get("name","")
        expected_uid=expected_meta.get("uid","")
        if not isinstance(expected_name,str) or not expected_name or not isinstance(expected_uid,str) or not expected_uid: return False
        meta=cls._response_meta(response,expected_name)
        if meta is None or not isinstance(response.body,dict): return False
        if meta.get("uid") != expected_uid: return False
        expected_generation=expected_meta.get("generation")
        if expected_generation is not None and "generation" in meta:
            try:
                if int(meta.get("generation")) != int(expected_generation): return False
            except (TypeError,ValueError): return False
        returned=response.body.get("status")
        if not isinstance(returned,dict): return False
        for key,value in expected_status.items():
            if returned.get(key) != value: return False
        return True

    @classmethod
    def _finalizer_response_verified(cls, response: ApiResponse | None, expected_name: str, expected_finalizers: list[str], expected_uid: str="") -> bool:
        meta=cls._response_meta(response,expected_name)
        if meta is None: return False
        if expected_uid and meta.get("uid") != expected_uid: return False
        finalizers=meta.get("finalizers")
        if not isinstance(finalizers,list) or not all(isinstance(x,str) for x in finalizers): return False
        if PROTECTIVE_FINALIZER in finalizers: return False
        return finalizers == expected_finalizers

    @classmethod
    def _event_response_verified(cls, response: ApiResponse | None, expected_name: str, expected_uid: str, expected_identity: str) -> bool:
        if cls._response_meta(response) is None or not isinstance(response.body,dict): return False
        regarding=response.body.get("regarding")
        if not isinstance(regarding,dict): return False
        if regarding.get("name") != expected_name or regarding.get("uid") != expected_uid: return False
        if response.body.get("reportingController") != "nvlx.io/operator": return False
        if response.body.get("reportingInstance") != expected_identity: return False
        return True

    @staticmethod
    def _same_incarnation(fresh: object, original_meta: dict) -> bool:
        if not Runtime._object_identity_valid(fresh): return False
        meta=fresh["metadata"]
        return meta.get("name")==original_meta.get("name") and meta.get("uid")==original_meta.get("uid")

    @staticmethod
    def _approval_allowed(obj: dict) -> bool:
        meta=obj.get("metadata") or {}
        annotations=meta.get("annotations") or {}
        return isinstance(annotations,dict) and annotations.get("nvlx.io/approved")=="true"

    def _status_plan(self, obj: dict, event_type: str) -> tuple[str,dict|None,bool]:
        if not self._object_identity_valid(obj): return "invalid",None,False
        meta=obj["metadata"]
        if meta.get("deletionTimestamp"): return "deleting",None,self._approval_allowed(obj)
        name=meta["name"]; rv=meta["resourceVersion"]; generation=int(meta.get("generation",0) or 0)
        allowed=self._approval_allowed(obj)
        p=operator_plan(name,event_type=event_type,resource_version=rv,generation=generation,allowed=allowed,runtime_action="execute" if allowed else "hold",mutation_fence_ok=True)
        status=self._status_from_plan(p.reconcile) if p.action=="patch-status" and p.reconcile else None
        return p.action,status,allowed

    def _event(self, obj: dict, reason: str, note: str) -> bool:
        meta=obj.get("metadata",{}); name=meta.get("name",""); uid=meta.get("uid","")
        if not name or not uid or self.stats.terminating or not self._leader(): return False
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
        event={"apiVersion":"events.k8s.io/v1","kind":"Event","metadata":{"generateName":f"nvlx-{name}-","namespace":self.namespace},"eventTime":now,"reportingController":"nvlx.io/operator","reportingInstance":self.identity,"action":"Reconcile","reason":reason,"note":note[:1024],"type":"Normal","regarding":{"apiVersion":"nvlx.io/v1alpha1","kind":"GPUFleet","name":name,"uid":uid}}
        try:
            response=self.client.create_event(self.namespace,event)
            return self._event_response_verified(response,name,uid,self.identity)
        except ApiError: return False

    def _patch_status_result(self, obj: dict, status: dict, *, event_type: str="MODIFIED") -> tuple[bool,dict,dict]:
        meta=obj.get("metadata",{}); name=meta.get("name",""); rv=meta.get("resourceVersion","")
        original_allowed=self._approval_allowed(obj)
        if not self._leader(): return False,obj,status
        try:
            response=self.client.patch_status(name,rv,status)
            return self._status_response_verified(response,meta,status),obj,status
        except ApiError as e:
            if e.status not in {409,412}: raise
        if not self._leader(): return False,obj,status
        try:
            response=self.client.get_fleet(name)
        except ApiError:
            self.stats.status_conflict_fenced += 1
            return False,obj,status
        fresh=response.body if response is not None else None
        if not self._same_incarnation(fresh,meta):
            self.stats.status_conflict_fenced += 1
            return False,obj,status
        if fresh["metadata"].get("deletionTimestamp"):
            self.stats.status_conflict_fenced += 1
            return False,obj,status
        if self._approval_allowed(fresh) != original_allowed:
            self.stats.status_conflict_fenced += 1
            return False,obj,status
        action,recomputed,_allowed=self._status_plan(fresh,event_type)
        if action!="patch-status" or recomputed is None:
            self.stats.status_conflict_fenced += 1
            return False,obj,status
        self.stats.status_conflict_recomputes += 1
        if not self._leader():
            self.stats.status_conflict_fenced += 1
            return False,obj,status
        fresh_meta=fresh["metadata"]
        try:
            retry=self.client.patch_status(fresh_meta["name"],fresh_meta["resourceVersion"],recomputed)
        except ApiError:
            self.stats.status_conflict_fenced += 1
            return False,obj,status
        ok=self._status_response_verified(retry,fresh_meta,recomputed)
        if not ok: self.stats.status_conflict_fenced += 1
        return ok,fresh,recomputed

    def _patch_status(self, obj: dict, status: dict, *, event_type: str="MODIFIED") -> bool:
        ok,_fresh,_status=self._patch_status_result(obj,status,event_type=event_type)
        return ok

    @staticmethod
    def _finalizer_plan(obj: dict) -> tuple[bool,bool,list[str]]:
        if not Runtime._object_identity_valid(obj): return False,False,[]
        meta=obj["metadata"]
        finalizers=meta.get("finalizers") or []
        if not isinstance(finalizers,list) or not all(isinstance(x,str) for x in finalizers): return False,False,[]
        if PROTECTIVE_FINALIZER not in finalizers: return True,True,finalizers
        if not meta.get("deletionTimestamp"): return False,False,[]
        annotations=meta.get("annotations") or {}
        status=obj.get("status") or {}
        if not isinstance(annotations,dict) or not isinstance(status,dict): return False,False,[]
        try: quarantined=int(status.get("quarantined_nodes",0) or 0)
        except (TypeError,ValueError): return False,False,[]
        decision=finalizer_decide(deleting=True,rollback_pending=annotations.get("nvlx.io/rollback-pending")=="true",quarantined_nodes=quarantined,active_execution=annotations.get("nvlx.io/active-execution")=="true",status_write_pending=False)
        if not decision.remove_finalizer: return False,False,[]
        remaining=[x for x in finalizers if x != PROTECTIVE_FINALIZER]
        return True,False,remaining

    def _finalize(self, obj: dict) -> bool:
        allowed,already_done,remaining=self._finalizer_plan(obj)
        if already_done: return True
        if not allowed or not self._leader(): return False
        meta=obj["metadata"]
        try:
            response=self.client.patch_finalizers(meta["name"],meta["resourceVersion"],remaining)
            return self._finalizer_response_verified(response,meta["name"],remaining,meta["uid"])
        except ApiError as e:
            if e.status not in {409,412}: return False if e.status in {404,410} else (_ for _ in ()).throw(e)
        if not self._leader(): return False
        try:
            response=self.client.get_fleet(meta["name"])
        except ApiError:
            self.stats.finalizer_conflict_fenced += 1
            return False
        fresh=response.body if response is not None else None
        if not self._same_incarnation(fresh,meta):
            self.stats.finalizer_conflict_fenced += 1
            return False
        allowed,already_done,remaining=self._finalizer_plan(fresh)
        if already_done: return True
        if not allowed:
            self.stats.finalizer_conflict_fenced += 1
            return False
        self.stats.finalizer_conflict_recomputes += 1
        if not self._leader():
            self.stats.finalizer_conflict_fenced += 1
            return False
        fresh_meta=fresh["metadata"]
        try:
            retry=self.client.patch_finalizers(fresh_meta["name"],fresh_meta["resourceVersion"],remaining)
        except ApiError:
            self.stats.finalizer_conflict_fenced += 1
            return False
        ok=self._finalizer_response_verified(retry,fresh_meta["name"],remaining,fresh_meta["uid"])
        if not ok: self.stats.finalizer_conflict_fenced += 1
        return ok

    def reconcile_object(self, obj: dict, *, event_type: str="MODIFIED") -> str:
        self.stats.reconcile_total += 1
        if not self._object_identity_valid(obj): self.stats.reconcile_failures += 1; return "invalid"
        meta=obj["metadata"]; rv=meta["resourceVersion"]
        self.stats.last_resource_version=rv
        if event_type=="DELETED" and not meta.get("deletionTimestamp"):
            return "deleted-observed"
        if meta.get("deletionTimestamp"):
            return "finalized" if self._finalize(obj) else "finalizer-hold"
        if not self._leader(): return "standby"
        action,status,_allowed=self._status_plan(obj,event_type)
        if action=="patch-status" and status is not None:
            ok,applied_obj,applied_status=self._patch_status_result(obj,status,event_type=event_type)
            if ok:
                self._event(applied_obj,"Reconciled",f"GPUFleet status advanced to {applied_status.get('phase','Unknown')}")
                return "patched"
            return "fenced"
        return action

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
        if not all(self._object_identity_valid(item) for item in items):
            self.stats.inventory_fresh=False
            raise RuntimeError("GPUFleet list contains invalid object identity")
        self._prune_watch_state_from_list(items)
        settled=[]
        for item in items:
            if self._stop.is_set(): return "stopped"
            result=self.reconcile_object(item,event_type="ADDED")
            if result in _LIST_SETTLED_RESULTS:
                settled.append(item)
            else:
                self.stats.relist_deferred_objects += 1
        self._seed_watch_state_from_list(settled)
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
                event_type=decision.action.upper()
                disposition=self._watch_event_disposition(obj,event_type)
                if disposition=="invalid":
                    self.stats.reconcile_failures += 1
                    continue
                if disposition=="duplicate": continue
                if disposition=="stale-generation":
                    self.stats.reconcile_failures += 1
                    continue
                self.reconcile_object(obj,event_type=event_type)
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
