"""Kubernetes-native nvlx control-plane manifest and reconciliation CLI."""
from __future__ import annotations
import argparse, json
from .fleet_crd import FleetSpec, crd_manifest, resource
from .status_conditions import summarize
from .finalizer import decide as finalizer_decide
from .k8s_events import event
from .admission_v14 import render as admission_render
from .reconcile_v14 import reconcile

def _json(v): print(json.dumps(v,indent=2,sort_keys=True))

def main(argv=None):
    p=argparse.ArgumentParser(prog="nvlx-k8s",description="nvlx 1.4 Kubernetes-native GPUFleet control plane")
    s=p.add_subparsers(dest="cmd",required=True)
    s.add_parser("crd")
    q=s.add_parser("fleet"); q.add_argument("name"); q.add_argument("--driver-version",required=True); q.add_argument("--gpu-operator-version",required=True); q.add_argument("--allocation-mode",choices=["dra","device-plugin"],default="dra"); q.add_argument("--canary-waves",type=int,default=3)
    q=s.add_parser("conditions"); q.add_argument("--generation",type=int,required=True); q.add_argument("--ready",action="store_true"); q.add_argument("--progressing",action="store_true"); q.add_argument("--degraded",action="store_true"); q.add_argument("--message",default="")
    q=s.add_parser("finalize-check"); q.add_argument("--deleting",action="store_true"); q.add_argument("--rollback-pending",action="store_true"); q.add_argument("--quarantined",type=int,default=0); q.add_argument("--active-execution",action="store_true")
    q=s.add_parser("event"); q.add_argument("name"); q.add_argument("--reason",required=True); q.add_argument("--note",required=True); q.add_argument("--warning",action="store_true")
    s.add_parser("admission-policy")
    q=s.add_parser("reconcile"); q.add_argument("name"); q.add_argument("--generation",type=int,required=True); q.add_argument("--allowed",action="store_true"); q.add_argument("--runtime-action",default="hold"); q.add_argument("--reason",action="append",default=[]); q.add_argument("--current-wave",type=int,default=0); q.add_argument("--promoted",action="store_true")
    a=p.parse_args(argv)
    if a.cmd=="crd": _json(crd_manifest()); return 0
    if a.cmd=="fleet": _json(resource(a.name,FleetSpec(a.driver_version,a.gpu_operator_version,a.allocation_mode,a.canary_waves))); return 0
    if a.cmd=="conditions": _json(summarize(ready=a.ready,progressing=a.progressing,degraded=a.degraded,generation=a.generation,message=a.message)); return 0
    if a.cmd=="finalize-check": r=finalizer_decide(deleting=a.deleting,rollback_pending=a.rollback_pending,quarantined_nodes=a.quarantined,active_execution=a.active_execution); _json(r.to_dict()); return 0 if r.action != "hold" else 2
    if a.cmd=="event": _json(event(a.name,reason=a.reason,note=a.note,warning=a.warning)); return 0
    if a.cmd=="admission-policy": print(admission_render(),end=""); return 0
    if a.cmd=="reconcile": r=reconcile(a.name,generation=a.generation,allowed=a.allowed,runtime_action=a.runtime_action,runtime_reasons=tuple(a.reason),current_wave=a.current_wave,promoted=a.promoted); _json(r.to_dict()); return 0 if r.phase != "Blocked" else 2
    return 2

if __name__=="__main__": raise SystemExit(main())
