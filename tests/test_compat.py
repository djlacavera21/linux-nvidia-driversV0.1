import unittest
from unittest.mock import patch

from nvlx.compat import compatibility_report


class CompatibilityTests(unittest.TestCase):
    @patch("nvlx.compat.shutil.which", side_effect=lambda name: f"/usr/bin/{name}" if name in {"docker", "podman"} else None)
    @patch("nvlx.compat._package_versions", return_value=(
        ("nvidia-container-toolkit", "1.20.0-1"),
        ("nvidia-container-toolkit-base", "1.20.0-1"),
        ("libnvidia-container-tools", "1.20.0-1"),
        ("libnvidia-container1", "1.20.0-1"),
    ))
    @patch("nvlx.compat.detect_container_toolkit_version", return_value="1.20.0")
    @patch("nvlx.compat.detect_cuda_toolkit_version", return_value="13.3")
    @patch("nvlx.compat.nvidia_smi_driver_version", return_value="610.57.04")
    def test_cuda_13_is_compatible_with_610_and_container_packages_align(self, *_mocks) -> None:
        report = compatibility_report()
        self.assertTrue(report.cuda_compatible)
        self.assertTrue(report.container_packages_aligned)
        self.assertIn("known cuda-compat-mode issue", report.container_detail)
        self.assertTrue(report.docker_available)
        self.assertTrue(report.podman_available)

    @patch("nvlx.compat._package_versions", return_value=())
    @patch("nvlx.compat.detect_container_toolkit_version", return_value=None)
    @patch("nvlx.compat.detect_cuda_toolkit_version", return_value="13.0")
    @patch("nvlx.compat.nvidia_smi_driver_version", return_value="570.0")
    def test_cuda_13_rejects_driver_below_580(self, *_mocks) -> None:
        report = compatibility_report()
        self.assertFalse(report.cuda_compatible)
        self.assertIn("requires driver >= 580", report.cuda_detail)


if __name__ == "__main__":
    unittest.main()
