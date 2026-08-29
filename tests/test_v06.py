from __future__ import annotations
import unittest
from nvlx.alerts import prometheus_rule_group
from nvlx.maintenance import plan as maintenance_plan
from nvlx.quarantine import plan as quarantine_plan
from nvlx.rollout import advancement_allowed, plan_waves
from nvlx.security_gate import evaluate_dcgm_exporter

class V06Tests(unittest.TestCase):
    def test_canary_wave_first(self):
        waves=plan_waves(["gpu03","gpu01","gpu02","gpu04"],canary_count=1,wave_size=2)
        self.assertTrue(waves[0].canary); self.assertEqual(waves[0].nodes,("gpu01",)); self.assertEqual(waves[1].nodes,("gpu02","gpu03"))
    def test_advancement_blocks_quarantine(self):
        ok,reasons=advancement_allowed(qualified=True,diagnostics_passed=True,security_gate_passed=True,quarantined=1)
        self.assertFalse(ok); self.assertIn("quarantined",reasons[0])
    def test_dcgm_security_gate(self):
        self.assertTrue(evaluate_dcgm_exporter("4.8.1").blocked); self.assertFalse(evaluate_dcgm_exporter("4.8.3").blocked)
    def test_maintenance_plan(self):
        p=maintenance_plan("gpu01"); self.assertIn("drain",p.drain); self.assertIn("--ignore-daemonsets",p.drain)
    def test_quarantine_plan(self):
        p=quarantine_plan("gpu01","Xid 79"); self.assertIn("NoSchedule"," ".join(p.taint_command))
    def test_alerts_have_xid_and_ecc(self):
        text=prometheus_rule_group(); self.assertIn("NvlxGpuXidError",text); self.assertIn("NvlxGpuUncorrectedEcc",text)

if __name__=="__main__": unittest.main()
