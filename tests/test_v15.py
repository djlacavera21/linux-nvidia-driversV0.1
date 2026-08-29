import tempfile
import unittest
from pathlib import Path
from nvlx.watch_v15 import decide
from nvlx.patch_v15 import plan as patch, classify_status
from nvlx.workqueue_v15 import retry
from nvlx.owner_v15 import validate
from nvlx.operator_v15 import plan
from nvlx.healthz_v15 import evaluate
from nvlx.finalizer import decide as finalize
from nvlx.generation_v153 import evaluate as generation
from nvlx.status_write_v153 import changed as status_changed
from nvlx.event_dedupe_v154 import fingerprint as event_fingerprint
from nvlx.shutdown_v154 import evaluate as shutdown
from nvlx.leadership_v155 import FenceToken, validate as fence
from nvlx.fence_store_v156 import save as save_fence, load as load_fence
from nvlx.lease_renewal_v156 import classify as renewal

class V15Tests(unittest.TestCase):
    def test_watch_relist(self): self.assertEqual(decide("ERROR","10").action,"relist")
    def test_bookmark(self): self.assertEqual(decide("BOOKMARK","11").action,"checkpoint")
    def test_empty_cursor_relists(self): self.assertEqual(decide("MODIFIED"," ").action,"relist")
    def test_patch_requires_rv(self): self.assertFalse(patch("").valid)
    def test_patch_conflict_retries(self): self.assertEqual(classify_status(409),("relist-retry",True))
    def test_patch_precondition_retries(self): self.assertEqual(classify_status(412),("relist-retry",True))
    def test_patch_gone_does_not_retry(self): self.assertEqual(classify_status(410),("gone",False))
    def test_patch_timeout_retries(self): self.assertEqual(classify_status(408),("retry",True))
    def test_queue_deadletters(self): self.assertTrue(retry(8).dead_letter)
    def test_retry_jitter_is_deterministic_and_bounded(self):
        a=retry(3,jitter_key="event-a"); b=retry(3,jitter_key="event-a")
        self.assertEqual(a.delay_seconds,b.delay_seconds); self.assertGreaterEqual(a.delay_seconds,16); self.assertLessEqual(a.delay_seconds,20)
    def test_ownership(self):
        ok,denied=validate(["status.phase","spec.driver.version"]); self.assertFalse(ok); self.assertEqual(denied,("spec.driver.version",))
    def test_generation_discards_stale_event(self): self.assertTrue(generation(3,4).stale)
    def test_operator_status_patch(self): self.assertEqual(plan("prod",event_type="MODIFIED",resource_version="12",generation=3,allowed=True,runtime_action="execute").action,"patch-status")
    def test_operator_discards_stale_generation(self): self.assertEqual(plan("prod",event_type="MODIFIED",resource_version="12",generation=3,latest_generation=4,allowed=True,runtime_action="execute").action,"discard-stale")
    def test_duplicate_watch_event_is_noop(self):
        fp=event_fingerprint(event_type="MODIFIED",resource_version="12",generation=3)
        self.assertEqual(plan("prod",event_type="MODIFIED",resource_version="12",generation=3,allowed=True,runtime_action="execute",previous_event_fingerprint=fp).action,"event-noop")
    def test_operator_fences_lost_leader(self): self.assertEqual(plan("prod",event_type="MODIFIED",resource_version="12",generation=3,allowed=True,runtime_action="execute",mutation_fence_ok=False).action,"fenced")
    def test_fence_token_allows_exact_lease(self):
        t=FenceToken("controller-a",7,"42"); self.assertTrue(fence(t,current_holder="controller-a",current_epoch=7,current_resource_version="42").allowed)
    def test_fence_token_rejects_handoff(self):
        t=FenceToken("controller-a",7,"42"); self.assertFalse(fence(t,current_holder="controller-b",current_epoch=8,current_resource_version="43").allowed)
    def test_fence_token_rejects_stale_lease(self):
        t=FenceToken("controller-a",7,"42"); self.assertFalse(fence(t,current_holder="controller-a",current_epoch=7,current_resource_version="42",lease_fresh=False).allowed)
    def test_fence_token_persists_across_restart(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fence.json"; t=FenceToken("controller-a",7,"42"); save_fence(p,t); self.assertEqual(load_fence(p),t)
    def test_persisted_old_token_fails_after_handoff(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fence.json"; save_fence(p,FenceToken("controller-a",7,"42")); restored=load_fence(p)
            self.assertFalse(fence(restored,current_holder="controller-b",current_epoch=8,current_resource_version="43").allowed)
    def test_corrupt_fence_store_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fence.json"; p.write_text('{"holder":"a"}',encoding="utf-8")
            with self.assertRaises(ValueError): load_fence(p)
    def test_renewal_conflict_fences_and_retries(self): self.assertEqual(renewal(409,holder_unchanged=True,resource_version_unchanged=False).action,"relist-fence")
    def test_renewal_uncertainty_fences(self):
        r=renewal(503,holder_unchanged=True,resource_version_unchanged=True); self.assertFalse(r.leadership_valid); self.assertTrue(r.retry)
    def test_renewal_success_preserves_authority(self): self.assertTrue(renewal(200,holder_unchanged=True,resource_version_unchanged=True).leadership_valid)
    def test_status_write_is_idempotent(self):
        status={"phase":"Ready","conditions":[{"type":"Ready","lastTransitionTime":"now"}]}; first,fp=status_changed(status,None); second,_=status_changed(status,fp); self.assertTrue(first); self.assertFalse(second)
    def test_finalizer_absent_is_complete(self): self.assertEqual(finalize(deleting=True,rollback_pending=False,quarantined_nodes=0,active_execution=False,finalizer_present=False).action,"complete")
    def test_finalizer_waits_for_status_write(self): self.assertEqual(finalize(deleting=True,rollback_pending=False,quarantined_nodes=0,active_execution=False,status_write_pending=True).action,"hold")
    def test_shutdown_drains_active_mutation(self): self.assertEqual(shutdown(terminating=True,active_mutation=True).action,"drain")
    def test_shutdown_fences_on_leadership_loss(self): self.assertEqual(shutdown(terminating=False,active_mutation=True,leadership_valid=False).action,"fence-drain")
    def test_shutdown_standby_after_handoff(self): self.assertEqual(shutdown(terminating=False,active_mutation=False,leadership_valid=False).action,"standby")
    def test_health(self): self.assertTrue(evaluate(api_reachable=True,leader=True,inventory_fresh=True).ready)

if __name__=="__main__": unittest.main()
