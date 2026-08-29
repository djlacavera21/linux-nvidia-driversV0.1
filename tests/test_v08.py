from __future__ import annotations
import unittest
from nvlx.placement import plan as placement
from nvlx.gang import plan as gang
from nvlx.mig_broker import plan as mig
from nvlx.power_policy import plan as power
from nvlx.evacuation import plan as evacuate
from nvlx.federation import ClusterTarget, plan as federation

class V08Tests(unittest.TestCase):
    def test_placement_selectors(self):
        p=placement(count=2,product="H100",min_memory_gib=80,compute_domain="rack-a")
        self.assertEqual(p.count,2); self.assertIn("product",p.selectors[0]); self.assertIn("ComputeDomain",p.manifest)
    def test_gang_defaults_all_or_nothing(self):
        p=gang(4,8,compute_domain="rack-a"); self.assertTrue(p.requires_all_or_nothing); self.assertEqual(p.min_available,4)
    def test_dynamic_mig_conflict(self):
        p=mig(profile="1g.10gb",dynamic=True,enabled_feature_gates=["MPSSupport"]); self.assertFalse(p.valid); self.assertIn("MPSSupport",p.reasons[0])
    def test_power_policy_validation(self):
        self.assertTrue(power(max_watts=700,max_temp_c=85).valid); self.assertFalse(power(max_temp_c=120).valid)
    def test_evacuation_is_explicit(self):
        p=evacuate("gpu01"); self.assertEqual(p.checkpoint_mode,"application"); self.assertEqual(p.commands[0][-1],"gpu01")
    def test_federation_capacity(self):
        clusters=[ClusterTarget("a","east",8),ClusterTarget("b","west",16),ClusterTarget("c","central",4)]
        p=federation(clusters,primary="a",required_gpus=8); self.assertTrue(p.valid); self.assertEqual(p.failover_order,("b",))

if __name__=="__main__": unittest.main()
