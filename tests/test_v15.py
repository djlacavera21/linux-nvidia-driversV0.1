import unittest
from nvlx.watch_v15 import decide
from nvlx.patch_v15 import plan as patch
from nvlx.workqueue_v15 import retry
from nvlx.owner_v15 import validate
from nvlx.operator_v15 import plan
from nvlx.healthz_v15 import evaluate

class V15Tests(unittest.TestCase):
    def test_watch_relist(self): self.assertEqual(decide("ERROR","10").action,"relist")
    def test_bookmark(self): self.assertEqual(decide("BOOKMARK","11").action,"checkpoint")
    def test_patch_requires_rv(self): self.assertFalse(patch("").valid)
    def test_queue_deadletters(self): self.assertTrue(retry(8).dead_letter)
    def test_ownership(self):
        ok,denied=validate(["status.phase","spec.driver.version"]); self.assertFalse(ok); self.assertEqual(denied,("spec.driver.version",))
    def test_operator_status_patch(self):
        r=plan("prod",event_type="MODIFIED",resource_version="12",generation=3,allowed=True,runtime_action="execute")
        self.assertEqual(r.action,"patch-status"); self.assertEqual(r.patch["resource_version"],"12")
    def test_operator_relist(self): self.assertEqual(plan("prod",event_type="ERROR",resource_version="12",generation=3,allowed=False,runtime_action="hold").action,"relist")
    def test_health(self):
        self.assertTrue(evaluate(api_reachable=True,leader=True,inventory_fresh=True).ready)
        self.assertFalse(evaluate(api_reachable=True,leader=False,inventory_fresh=True).ready)

if __name__=="__main__": unittest.main()
