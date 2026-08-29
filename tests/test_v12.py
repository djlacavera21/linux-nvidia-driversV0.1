import unittest
from datetime import datetime, timezone
from nvlx.change_window import ChangeWindow, allowed
from nvlx.circuit_breaker import evaluate as circuit
from nvlx.idempotency import key, duplicate
from nvlx.rollout_budget import evaluate as budget
from nvlx.drift import classify
from nvlx.preflight_snapshot import capture, unchanged
from nvlx.recovery import plan

class V12Tests(unittest.TestCase):
    def test_change_window(self):
        ok,_=allowed(ChangeWindow(1,3),datetime(2026,1,1,2,tzinfo=timezone.utc)); self.assertTrue(ok)
        ok,_=allowed(ChangeWindow(1,3),datetime(2026,1,1,4,tzinfo=timezone.utc)); self.assertFalse(ok)
    def test_circuit_breaker(self):
        self.assertTrue(circuit(3,3).open); self.assertTrue(circuit(0,3,security_failure=True).open)
    def test_idempotency(self):
        a=key("abc","gpu01",2); self.assertEqual(a,key("abc","gpu01",2)); self.assertTrue(duplicate(a,[a]))
    def test_rollout_budget(self):
        r=budget(20,1,max_unavailable=2); self.assertTrue(r.allowed); self.assertEqual(r.slots,1)
        self.assertFalse(budget(20,2,max_unavailable=2).allowed)
    def test_drift(self):
        r=classify({"driver_version":"610"},{"driver_version":"595"}); self.assertTrue(r.requires_approval)
    def test_preflight(self):
        s=capture({"healthy":True,"nodes":4}); self.assertTrue(unchanged(s,{"healthy":True,"nodes":4})); self.assertFalse(unchanged(s,{"healthy":False,"nodes":4}))
    def test_recovery(self):
        self.assertEqual(plan(rollback_available=True,security_failure=False,state_uncertain=False,failure_count=1).action,"rollback")
        self.assertFalse(plan(rollback_available=False,security_failure=False,state_uncertain=True,failure_count=1).automatic)

if __name__=="__main__": unittest.main()
