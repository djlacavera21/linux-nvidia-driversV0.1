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

def _json(v): print(json.dumps(v,indent=2,sort_keys=True))
def _read(path): return json.loads(Path(path).read_text())

def main(argv=None):
    p=argparse.ArgumentParser(prog="nvlx-controller",description="nvlx 1.0 production reconciliation and approval controller")
    s=p.add_subparsers(dest="cmd",required=True)
    q=s.add_parser("config-validate"); q.add_argument("config")
    q=s.add_parser("compat"); q.add_argument("--kubernetes-version",required=True); q.add_argument("--gpucluster",action="store_true"); q.add_argument("--clusterpolicy",action="store_true"); q.add_argument("--computedomains-crd-ready",action="store_true"); q.add_argument("--migrate-clusterpolicy-to-gpucluster",action="store_true")
    q=s.add_parser("reconcile-plan"); q.add_argument("config"); q.add_argument("--kubernetes-version",required=True); q.add_argument("--gpucluster",action="store_true"); q.add_argument("--clusterpolicy",action="store_true"); q.add_argument("--computedomains-crd-ready",action="store_true"); q.add_argument("--operation",required=True); q.add_argument("--target",required=True); q.add_argument("--step",action="append",required=True)
    q=s.add_parser("approve"); q.add_argument("plan"); q.add_argument("--by",required=True)
    q=s.add_parser("execute-check"); q.add_argument("plan"); q.add_argument("approval")
    q=s.add_parser("state-demo"); q.add_argument("config_fingerprint"); q.add_argument("--plan-fingerprint")
    q=s.add_parser("ha-plan"); q.add_argument("--namespace",default="nvlx-system"); q.add_argument("--name",default="nvlx-controller"); q.add_argument("--holder",default="controller-0"); q.add_argument("--lease",type=int,default=30); q.add_argument("--renew",type=int,default=20); q.add_argument("--retry",type=int,default=5)
    q=s.add_parser("bundle-manifest"); q.add_argument("root"); q.add_argument("paths",nargs="+")
    q=s.add_parser("cosign-plan"); q.add_argument("manifest"); q.add_argument("signature"); q.add_argument("--identity",required=True)
    a=p.parse_args(argv)
    if a.cmd=="config-validate":
        r=config_validate(_read(a.config)); _json(r.to_dict()); return 0 if r.valid else 2
    if a.cmd=="compat":
        r=compat_check(kubernetes_version=a.kubernetes_version,has_gpucluster=a.gpucluster,has_clusterpolicy=a.clusterpolicy,computedomains_crd_ready=a.computedomains_crd_ready,migrating_clusterpolicy_to_gpucluster=a.migrate_clusterpolicy_to_gpucluster); _json(r.to_dict()); return 0 if r.compatible else 2
    if a.cmd=="reconcile-plan":
        c=config_validate(_read(a.config)); x=compat_check(kubernetes_version=a.kubernetes_version,has_gpucluster=a.gpucluster,has_clusterpolicy=a.clusterpolicy,computedomains_crd_ready=a.computedomains_crd_ready); r=reconcile_plan(c,x,operation=a.operation,target=a.target,steps=a.step); _json(r.to_dict()); return 0 if r.allowed else 2
    if a.cmd=="approve":
        d=_read(a.plan); pd=d.get("plan",d); ep=ExecutionPlan(pd["operation"],pd["target"],tuple(pd["steps"]),pd["config_fingerprint"],pd["fingerprint"]); r=approve(ep,a.by); _json(r.to_dict()); return 0
    if a.cmd=="execute-check":
        pd=_read(a.plan); pd=pd.get("plan",pd); ad=_read(a.approval); ep=ExecutionPlan(pd["operation"],pd["target"],tuple(pd["steps"]),pd["config_fingerprint"],pd["fingerprint"]); ap=Approval(**ad); ok,reasons=execution_allowed(ep,ap); _json({"allowed":ok,"reasons":reasons}); return 0 if ok else 2
    if a.cmd=="state-demo":
        st=new_state(a.config_fingerprint); out=[st.to_dict()]; st=transition(st,"planned",plan_fingerprint=a.plan_fingerprint or "demo"); out.append(st.to_dict()); st=transition(st,"awaiting-approval"); out.append(st.to_dict()); _json(out); return 0
    if a.cmd=="ha-plan":
        r=ha_plan(a.namespace,a.name,a.holder,a.lease,a.renew,a.retry); _json({"plan":r.to_dict(),"lease_manifest":kubernetes_manifest(r) if r.valid else None}); return 0 if r.valid else 2
    if a.cmd=="bundle-manifest": _json(bundle_build(Path(a.root),a.paths).to_dict()); return 0
    if a.cmd=="cosign-plan": _json(cosign_verify_blob_plan(a.manifest,a.signature,a.identity)); return 0
    return 2

if __name__=="__main__": raise SystemExit(main())
