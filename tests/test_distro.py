import unittest

from nvlx.distro import build_distro_plan


class DistroPlanTests(unittest.TestCase):
    def test_ubuntu_2604_is_nvidia_validated(self) -> None:
        plan = build_distro_plan({"ID": "ubuntu", "VERSION_ID": "26.04"})
        self.assertEqual(plan.adapter, "ubuntu")
        self.assertEqual(plan.package_manager, "apt")
        self.assertTrue(plan.nvidia_validated)
        self.assertIn("sudo apt install -y nvidia-open", plan.open_driver)

    def test_rhel_9_uses_open_dkms_stream(self) -> None:
        plan = build_distro_plan({"ID": "rhel", "VERSION_ID": "9.7"})
        self.assertTrue(plan.nvidia_validated)
        self.assertIn("sudo dnf module enable -y nvidia-driver:open-dkms", plan.dkms)

    def test_arch_is_supported_adapter_but_not_nvidia_validated(self) -> None:
        plan = build_distro_plan({"ID": "arch", "VERSION_ID": "rolling"})
        self.assertEqual(plan.adapter, "arch")
        self.assertFalse(plan.nvidia_validated)
        self.assertIn("sudo pacman -S --needed nvidia-open-dkms nvidia-utils", plan.dkms)

    def test_nixos_is_declarative(self) -> None:
        plan = build_distro_plan({"ID": "nixos", "VERSION_ID": "26.05"})
        self.assertEqual(plan.package_manager, "nix")
        self.assertFalse(plan.nvidia_validated)
        self.assertIn("hardware.nvidia.open = true", plan.open_driver[0])


if __name__ == "__main__":
    unittest.main()
