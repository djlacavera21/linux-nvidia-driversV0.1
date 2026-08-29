from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from nvlx.config_v1 import validate
from nvlx.approvals import make_plan, approve, execution_allowed
from nvlx.controller_state import new_state, transition
from nvlx.ha import plan as ha_plan
from nvlx.v1_compat import check
from nvlx.bundle import build, verify

class V10Tests(unittest.TestCase):
    def test_config_contract_and_fingerprint(self):
        c={"schema_version":1,"cluster":{"name":"prod"},"policy":{},"execution":{"mode":"plan"}}
        a=validate(c); b=validate(dict(c)); self.assertTrue(a.valid); self.assertEqual(a.fingerprint,b.fingerprint)
    def test_unknown_config_key_fails_closed(self):
        r=validate({"schema_version":1,"cluster":{"name":"prod"},"policy":{},"surprise":1}); self.assertFalse(r.valid)
    def test_approval_bound_to_exact_plan(self):
        p=make_plan("upgrade","gpu-a",["step-a"],"cfg"); a=approve(p,"operator"); self.assertTrue(execution_allowed(p,a)[0])
        p2=make_plan("upgrade","gpu-a",["step-b"],"cfg"); self.assertFalse(execution_allowed(p2,a)[0])
    def test_state_machine_rejects_skip(self):
        s=new_state("cfg");
        with self.assertRaises(ValueError): transition(s,"executing")
    def test_ha_timing(self):
        self.assertTrue(ha_plan().valid); self.assertFalse(ha_plan(lease_duration_seconds=10,renew_deadline_seconds=10,retry_period_seconds=5).valid)
    def test_gpucluster_requires_compute_crd(self):
        r=check(kubernetes_version="v1.35.2",has_gpucluster=True,has_clusterpolicy=False,computedomains_crd_ready=False); self.assertFalse(r.compatible)
    def test_in_place_policy_to_gpucluster_migration_blocked(self):
        r=check(kubernetes_version="v1.35.2",has_gpucluster=False,has_clusterpolicy=True,computedomains_crd_ready=True,migrating_clusterpolicy_to_gpucluster=True); self.assertFalse(r.compatible)
    def test_bundle_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/"a.json").write_text("{}\n"); m=build(root,["a.json"]); self.assertTrue(verify(root,m)[0]); (root/"a.json").write_text("changed\n"); self.assertFalse(verify(root,m)[0])

if __name__=="__main__": unittest.main()
