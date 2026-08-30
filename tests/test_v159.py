import unittest
from nvlx.leadership_v155 import FenceToken
from nvlx.fence_sequence_v159 import assess, verify_floor

class V159Tests(unittest.TestCase):
    def test_initial_sequence_starts_at_one(self):
        r=assess(None,None,1,FenceToken("controller-a",1,"10"))
        self.assertTrue(r.allowed); self.assertEqual(r.action,"persist-initial")
        self.assertEqual(assess(None,None,2,FenceToken("controller-a",1,"10")).action,"reject-initial-sequence")

    def test_token_change_requires_sequence_advance(self):
        previous=FenceToken("controller-a",7,"42")
        candidate=FenceToken("controller-a",7,"43")
        self.assertEqual(assess(9,previous,9,candidate).action,"reject-sequence-replay")
        r=assess(9,previous,10,candidate)
        self.assertTrue(r.allowed); self.assertEqual(r.action,"persist-next")

    def test_sequence_rollback_is_rejected(self):
        r=assess(9,FenceToken("controller-a",7,"42"),8,FenceToken("controller-a",7,"43"))
        self.assertFalse(r.allowed); self.assertEqual(r.action,"reject-sequence-rollback")

    def test_sequence_gap_is_rejected(self):
        r=assess(9,FenceToken("controller-a",7,"42"),11,FenceToken("controller-a",7,"43"))
        self.assertFalse(r.allowed); self.assertEqual(r.action,"reject-sequence-gap"); self.assertEqual(r.next_sequence,10)

    def test_same_checkpoint_is_noop(self):
        token=FenceToken("controller-a",7,"42")
        r=assess(9,token,9,token)
        self.assertFalse(r.allowed); self.assertEqual(r.action,"noop")

    def test_unchanged_token_cannot_advance_sequence(self):
        token=FenceToken("controller-a",7,"42")
        r=assess(9,token,10,token)
        self.assertFalse(r.allowed); self.assertEqual(r.action,"reject-redundant-advance")

    def test_reacquire_still_requires_new_epoch(self):
        previous=FenceToken("controller-a",7,"42")
        stale=FenceToken("controller-a",7,"43")
        self.assertEqual(assess(9,previous,10,stale,reacquired=True).action,"reject-stale-reacquire")
        newer=FenceToken("controller-b",8,"44")
        self.assertTrue(assess(9,previous,10,newer,reacquired=True).allowed)

    def test_floor_detects_replayed_snapshot(self):
        r=verify_floor(8,9)
        self.assertFalse(r.allowed); self.assertEqual(r.action,"replay-detected")
        self.assertTrue(verify_floor(9,9).allowed)
        self.assertTrue(verify_floor(10,9).allowed)

if __name__ == "__main__": unittest.main()
