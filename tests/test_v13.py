import unittest
from datetime import datetime, timezone
from nvlx.change_window import ChangeWindow
from nvlx.preflight_snapshot import capture
from nvlx.runtime_v13 import decide
from nvlx.runtime_store import empty, record_failure, record_success
from nvlx.idempotency import key
from nvlx.canary import evaluate as canary
from nvlx.rollback_orchestrator import plan as rollback_plan
from nvlx.maintenance_policy import render as maintenance_render

class V13Tests(unittest.TestCase):
    def test_integrated_runtime_executes_when_all_gates_pass(self):
        facts={"healthy":True,"generation":2}; snap=capture(facts); ek=key("plan","gpu01",2)
        r=decide(leader=True,approval_valid=True,window=ChangeWindow(1,3),preflight=snap,current_facts=facts,execution_key=ek,completed_keys=(),total_nodes=20,currently_unavailable=0,failure_count=0,now=datetime(2026,1,1,2,tzinfo=timezone.utc))
        self.assertTrue(r.allowed); self.assertEqual(r.action,"execute")
    def test_stale_preflight_holds(self):
        snap=capture({"healthy":True}); ek=key("plan","gpu01",2)
        r=decide(leader=True,approval_valid=True,window=ChangeWindow(1,3),preflight=snap,current_facts={"healthy":False},execution_key=ek,completed_keys=(),total_nodes=20,currently_unavailable=0,failure_count=0,now=datetime(2026,1,1,2,tzinfo=timezone.utc))
        self.assertFalse(r.allowed); self.assertIn("preflight facts changed",r.reasons)
    def test_security_failure_quarantines(self):
        facts={"healthy":True}; snap=capture(facts); ek=key("plan","gpu01",2)
        r=decide(leader=True,approval_valid=True,window=ChangeWindow(1,3),preflight=snap,current_facts=facts,execution_key=ek,completed_keys=(),total_nodes=20,currently_unavailable=0,failure_count=0,security_failure=True,now=datetime(2026,1,1,2,tzinfo=timezone.utc))
        self.assertEqual(r.action,"quarantine")
    def test_runtime_store(self):
        s=record_failure(empty()); self.assertEqual(s.failure_count,1)
        s=record_success(s,"exec-a",3); self.assertEqual(s.failure_count,0); self.assertIn("exec-a",s.completed_execution_keys)
    def test_canary(self):
        self.assertTrue(canary(current_wave=0,total_waves=3,healthy_fraction=1.0).promote)
        self.assertFalse(canary(current_wave=0,total_waves=3,healthy_fraction=.9).promote)
    def test_rollback_orchestration(self):
        r=rollback_plan(rollback_available=True,security_failure=False,state_uncertain=False,failure_count=1)
        self.assertTrue(r.automatic); self.assertIn("boot-validate",r.steps)
    def test_maintenance_manifest(self):
        text=maintenance_render(start_hour_utc=2,end_hour_utc=5); self.assertIn('"timezone": "UTC"',text)

if __name__=="__main__": unittest.main()
