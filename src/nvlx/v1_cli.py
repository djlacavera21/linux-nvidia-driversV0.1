"""nvlx-controller stable production command surface."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from .config_v1 import validate as config_validate
from .v1_compat import check as compat_check
from .controller import plan as reconcile_plan
from .approvals import ExecutionPlan, Approval, approve, execution_allowed
from .controller_state import new_state, transition
from .ha import plan as ha_plan, kubernetes_manifest
from .bundle import build as bundle_build, cosign_verify_blob_plan
from .approval_lifecycle import evaluate as approval_evaluate
from .state_migration import migrate as state_migrate
from .runtime import tick as runtime_tick
from .controller_metrics import render as metrics_render
from .execution_record import start as execution_start, finish as execution_finish
from .k8s_controller import render_json as k8s_render
from .audit_chain import append as audit_append, verify as audit_verify
from .change_window import ChangeWindow
from .preflight_snapshot import PreflightSnapshot, capture as preflight_capture
from .runtime_v13 import decide as runtime_decide
from .runtime_store import load as runtime_load, save as runtime_save, record_success, record_failure
from .canary import evaluate as canary_evaluate
from .rollback_orchestrator import plan as rollback_orchestrate
from .maintenance_policy import render as maintenance_render
from .idempotency import key as idempotency_key

def _json(v): print(json.dumps(v,indent=2,sort_keys=True))
def _read(path): return json.loads(Path(path).read_text())
def _plan(path):
    d=_read(path); d=d.get("plan",d)
    return ExecutionPlan(d["operation"],d["target"],tuple(d["steps"]),d["config_fingerprint"],d["fingerprint"])

def main(argv=None):
    p=argparse.ArgumentParser(prog="nvlx-controller",description="nvlx 1.3 production reconciliation and operations controller")
    s=p.add_subparsers(dest="cmd",required=True)
    q=s.add_parser("config-validate"); q.add_argument("config")
    q=s.add_parser("compat"); q.add_argument("--kubernetes-version",required=True); q.add_argument("--gpucluster",action="store_true"); q.add_argument("--clusterpolicy",action="store_true"); q.add_argument("--computedomains-crd-ready",action="store_true"); q.add_argument("--migrate-clusterpolicy-to-gpucluster",action="store_true")
    q=s.add_parser("reconcile-plan"); q.add_argument("config"); q.add_argument("--kubernetes-version",required=True); q.add_argument("--gpucluster",action="store_true"); q.add_argument("--clusterpolicy",action="store_true"); q.add_argument("--computedomains-crd-ready",action="store_true"); q.add_argument("--operation",required=True); q.add_argument("--target",required=True); q.add_argument("--step",action="append",required=True)
    q=s.add_parser("approve"); q.add_argument("plan"); q.add_argument("--by",required=True)
    q=s.add_parser("execute-check"); q.add_argument("plan"); q.add_argument("approval")
    q=s.add_parser("approval-status"); q.add_argument("plan"); q.add_argument("approval"); q.add_argument("--ttl-seconds",type=int,default=1800); q.add_argument("--revoked",action="store_true")
    q=s.add_parser("state-demo"); q.add_argument("config_fingerprint"); q.add_argument("--plan-fingerprint")
    q=s.add_parser("state-migrate"); q.add_argument("state")
    q=s.add_parser("runtime-tick"); q.add_argument("--observed-generation",type=int,required=True); q.add_argument("--desired-generation",type=int,required=True); q.add_argument("--leader",action="store_true"); q.add_argument("--blocked",action="store_true")
    q=s.add_parser("runtime-evaluate"); q.add_argument("current_facts"); q.add_argument("--leader",action="store_true"); q.add_argument("--approval-valid",action="store_true"); q.add_argument("--start-hour",type=int,default=0); q.add_argument("--end-hour",type=int,default=23); q.add_argument("--emergency-override",action="store_true"); q.add_argument("--execution-key",required=True); q.add_argument("--completed-key",action="append",default=[]); q.add_argument("--total-nodes",type=int,required=True); q.add_argument("--unavailable",type=int,default=0); q.add_argument("--failures",type=int,default=0); q.add_argument("--security-failure",action="store_true")
    q=s.add_parser("runtime-state"); q.add_argument("path"); q.add_argument("--record-success"); q.add_argument("--generation",type=int,default=0); q.add_argument("--record-failure",action="store_true")
    q=s.add_parser("idempotency-key"); q.add_argument("plan_fingerprint"); q.add_argument("target"); q.add_argument("generation",type=int)
    q=s.add_parser("canary-check"); q.add_argument("--current-wave",type=int,required=True); q.add_argument("--total-waves",type=int,required=True); q.add_argument("--healthy-fraction",type=float,required=True); q.add_argument("--min-healthy-fraction",type=float,default=.99); q.add_argument("--diagnostics-passed",action="store_true"); q.add_argument("--security-passed",action="store_true"); q.add_argument("--quarantined",type=int,default=0); q.add_argument("--circuit-open",action="store_true")
    q=s.add_parser("rollback-plan"); q.add_argument("--rollback-available",action="store_true"); q.add_argument("--security-failure",action="store_true"); q.add_argument("--state-uncertain",action="store_true"); q.add_argument("--failure-count",type=int,default=1)
    q=s.add_parser("maintenance-policy"); q.add_argument("--namespace",default="nvlx-system"); q.add_argument("--name",default="nvlx-maintenance-policy"); q.add_argument("--start-hour",type=int,default=2); q.add_argument("--end-hour",type=int,default=5); q.add_argument("--emergency-override",action="store_true")
    q=s.add_parser("metrics"); q.add_argument("--leader",action="store_true"); q.add_argument("--reconcile-total",type=int,default=0); q.add_argument("--reconcile-failures",type=int,default=0); q.add_argument("--pending-approvals",type=int,default=0); q.add_argument("--rollback-required",type=int,default=0); q.add_argument("--circuit-open",action="store_true"); q.add_argument("--rollout-slots",type=int,default=0); q.add_argument("--completed-executions",type=int,default=0); q.add_argument("--preflight-stale",type=int,default=0); q.add_argument("--canary-wave",type=int,default=0)
    q=s.add_parser("execution-record"); q.add_argument("plan_fingerprint"); q.add_argument("--fail",action="store_true"); q.add_argument("--message")
    q=s.add_parser("k8s-manifests"); q.add_argument("--namespace",default="nvlx-system"); q.add_argument("--image",default="ghcr.io/nvlx/controller:1.3.0"); q.add_argument("--replicas",type=int,default=2)
    q=s.add_parser("ha-plan"); q.add_argument("--namespace",default="nvlx-system"); q.add_argument("--name",default="nvlx-controller"); q.add_argument("--holder",default="controller-0"); q.add_argument("--lease",type=int,default=30); q.add_argument("--renew",type=int,default=20); q.add_argument("--retry",type=int,default=5)
    q=s.add_parser("bundle-manifest"); q.add_argument("root"); q.add_argument("paths",nargs="+")
    q=s.add_parser("cosign-plan"); q.add_argument("manifest"); q.add_argument("signature"); q.add_argument("--identity",required=True)
    a=p.parse_args(argv)
    if a.cmd=="config-validate": r=config_validate(_read(a.config)); _json(r.to_dict()); return 0 if r.valid else 2
    if a.cmd=="compat": r=compat_check(kubernetes_version=a.kubernetes_version,has_gpucluster=a.gpucluster,has_clusterpolicy=a.clusterpolicy,computedomains_crd_ready=a.computedomains_crd_ready,migrating_clusterpolicy_to_gpucluster=a.migrate_clusterpolicy_to_gpucluster); _json(r.to_dict()); return 0 if r.compatible else 2
    if a.cmd=="reconcile-plan": c=config_validate(_read(a.config)); x=compat_check(kubernetes_version=a.kubernetes_version,has_gpucluster=a.gpucluster,has_clusterpolicy=a.clusterpolicy,computedomains_crd_ready=a.computedomains_crd_ready); r=reconcile_plan(c,x,operation=a.operation,target=a.target,steps=a.step); _json(r.to_dict()); return 0 if r.allowed else 2
    if a.cmd=="approve": r=approve(_plan(a.plan),a.by); _json(r.to_dict()); return 0
    if a.cmd in {"execute-check","approval-status"}:
        ep=_plan(a.plan); ap=Approval(**_read(a.approval))
        if a.cmd=="execute-check": ok,reasons=execution_allowed(ep,ap); _json({"allowed":ok,"reasons":reasons}); return 0 if ok else 2
        r=approval_evaluate(ep,ap,ttl_seconds=a.ttl_seconds,revoked=a.revoked); _json(r.to_dict()); return 0 if r.allowed else 2
    if a.cmd=="state-demo": st=new_state(a.config_fingerprint); out=[st.to_dict()]; st=transition(st,"planned",plan_fingerprint=a.plan_fingerprint or "demo"); out.append(st.to_dict()); st=transition(st,"awaiting-approval"); out.append(st.to_dict()); _json(out); return 0
    if a.cmd=="state-migrate": r=state_migrate(_read(a.state)); _json(r.to_dict()); return 0
    if a.cmd=="runtime-tick": r=runtime_tick(observed_generation=a.observed_generation,desired_generation=a.desired_generation,leader=a.leader,blocked=a.blocked); _json(r.to_dict()); return 0 if r.action != "hold" else 2
    if a.cmd=="runtime-evaluate":
        facts=_read(a.current_facts); snap=preflight_capture(facts); window=ChangeWindow(a.start_hour,a.end_hour,a.emergency_override); r=runtime_decide(leader=a.leader,approval_valid=a.approval_valid,window=window,preflight=snap,current_facts=facts,execution_key=a.execution_key,completed_keys=a.completed_key,total_nodes=a.total_nodes,currently_unavailable=a.unavailable,failure_count=a.failures,security_failure=a.security_failure); _json(r.to_dict()); return 0 if r.allowed else 2
    if a.cmd=="runtime-state":
        path=Path(a.path); st=runtime_load(path)
        if a.record_failure: st=record_failure(st); runtime_save(path,st)
        if a.record_success: st=record_success(st,a.record_success,a.generation); runtime_save(path,st)
        _json(st.to_dict()); return 0
    if a.cmd=="idempotency-key": print(idempotency_key(a.plan_fingerprint,a.target,a.generation)); return 0
    if a.cmd=="canary-check": r=canary_evaluate(current_wave=a.current_wave,total_waves=a.total_waves,healthy_fraction=a.healthy_fraction,min_healthy_fraction=a.min_healthy_fraction,diagnostics_passed=a.diagnostics_passed,security_passed=a.security_passed,quarantined=a.quarantined,circuit_open=a.circuit_open); _json(r.to_dict()); return 0 if r.promote else 2
    if a.cmd=="rollback-plan": r=rollback_orchestrate(rollback_available=a.rollback_available,security_failure=a.security_failure,state_uncertain=a.state_uncertain,failure_count=a.failure_count); _json(r.to_dict()); return 0 if r.action=="rollback" else 2
    if a.cmd=="maintenance-policy": print(maintenance_render(namespace=a.namespace,name=a.name,start_hour_utc=a.start_hour,end_hour_utc=a.end_hour,emergency_override=a.emergency_override),end=""); return 0
    if a.cmd=="metrics": print(metrics_render(leader=a.leader,reconcile_total=a.reconcile_total,reconcile_failures=a.reconcile_failures,pending_approvals=a.pending_approvals,rollback_required=a.rollback_required,circuit_open=a.circuit_open,rollout_slots=a.rollout_slots,completed_executions=a.completed_executions,preflight_stale=a.preflight_stale,canary_wave=a.canary_wave),end=""); return 0
    if a.cmd=="execution-record": r=execution_finish(execution_start(a.plan_fingerprint),success=not a.fail,message=a.message); _json(r.to_dict()); return 0 if not r.rollback_required else 2
    if a.cmd=="k8s-manifests": print(k8s_render(namespace=a.namespace,image=a.image,replicas=a.replicas),end=""); return 0
    if a.cmd=="ha-plan": r=ha_plan(a.namespace,a.name,a.holder,a.lease,a.renew,a.retry); _json({"plan":r.to_dict(),"lease_manifest":kubernetes_manifest(r) if r.valid else None}); return 0 if r.valid else 2
    if a.cmd=="bundle-manifest": _json(bundle_build(Path(a.root),a.paths).to_dict()); return 0
    if a.cmd=="cosign-plan": _json(cosign_verify_blob_plan(a.manifest,a.signature,a.identity)); return 0
    return 2

if __name__=="__main__": raise SystemExit(main())
