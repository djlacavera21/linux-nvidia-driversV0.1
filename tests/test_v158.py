import unittest
from nvlx.leadership_v155 import FenceToken
from nvlx.fence_monotonic_v158 import assess
from nvlx.fence_recovery_v157 import assess as recover

class V158Tests(unittest.TestCase):
    def test_initial_token_can_persist(self):
        self.assertEqual(assess(None,FenceToken("controller-a",1,"10")).action,"persist-initial")

    def test_epoch_rollback_is_rejected(self):
        previous=FenceToken("controller-a",7,"42")
        candidate=FenceToken("controller-a",6,"41")
        r=assess(previous,candidate)
        self.assertFalse(r.allowed); self.assertEqual(r.action,"reject-rollback")

    def test_holder_change_without_epoch_advance_is_rejected(self):
        previous=FenceToken("controller-a",7,"42")
        candidate=FenceToken("controller-b",7,"43")
        r=assess(previous,candidate)
        self.assertFalse(r.allowed); self.assertEqual(r.action,"reject-epoch-collision")

    def test_same_epoch_renewal_can_advance_resource_version(self):
        previous=FenceToken("controller-a",7,"42")
        candidate=FenceToken("controller-a",7,"43")
        r=assess(previous,candidate)
        self.assertTrue(r.allowed); self.assertEqual(r.action,"persist-renewal")

    def test_duplicate_token_is_noop(self):
        token=FenceToken("controller-a",7,"42")
        r=assess(token,token)
        self.assertFalse(r.allowed); self.assertEqual(r.action,"noop")

    def test_reacquire_requires_newer_epoch(self):
        previous=FenceToken("controller-a",7,"42")
        same_epoch=FenceToken("controller-a",7,"43")
        r=assess(previous,same_epoch,reacquired=True)
        self.assertFalse(r.allowed); self.assertEqual(r.action,"reject-stale-reacquire")
        newer=FenceToken("controller-b",8,"44")
        r=assess(previous,newer,reacquired=True)
        self.assertTrue(r.allowed); self.assertEqual(r.action,"persist-new-epoch")

    def test_recovery_still_blocks_epoch_rollback(self):
        r=recover(FenceToken("controller-a",8,"43"),current_holder="controller-a",current_epoch=7,current_resource_version="42")
        self.assertFalse(r.allowed); self.assertEqual(r.action,"rollback-detected")

if __name__ == "__main__": unittest.main()
