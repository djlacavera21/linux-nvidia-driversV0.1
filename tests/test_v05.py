from unittest.mock import patch
import unittest
from nvlx.gpu_operator import gpu_operator_plan
from nvlx.immutable import immutable_plan
from nvlx.package_state import PackageRecord, PackageSnapshot
from nvlx.rollback_preflight import check_rollback_availability
from nvlx.watchdog import WatchdogPolicy, render_service
from nvlx.config import DEFAULT
from nvlx.dcgm_telemetry import _bus, _int

class RollbackPreflightTests(unittest.TestCase):
    def test_unknown_manager_refuses_false_confidence(self):
        snap=PackageSnapshot("mystery","x",(PackageRecord("nvidia-driver","1"),))
        report=check_rollback_availability(snap)
        self.assertFalse(report.available)
        self.assertEqual(report.checked,1)

class WatchdogTests(unittest.TestCase):
    def test_retry_policy_is_rendered(self):
        text=render_service(WatchdogPolicy(retries=4,restart_sec=15,timeout_sec=80,start_limit_sec=240))
        self.assertIn("StartLimitBurst=4",text)
        self.assertIn("RestartSec=15",text)
        self.assertIn("TimeoutStartSec=80",text)

class ImmutableTests(unittest.TestCase):
    def test_rhcos_is_validated_operator_path(self):
        plan=immutable_plan({"ID":"rhcos"})
        self.assertTrue(plan.immutable)
        self.assertTrue(plan.nvidia_validated)

class GpuOperatorTests(unittest.TestCase):
    @patch("nvlx.gpu_operator.shutil.which",return_value=None)
    @patch("nvlx.gpu_operator.read_os_release",return_value={"ID":"ubuntu"})
    def test_plan_pins_operator_and_driver(self,_os,_which):
        plan=gpu_operator_plan(DEFAULT,mig_strategy="mixed")
        joined=" ".join(plan.helm_command)
        self.assertIn("v26.7.0",joined)
        self.assertIn(DEFAULT.version,joined)
        self.assertIn("mig.strategy=mixed",joined)

class TelemetryParsingTests(unittest.TestCase):
    def test_pci_domain_normalization(self): self.assertEqual(_bus("00000000:65:00.0"),"0000:65:00.0")
    def test_na_integer(self): self.assertIsNone(_int("N/A"))

if __name__=="__main__": unittest.main()
