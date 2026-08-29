from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from nvlx.system import detect_nvidia_devices, secure_boot_enabled


class DetectNvidiaDevicesTests(unittest.TestCase):
    def test_filters_non_nvidia_pci_devices(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            nvidia = root / "0000:01:00.0"
            nvidia.mkdir()
            (nvidia / "vendor").write_text("0x10de\n", encoding="utf-8")
            (nvidia / "device").write_text("0x2684\n", encoding="utf-8")
            (nvidia / "class").write_text("0x030000\n", encoding="utf-8")

            other = root / "0000:00:02.0"
            other.mkdir()
            (other / "vendor").write_text("0x8086\n", encoding="utf-8")
            (other / "device").write_text("0x1234\n", encoding="utf-8")
            (other / "class").write_text("0x030000\n", encoding="utf-8")

            devices = detect_nvidia_devices(root)
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0].address, "0000:01:00.0")
            self.assertEqual(devices[0].device_id, "0x2684")

    def test_missing_sysfs_root_returns_empty_list(self) -> None:
        self.assertEqual(detect_nvidia_devices(Path("/definitely/not/here")), [])


class SecureBootTests(unittest.TestCase):
    def test_secure_boot_reads_last_efivar_byte(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "SecureBoot-test").write_bytes(b"\x07\x00\x00\x00\x01")
            self.assertTrue(secure_boot_enabled(root))

    def test_no_efivar_returns_unknown(self) -> None:
        with TemporaryDirectory() as tmp:
            self.assertIsNone(secure_boot_enabled(Path(tmp)))


if __name__ == "__main__":
    unittest.main()
