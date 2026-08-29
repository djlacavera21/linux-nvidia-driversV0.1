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


def _json(v): print(json.dumps(v,indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(prog="nvlx-fleet",description="NVIDIA GPU cluster qualification and rollout orchestration")
    s=p.add_subparsers(dest="cmd",required=True)
    s.add_parser("qualify"); s.add_parser("clusterpolicy")
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
    if a.cmd=="qualify":
        rows=qualify_nodes(); _json([r.to_dict() for r in rows]); return 0 if rows and all(r.qualified for r in rows if r.gpu_present) else 2
    if a.cmd=="clusterpolicy":
        r=validate_clusterpolicy(); _json(r.to_dict()); return 0 if r.valid else 2
    if a.cmd=="maintenance-plan": _json(maintenance_plan(a.node,timeout=a.timeout).to_dict()); return 0
    if a.cmd=="drain": _json(drain_node(a.node,confirmed=a.yes,timeout=a.timeout).to_dict()); return 0
    if a.cmd=="uncordon": uncordon_node(a.node,confirmed=a.yes); return 0
    if a.cmd=="diag-plan": _json(diag_plan(a.level,a.timeout_sec).to_dict()); return 0
    if a.cmd=="diag-run":
        r=diag_run(a.level,a.timeout_sec,confirmed=a.yes); _json(r); return 0 if r["passed"] else 2
    if a.cmd=="quarantine-plan": _json(quarantine_plan(a.node,a.reason).to_dict()); return 0
    if a.cmd=="quarantine": _json(quarantine_node(a.node,a.reason,confirmed=a.yes).to_dict()); return 0
    if a.cmd=="unquarantine": unquarantine_node(a.node,confirmed=a.yes); return 0
    if a.cmd=="alerts": print(prometheus_rule_group(),end=""); return 0
    if a.cmd=="waves": _json([w.to_dict() for w in plan_waves(a.nodes,canary_count=a.canaries,wave_size=a.wave_size)]); return 0
    if a.cmd=="security-gate":
        r=gate(a.dcgm_exporter_version,fail_closed=not a.fail_open); _json(r); return 0 if r["passed"] else 2
    if a.cmd=="advance-check":
        ok,reasons=advancement_allowed(qualified=a.qualified,diagnostics_passed=a.diagnostics_passed,security_gate_passed=a.security_passed,quarantined=a.quarantined); _json({"allowed":ok,"reasons":reasons}); return 0 if ok else 2
    return 2

if __name__=="__main__": raise SystemExit(main())
