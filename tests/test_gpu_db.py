import unittest

from nvlx.config import DEFAULT
from nvlx.gpu_db import GpuRecord, classify_device, parse_supported_gpu_table, upstream_readme_url
from nvlx.system import NvidiaDevice


class GpuDatabaseTests(unittest.TestCase):
    def test_parses_generic_and_subsystem_rows(self) -> None:
        markdown = """# NVIDIA
## Compatible GPUs
| Product Name | PCI ID |
| --- | --- |
| NVIDIA GeForce RTX Test | 2B85 |
| NVIDIA Board Specific | 1E30 1028 129E |
## Next Section
"""
        records = parse_supported_gpu_table(markdown)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].device_id, "2b85")
        self.assertEqual(records[1].subsystem_vendor_id, "1028")
        self.assertEqual(records[1].subsystem_device_id, "129e")

    def test_subsystem_match_wins_over_generic_match(self) -> None:
        records = [
            GpuRecord("Generic", "1e30"),
            GpuRecord("Exact Board", "1e30", "1028", "129e"),
        ]
        device = NvidiaDevice(
            address="0000:01:00.0",
            vendor_id="0x10de",
            device_id="0x1e30",
            class_code="0x030000",
            subsystem_vendor_id="0x1028",
            subsystem_device_id="0x129e",
        )
        result = classify_device(device, records)
        self.assertEqual(result.status, "supported")
        self.assertEqual(result.product_name, "Exact Board")
        self.assertEqual(result.match_specificity, "subsystem")

    def test_unknown_device_is_not_claimed_unsupported(self) -> None:
        device = NvidiaDevice("0000:01:00.0", "0x10de", "0xffff", "0x030000")
        result = classify_device(device, [])
        self.assertEqual(result.status, "unknown")
        self.assertIsNone(result.product_name)

    def test_official_database_url_is_pinned_to_driver_release(self) -> None:
        url = upstream_readme_url(DEFAULT)
        self.assertEqual(
            url,
            "https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/610.57.04/README.md",
        )


if __name__ == "__main__":
    unittest.main()
