import unittest
from nvlx.watch_v15 import decide
from nvlx.patch_v15 import plan as patch, classify_status
from nvlx.workqueue_v15 import retry
from nvlx.owner_v15 import validate
from nvlx.operator_v15 import plan
from nvlx.healthz_v15 import evaluate
from nvlx.finalizer import decide as finalize
from nvlx.generation_v153 import evaluate as generation
from nvlx.status_write_v153 import changed as status_changed

class V15Tests(unittest.TestCase):
    def test_watch_relist(self): self.assertEqual(decide("ERROR","10").action,"relist")
    def test_bookmark(self): self.assertEqual(decide("BOOKMARK","11").action,"checkpoint")
    def test_empty_cursor_relists(self): self.assertEqual(decide("MODIFIED"," ").action,"relist")
    def test_patch_requires_rv(self): self.assertFalse(patch("").valid)
    def test_patch_conflict_retries(self): self.assertEqual(classify_status(409),("relist-retry",True))
    def test_patch_precondition_retries(self): self.assertEqual(classify_status(412),("relist-retry",True))
    def test_patch_gone_does_not_retry(self): self.assertEqual(classify_status(410),("gone",False))
    def test_patch_timeout_retries(self): self.assertEqual(classify_status(408),("retry",True))
    def test_queue_deadletters(self):
        r=retry(8); self.assertTrue(r.dead_letter); self.assertEqual(r.reason,"retry budget exhausted")
    def test_queue_rejects_invalid_bounds(self):
        with self.assertRaises(ValueError): retry(0,base_seconds=0)
        with self.assertRaises(ValueError): retry(0,base_seconds=5,max_seconds=4)
    def test_ownership(self):
        ok,denied=validate(["status.phase","spec.driver.version"]); self.assertFalse(ok); self.assertEqual(denied,("spec.driver.version",))
    def test_malformed_ownership_path_denied(self):
        ok,denied=validate([".status.phase","status..phase","status.conditions[0]"]); self.assertFalse(ok); self.assertEqual(len(denied),3)
    def test_generation_discards_stale_event(self): self.assertTrue(generation(3,4).stale)
    def test_generation_advances_new_event(self): self.assertEqual(generation(5,4).action,"advance")
    def test_operator_status_patch(self):
        r=plan("prod",event_type="MODIFIED",resource_version="12",generation=3,allowed=True,runtime_action="execute")
        self.assertEqual(r.action,"patch-status"); self.assertEqual(r.patch["resource_version"],"12")
    def test_operator_discards_stale_generation(self):
        r=plan("prod",event_type="MODIFIED",resource_version="12",generation=3,latest_generation=4,allowed=True,runtime_action="execute")
        self.assertEqual(r.action,"discard-stale"); self.assertIsNone(r.patch)
    def test_status_write_is_idempotent(self):
        status={"phase":"Ready","event":{"eventTime":"now"},"conditions":[{"type":"Ready","lastTransitionTime":"now"}]}
        first,fp=status_changed(status,None); second,fp2=status_changed(status,fp)
        self.assertTrue(first); self.assertFalse(second); self.assertEqual(fp,fp2)
    def test_operator_duplicate_status_is_noop(self):
        first=plan("prod",event_type="MODIFIED",resource_version="12",generation=3,allowed=True,runtime_action="execute")
        second=plan("prod",event_type="MODIFIED",resource_version="13",generation=3,allowed=True,runtime_action="execute",previous_status_fingerprint=first.status_fingerprint)
        self.assertEqual(second.action,"status-noop"); self.assertIsNone(second.patch)
    def test_operator_missing_cursor_relists(self):
        self.assertEqual(plan("prod",event_type="MODIFIED",resource_version="",generation=3,allowed=True,runtime_action="execute").action,"relist")
    def test_operator_relist(self): self.assertEqual(plan("prod",event_type="ERROR",resource_version="12",generation=3,allowed=False,runtime_action="hold").action,"relist")
    def test_delete_event_never_patches_status(self):
        r=plan("prod",event_type="DELETED",resource_version="13",generation=3,allowed=False,runtime_action="hold")
        self.assertEqual(r.action,"observe-delete"); self.assertIsNone(r.patch)
    def test_exhausted_requeue_deadletters(self):
        r=plan("prod",event_type="ERROR",resource_version="13",generation=3,allowed=False,runtime_action="hold",attempt=8)
        self.assertEqual(r.action,"dead-letter")
    def test_finalizer_rejects_negative_quarantine(self):
        with self.assertRaises(ValueError): finalize(deleting=True,rollback_pending=False,quarantined_nodes=-1,active_execution=False)
    def test_finalizer_absent_is_complete(self):
        r=finalize(deleting=True,rollback_pending=False,quarantined_nodes=0,active_execution=False,finalizer_present=False)
        self.assertEqual(r.action,"complete"); self.assertFalse(r.remove_finalizer)
    def test_health(self):
        self.assertTrue(evaluate(api_reachable=True,leader=True,inventory_fresh=True).ready)
        self.assertFalse(evaluate(api_reachable=True,leader=False,inventory_fresh=True).ready)
        self.assertFalse(evaluate(api_reachable=True,leader=True,inventory_fresh=True,lease_fresh=False).ready)

if __name__=="__main__": unittest.main()
