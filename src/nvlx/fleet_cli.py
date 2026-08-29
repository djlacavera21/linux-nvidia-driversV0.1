"""nvlx fleet command surface for cluster orchestration."""
from __future__ import annotations
import argparse, json
from .alerts import prometheus_rule_group
from .cluster import qualify_nodes
from .clusterpolicy import validate_clusterpolicy
from .dcgm_diag import plan as diag_plan, run as diag_run
from .maintenance import apply as drain_node, plan as maintenance_plan, release as uncordon_node
from .quarantine import apply as quarantine_node, clear as unquarantine_node, plan as quarantine_plan
from .rollout import advancement_allowed, plan_waves
from .security_gate import gate
from .dra import validate as dra_validate
from .fabric import inspect as fabric_inspect, domain_labels
from .network import inspect as network_inspect
from .capacity import inspect as capacity_inspect
from .confidential import inspect as confidential_inspect
from .admission import render as admission_render
from .placement import plan as placement_plan
from .gang import plan as gang_plan
from .gpudirect import report as gpudirect_report
from .mig_broker import plan as mig_broker_plan
from .power_policy import plan as power_policy_plan
from .evacuation import plan as evacuation_plan
from .federation import ClusterTarget, plan as federation_plan

def _json(v): print(json.dumps(v,indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(prog="nvlx-fleet",description="NVIDIA GPU placement, resource-fabric, and resilience orchestration")
    s=p.add_subparsers(dest="cmd",required=True)
    for name in ("qualify","clusterpolicy","dra","fabric","network","capacity","confidential","admission-policy","gpudirect"): s.add_parser(name)
    q=s.add_parser("fabric-domains"); q.add_argument("nodes",nargs="+"); q.add_argument("--size",type=int,default=8)
    q=s.add_parser("placement"); q.add_argument("--count",type=int,default=1); q.add_argument("--product"); q.add_argument("--min-memory-gib",type=int); q.add_argument("--compute-domain")
    q=s.add_parser("gang"); q.add_argument("--replicas",type=int,required=True); q.add_argument("--gpus-per-replica",type=int,required=True); q.add_argument("--compute-domain"); q.add_argument("--min-available",type=int)
    q=s.add_parser("mig-broker"); q.add_argument("--profile"); q.add_argument("--replicas",type=int,default=1); q.add_argument("--dynamic",action="store_true"); q.add_argument("--feature-gate",action="append",default=[])
    q=s.add_parser("power-policy"); q.add_argument("--max-watts",type=int); q.add_argument("--max-temp-c",type=int); q.add_argument("--action",choices=("alert","drain","quarantine"),default="quarantine")
    q=s.add_parser("evacuate-plan"); q.add_argument("node"); q.add_argument("--checkpoint-mode",choices=("application","criu","none"),default="application"); q.add_argument("--namespace")
    q=s.add_parser("federation-plan"); q.add_argument("--primary",required=True); q.add_argument("--required-gpus",type=int,required=True); q.add_argument("clusters",nargs="+",help="name:region:gpu_capacity[:healthy]")
    q=s.add_parser("maintenance-plan"); q.add_argument("node"); q.add_argument("--timeout",default="10m")
    q=s.add_parser("drain"); q.add_argument("node"); q.add_argument("--timeout",default="10m"); q.add_argument("--yes",action="store_true")
    q=s.add_parser("uncordon"); q.add_argument("node"); q.add_argument("--yes",action="store_true")
    q=s.add_parser("diag-plan"); q.add_argument("--level",type=int,default=3); q.add_argument("--timeout-sec",type=int,default=900)
    q=s.add_parser("diag-run"); q.add_argument("--level",type=int,default=3); q.add_argument("--timeout-sec",type=int,default=900); q.add_argument("--yes",action="store_true")
    q=s.add_parser("quarantine-plan"); q.add_argument("node"); q.add_argument("reason")
    q=s.add_parser("quarantine"); q.add_argument("node"); q.add_argument("reason"); q.add_argument("--yes",action="store_true")
    q=s.add_parser("unquarantine"); q.add_argument("node"); q.add_argument("--yes",action="store_true")
    s.add_parser("alerts")
    q=s.add_parser("waves"); q.add_argument("nodes",nargs="+"); q.add_argument("--canaries",type=int,default=1); q.add_argument("--wave-size",type=int,default=5)
    q=s.add_parser("security-gate"); q.add_argument("--dcgm-exporter-version"); q.add_argument("--fail-open",action="store_true")
    q=s.add_parser("advance-check"); q.add_argument("--qualified",action="store_true"); q.add_argument("--diagnostics-passed",action="store_true"); q.add_argument("--security-passed",action="store_true"); q.add_argument("--quarantined",type=int,default=0)
    a=p.parse_args(argv)
    if a.cmd=="qualify": rows=qualify_nodes(); _json([r.to_dict() for r in rows]); return 0 if rows and all(r.qualified for r in rows if r.gpu_present) else 2
    if a.cmd=="clusterpolicy": r=validate_clusterpolicy(); _json(r.to_dict()); return 0 if r.valid else 2
    if a.cmd=="dra": r=dra_validate(); _json(r.to_dict()); return 0 if r.valid else 2
    if a.cmd=="fabric": r=fabric_inspect(); _json(r.to_dict()); return 0 if r.healthy else 2
    if a.cmd=="network": r=network_inspect(); _json(r.to_dict()); return 0 if r.healthy else 2
    if a.cmd=="capacity": _json(capacity_inspect().to_dict()); return 0
    if a.cmd=="confidential": r=confidential_inspect(); _json(r.to_dict()); return 0 if r.valid else 2
    if a.cmd=="admission-policy": print(admission_render(),end=""); return 0
    if a.cmd=="gpudirect": r=gpudirect_report(); _json(r.to_dict()); return 0 if r.qualified else 2
    if a.cmd=="fabric-domains": _json(domain_labels(a.nodes,a.size)); return 0
    if a.cmd=="placement": _json(placement_plan(count=a.count,product=a.product,min_memory_gib=a.min_memory_gib,compute_domain=a.compute_domain).to_dict()); return 0
    if a.cmd=="gang": _json(gang_plan(a.replicas,a.gpus_per_replica,compute_domain=a.compute_domain,min_available=a.min_available).to_dict()); return 0
    if a.cmd=="mig-broker": r=mig_broker_plan(profile=a.profile,replicas=a.replicas,dynamic=a.dynamic,enabled_feature_gates=a.feature_gate); _json(r.to_dict()); return 0 if r.valid else 2
    if a.cmd=="power-policy": r=power_policy_plan(max_watts=a.max_watts,max_temp_c=a.max_temp_c,action=a.action); _json(r.to_dict()); return 0 if r.valid else 2
    if a.cmd=="evacuate-plan": _json(evacuation_plan(a.node,checkpoint_mode=a.checkpoint_mode,namespace=a.namespace).to_dict()); return 0
    if a.cmd=="federation-plan":
        clusters=[]
        for raw in a.clusters:
            parts=raw.split(":"); clusters.append(ClusterTarget(parts[0],parts[1],int(parts[2]),len(parts)<4 or parts[3].lower() not in {"false","0","down"}))
        r=federation_plan(clusters,primary=a.primary,required_gpus=a.required_gpus); _json(r.to_dict()); return 0 if r.valid else 2
    if a.cmd=="maintenance-plan": _json(maintenance_plan(a.node,timeout=a.timeout).to_dict()); return 0
    if a.cmd=="drain": _json(drain_node(a.node,confirmed=a.yes,timeout=a.timeout).to_dict()); return 0
    if a.cmd=="uncordon": uncordon_node(a.node,confirmed=a.yes); return 0
    if a.cmd=="diag-plan": _json(diag_plan(a.level,a.timeout_sec).to_dict()); return 0
    if a.cmd=="diag-run": r=diag_run(a.level,a.timeout_sec,confirmed=a.yes); _json(r); return 0 if r["passed"] else 2
    if a.cmd=="quarantine-plan": _json(quarantine_plan(a.node,a.reason).to_dict()); return 0
    if a.cmd=="quarantine": _json(quarantine_node(a.node,a.reason,confirmed=a.yes).to_dict()); return 0
    if a.cmd=="unquarantine": unquarantine_node(a.node,confirmed=a.yes); return 0
    if a.cmd=="alerts": print(prometheus_rule_group(),end=""); return 0
    if a.cmd=="waves": _json([w.to_dict() for w in plan_waves(a.nodes,canary_count=a.canaries,wave_size=a.wave_size)]); return 0
    if a.cmd=="security-gate": r=gate(a.dcgm_exporter_version,fail_closed=not a.fail_open); _json(r); return 0 if r["passed"] else 2
    if a.cmd=="advance-check": ok,reasons=advancement_allowed(qualified=a.qualified,diagnostics_passed=a.diagnostics_passed,security_gate_passed=a.security_passed,quarantined=a.quarantined); _json({"allowed":ok,"reasons":reasons}); return 0 if ok else 2
    return 2

if __name__=="__main__": raise SystemExit(main())
