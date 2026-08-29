from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from nvlx.policy import FleetPolicy,evaluate
from nvlx.placement_controller import decide
from nvlx.curtailment import plan as curtailment_plan
from nvlx.slo import evaluate as slo_evaluate
from nvlx.failover_exec import plan as failover_plan
from nvlx.audit import append,event

class V09Tests(unittest.TestCase):
    def test_policy_blocks_missing_rdma(self):
        ok,reasons=evaluate({"free_gpus":2,"rdma_ready":False,"power_headroom_w":100},FleetPolicy(require_rdma=True))
        self.assertFalse(ok); self.assertIn("RDMA required",reasons)
    def test_placement_prefers_more_capacity_and_fabric(self):
        p=FleetPolicy(min_power_headroom_w=10)
        r=decide([{"name":"b","free_gpus":2,"power_headroom_w":100},{"name":"a","free_gpus":2,"power_headroom_w":100,"fabric_healthy":True}],p)
        self.assertEqual(r.target,"a")
    def test_slo_blocks_xid(self):
        self.assertFalse(slo_evaluate(healthy_fraction=1.0,p95_startup_seconds=30,quarantined=0,xid_events=1).passed)
    def test_curtailment_checkpoint_path(self):
        r=curtailment_plan(1000,500,checkpointable=True); self.assertTrue(r.safe); self.assertEqual(r.action,"checkpoint-and-evacuate")
    def test_failover_requires_all_gates(self):
        self.assertFalse(failover_plan("a","b","default",checkpoint_ready=True,capacity_ready=True,security_ready=False).safe)
    def test_audit_jsonl(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"audit.jsonl"; append(p,event("place","gpu01",True)); self.assertIn('"action": "place"',p.read_text())

if __name__=="__main__": unittest.main()
