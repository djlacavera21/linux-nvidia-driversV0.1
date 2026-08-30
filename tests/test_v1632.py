import unittest
from unittest.mock import patch

from nvlx.nvidia_continuity_v1632 import snapshot_identity
from nvlx.nvidia_inventory_v163 import NvidiaPreflight, NvidiaSnapshot
from nvlx.runtime_v163 import Runtime as RuntimeV163
from nvlx.runtime_v1632 import Runtime


def o(name, uid, api="nvidia.com/v1"):
    return {"apiVersion":api,"metadata":{"name":name,"uid":uid,"resourceVersion":"7"}}


def snap(*, policy_uid="p1", node_uid="n1", api_versions=(("nvidia.com","v1"),), resources=(("nvidia.com",("clusterpolicies",)),)):
    return NvidiaSnapshot(
        (), (o("cluster-policy",policy_uid),), (), (), (),
        (o("gpu-1",node_uid,"v1"),), tuple(api_versions), tuple(resources)
    )


def pf(snapshot): return NvidiaPreflight(True,"device-plugin",(),snapshot)


class SnapshotIdentityTests(unittest.TestCase):
    def test_resource_versions_do_not_affect_identity(self):
        a=snap(); b=snap(); b.clusterpolicies[0]["metadata"]["resourceVersion"]="99"
        self.assertEqual(snapshot_identity(a),snapshot_identity(b))

    def test_uid_and_api_mapping_affect_identity(self):
        self.assertNotEqual(snapshot_identity(snap()),snapshot_identity(snap(policy_uid="p2")))
        self.assertNotEqual(snapshot_identity(snap()),snapshot_identity(snap(api_versions=(("nvidia.com","v1alpha1"),))))


class RuntimeContinuityTests(unittest.TestCase):
    def runtime(self, results):
        r=Runtime(object(),"pod-a",leader_check=lambda:True)
        it=iter(results); r.nvidia_inventory_check=lambda: next(it)
        return r

    def test_first_snapshot_establishes_baseline(self):
        r=self.runtime([pf(snap())])
        with patch.object(RuntimeV163,"list_and_watch_once",return_value="eof"):
            self.assertEqual(r.list_and_watch_once(),"eof")
        self.assertIsNotNone(r.nvidia_identity_baseline)

    def test_uid_change_is_fenced_then_promoted_after_identical_confirmation(self):
        r=self.runtime([pf(snap()),pf(snap(policy_uid="p2")),pf(snap(policy_uid="p2"))])
        with patch.object(RuntimeV163,"list_and_watch_once",return_value="eof"):
            self.assertEqual(r.list_and_watch_once(),"eof")
            self.assertEqual(r.list_and_watch_once(),"relist")
            self.assertEqual(r.nvidia_preflight_mode,"continuity-fenced")
            self.assertFalse(r.stats.inventory_fresh)
            self.assertEqual(r.list_and_watch_once(),"eof")
        self.assertEqual(r.nvidia_continuity_promotions,1)

    def test_candidate_churn_never_promotes(self):
        r=self.runtime([pf(snap()),pf(snap(policy_uid="p2")),pf(snap(policy_uid="p3"))])
        with patch.object(RuntimeV163,"list_and_watch_once",return_value="eof"):
            self.assertEqual(r.list_and_watch_once(),"eof")
            self.assertEqual(r.list_and_watch_once(),"relist")
            self.assertEqual(r.list_and_watch_once(),"relist")
        self.assertEqual(r.nvidia_continuity_promotions,0)
        self.assertEqual(r.nvidia_continuity_fences,2)

    def test_return_to_baseline_clears_candidate(self):
        r=self.runtime([pf(snap()),pf(snap(policy_uid="p2")),pf(snap())])
        with patch.object(RuntimeV163,"list_and_watch_once",return_value="eof"):
            self.assertEqual(r.list_and_watch_once(),"eof")
            self.assertEqual(r.list_and_watch_once(),"relist")
            self.assertEqual(r.list_and_watch_once(),"eof")
        self.assertIsNone(r.nvidia_identity_candidate)

    def test_gpu_node_membership_change_is_fenced(self):
        r=self.runtime([pf(snap()),pf(snap(node_uid="n2"))])
        with patch.object(RuntimeV163,"list_and_watch_once",return_value="eof"):
            self.assertEqual(r.list_and_watch_once(),"eof")
            self.assertEqual(r.list_and_watch_once(),"relist")
        self.assertIn("gpu_nodes",r.nvidia_continuity_changes)


if __name__ == "__main__": unittest.main()
