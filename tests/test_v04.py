from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json, unittest

from nvlx.config import DEFAULT
from nvlx.package_state import PackageRecord, PackageSnapshot, restore_commands
from nvlx.session import session_report
from nvlx.topology import topology_report
from nvlx.transaction import Transaction, validate_pending

class PackageStateTests(unittest.TestCase):
    def test_apt_restore_pins_exact_versions(self):
        snap=PackageSnapshot("apt","ubuntu",(PackageRecord("nvidia-open","610.57.04-1"),PackageRecord("cuda-toolkit","13.0-1")))
        command=restore_commands(snap)[0]
        self.assertEqual(command[:3],["apt-get","install","-y"])
        self.assertIn("nvidia-open=610.57.04-1",command)

class SessionTests(unittest.TestCase):
    @patch("nvlx.session._ldconfig_has",return_value=True)
    @patch("nvlx.session._param",return_value="Y")
    def test_wayland_with_kms_and_libraries_is_clean(self,_param,_ld):
        with patch.dict("os.environ",{"XDG_SESSION_TYPE":"wayland","WAYLAND_DISPLAY":"wayland-0"},clear=True):
            report=session_report()
        self.assertEqual(report.session_type,"wayland")
        self.assertNotIn("modeset", " ".join(report.warnings).lower())

class TopologyTests(unittest.TestCase):
    def test_nvlink_matrix_counts_symmetric_edge_once(self):
        topo="""        GPU0 GPU1 CPU Affinity\nGPU0     X    NV4  0-31\nGPU1    NV4   X    0-31\n"""
        names="0, NVIDIA A100, 00000000:01:00.0\n1, NVIDIA A100, 00000000:02:00.0"
        with patch("nvlx.topology._run",side_effect=[topo,names]):
            report=topology_report()
        self.assertEqual(report.gpu_count,2)
        self.assertEqual(report.nvlink_edges,1)

class TransactionTests(unittest.TestCase):
    def test_pending_transaction_validates_after_reboot(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            tx=Transaction("tx1","now","test-kernel","600.1",DEFAULT.version,"/tmp/rollback","/tmp/packages","old-boot","pending-reboot")
            (root/"pending.json").write_text(json.dumps(tx.to_dict()),encoding="utf-8")
            with patch("nvlx.transaction.nvidia_smi_driver_version",return_value=DEFAULT.version), patch("nvlx.transaction.loaded_modules",return_value={"nvidia"}), patch("nvlx.transaction._boot_id",return_value="new-boot"):
                result,ok,message=validate_pending(root=root)
            self.assertTrue(ok)
            self.assertEqual(result.state,"validated")
            self.assertFalse((root/"pending.json").exists())

    def test_same_boot_does_not_validate(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            tx=Transaction("tx1","now","test-kernel","600.1",DEFAULT.version,"/tmp/rollback","/tmp/packages","same-boot","pending-reboot")
            (root/"pending.json").write_text(json.dumps(tx.to_dict()),encoding="utf-8")
            with patch("nvlx.transaction.nvidia_smi_driver_version",return_value=DEFAULT.version), patch("nvlx.transaction.loaded_modules",return_value={"nvidia"}), patch("nvlx.transaction._boot_id",return_value="same-boot"):
                result,ok,message=validate_pending(root=root)
            self.assertFalse(ok)
            self.assertIn("reboot",message)

if __name__=="__main__": unittest.main()
