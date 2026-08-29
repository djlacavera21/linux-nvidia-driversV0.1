from __future__ import annotations
import unittest
from unittest.mock import patch
from nvlx.fabric import domain_labels
from nvlx.admission import policy
from nvlx.dra import validate

class V07Tests(unittest.TestCase):
    def test_fabric_domains_are_deterministic(self):
        self.assertEqual(domain_labels(["gpu03","gpu01","gpu02"],2),{"gpu01":"fabric-000","gpu02":"fabric-000","gpu03":"fabric-001"})
    def test_admission_policy_fails_closed(self):
        self.assertEqual(policy()["spec"]["failurePolicy"],"Fail")
    @patch("nvlx.dra._get")
    def test_dra_and_clusterpolicy_cannot_coexist(self,get):
        get.side_effect=lambda r:{"items":[{}]} if r in {"gpuclusters.nvidia.com","clusterpolicies.nvidia.com"} else {"items":[]}
        r=validate(); self.assertFalse(r.valid); self.assertIn("must not coexist",r.reasons[0])

if __name__=="__main__": unittest.main()
