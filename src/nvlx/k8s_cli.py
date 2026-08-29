"""Kubernetes-native nvlx control-plane CLI."""
from __future__ import annotations
import argparse, json
from .fleet_crd import FleetSpec, crd_manifest, resource
from .finalizer import decide as finalizer_decide
from .admission_v14 import render as admission_render
from .reconcile_v14 import reconcile
from .operator_v15 import plan as operator_plan
from .workqueue_v15 import retry as queue_retry
from .owner_v15 import validate as owner_validate
from .healthz_v15 import evaluate as health_evaluate

def _json(v): print(json.dumps(v,indent=2,sort_keys=True))
def main(argv=None):
 p=argparse.ArgumentParser(prog="nvlx-k8s",description="nvlx 1.5 live Kubernetes GPUFleet operator"); s=p.add_subparsers(dest="cmd",required=True)
 s.add_parser("crd")
 q=s.add_parser("fleet"); q.add_argument("name"); q.add_argument("--driver-version",required=True); q.add_argument("--gpu-operator-version",required=True); q.add_argument("--allocation-mode",choices=["dra","device-plugin"],default="dra"); q.add_argument("--canary-waves",type=int,default=3)
 q=s.add_parser("finalize-check"); q.add_argument("--deleting",action="store_true"); q.add_argument("--rollback-pending",action="store_true"); q.add_argument("--quarantined",type=int,default=0); q.add_argument("--active-execution",action="store_true")
 s.add_parser("admission-policy")
 q=s.add_parser("reconcile"); q.add_argument("name"); q.add_argument("--generation",type=int,required=True); q.add_argument("--allowed",action="store_true"); q.add_argument("--runtime-action",default="hold"); q.add_argument("--reason",action="append",default=[]); q.add_argument("--current-wave",type=int,default=0); q.add_argument("--promoted",action="store_true")
 q=s.add_parser("operator-plan"); q.add_argument("name"); q.add_argument("--event-type",required=True); q.add_argument("--resource-version",default=""); q.add_argument("--generation",type=int,required=True); q.add_argument("--allowed",action="store_true"); q.add_argument("--runtime-action",default="hold"); q.add_argument("--reason",action="append",default=[]); q.add_argument("--current-wave",type=int,default=0); q.add_argument("--promoted",action="store_true"); q.add_argument("--attempt",type=int,default=0); q.add_argument("--expired",action="store_true")
 q=s.add_parser("queue-retry"); q.add_argument("attempt",type=int)
 q=s.add_parser("ownership-check"); q.add_argument("path",nargs="+")
 q=s.add_parser("health"); q.add_argument("--api-reachable",action="store_true"); q.add_argument("--leader",action="store_true"); q.add_argument("--inventory-fresh",action="store_true")
 a=p.parse_args(argv)
 if a.cmd=="crd": _json(crd_manifest()); return 0
 if a.cmd=="fleet": _json(resource(a.name,FleetSpec(a.driver_version,a.gpu_operator_version,a.allocation_mode,a.canary_waves))); return 0
 if a.cmd=="finalize-check": r=finalizer_decide(deleting=a.deleting,rollback_pending=a.rollback_pending,quarantined_nodes=a.quarantined,active_execution=a.active_execution); _json(r.to_dict()); return 0 if r.action!="hold" else 2
 if a.cmd=="admission-policy": print(admission_render(),end=""); return 0
 if a.cmd=="reconcile": r=reconcile(a.name,generation=a.generation,allowed=a.allowed,runtime_action=a.runtime_action,runtime_reasons=tuple(a.reason),current_wave=a.current_wave,promoted=a.promoted); _json(r.to_dict()); return 0 if r.phase!="Blocked" else 2
 if a.cmd=="operator-plan": r=operator_plan(a.name,event_type=a.event_type,resource_version=a.resource_version,generation=a.generation,allowed=a.allowed,runtime_action=a.runtime_action,reasons=tuple(a.reason),current_wave=a.current_wave,promoted=a.promoted,attempt=a.attempt,expired=a.expired); _json(r.to_dict()); return 0 if r.action not in {"hold"} else 2
 if a.cmd=="queue-retry": _json(queue_retry(a.attempt).to_dict()); return 0
 if a.cmd=="ownership-check": ok,denied=owner_validate(a.path); _json({"allowed":ok,"denied":denied}); return 0 if ok else 2
 if a.cmd=="health": r=health_evaluate(api_reachable=a.api_reachable,leader=a.leader,inventory_fresh=a.inventory_fresh); _json(r.to_dict()); return 0 if r.ready else 2
 return 2
if __name__=="__main__": raise SystemExit(main())
