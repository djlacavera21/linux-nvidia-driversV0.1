import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from nvlx.rollback import list_snapshots
from nvlx.secureboot import enroll_command, find_built_modules


class SecureBootHelperTests(unittest.TestCase):
    def test_discovers_only_built_ko_files(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kernel-open").mkdir()
            (root / "kernel-open" / "nvidia.ko").write_bytes(b"module")
            (root / "kernel-open" / "README").write_text("ignore", encoding="utf-8")
            modules = find_built_modules(root)
            self.assertEqual([path.name for path in modules], ["nvidia.ko"])

    def test_mok_enrollment_command_uses_supplied_certificate(self) -> None:
        self.assertEqual(enroll_command(Path("/root/mok/MOK.der")), "sudo mokutil --import /root/mok/MOK.der")


class RollbackManifestTests(unittest.TestCase):
    def test_lists_valid_snapshot_manifests(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "20260829T120000Z"
            snapshot.mkdir()
            payload = {
                "snapshot_id": "20260829T120000Z",
                "kernel": "7.2.0-test",
                "created_at": "2026-08-29T12:00:00+00:00",
                "root": str(snapshot),
                "files": ["updates/nvidia.ko"],
            }
            (snapshot / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
            rows = list_snapshots(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].kernel, "7.2.0-test")
            self.assertEqual(rows[0].files, ("updates/nvidia.ko",))


if __name__ == "__main__":
    unittest.main()
