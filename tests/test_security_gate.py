import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import check_nvidia_security as gate


class NvidiaSecurityGateTests(unittest.TestCase):
    def config(self, directory: str, *, baseline: str = "base") -> Path:
        path = Path(directory) / "security-baseline.json"
        path.write_text(
            json.dumps(
                {
                    "repository": "NVIDIA/product-security",
                    "baseline_commit": baseline,
                    "relevant_terms": ["GPU Operator", "DCGM"],
                }
            ),
            encoding="utf-8",
        )
        return path

    def run_check(self, files, texts=()):
        def fake_json(url):
            if url.endswith("/branches/main"):
                return {"commit": {"sha": "head"}}
            return {"status": "ahead", "files": files}

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(gate, "_json", side_effect=fake_json):
                with patch.object(gate, "_text", side_effect=texts) as fetch:
                    result = gate.check(self.config(directory))
        return result, fetch

    def test_matching_baseline_passes_without_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.config(directory, baseline="same")
            with patch.object(
                gate, "_json", return_value={"commit": {"sha": "same"}}
            ) as fetch:
                result = gate.check(config)
        self.assertTrue(result["passed"])
        self.assertEqual(fetch.call_count, 1)

    def test_unrelated_index_addition_ignores_relevant_context(self):
        files = [
            {
                "filename": "2026/CVE_index.md",
                "status": "modified",
                "patch": (
                    "@@ -10,2 +10,3 @@\n"
                    " | old | NVIDIA DCGM |\n"
                    "+| new | Megatron Bridge |"
                ),
            }
        ]
        result, fetch = self.run_check(files)
        self.assertTrue(result["passed"])
        fetch.assert_not_called()

    def test_relevant_changed_index_line_fails(self):
        files = [
            {
                "filename": "2026/CVE_index.md",
                "status": "modified",
                "patch": "@@ -1 +1 @@\n-| old |\n+| CVE | GPU Operator |",
            }
        ]
        result, _ = self.run_check(files)
        self.assertFalse(result["passed"])
        self.assertEqual(result["relevant_changes"][0]["terms"], ["GPU Operator"])

    def test_unrelated_added_bulletin_passes(self):
        files = [{"filename": "2026/5868/5868.md", "status": "added"}]
        result, _ = self.run_check(files, texts=["Megatron Bridge 0.5.1"])
        self.assertTrue(result["passed"])

    def test_relevant_added_bulletin_fails(self):
        files = [{"filename": "2026/6000/6000.md", "status": "added"}]
        result, _ = self.run_check(files, texts=["NVIDIA GPU Operator update"])
        self.assertFalse(result["passed"])
        self.assertEqual(result["relevant_changes"][0]["path"], "2026/6000/6000.md")

    def test_dedicated_bulletin_change_uses_full_context(self):
        files = [
            {
                "filename": "2026/6000/6000.md",
                "status": "modified",
                "patch": "@@ -8 +8 @@\n-1.0\n+1.1",
            }
        ]
        result, fetch = self.run_check(
            files,
            texts=["GPU Operator\nAffected: 1.0", "GPU Operator\nFixed: 1.1"],
        )
        self.assertFalse(result["passed"])
        self.assertEqual(fetch.call_count, 2)

    def test_missing_aggregate_patch_is_reconstructed(self):
        files = [{"filename": "2026/README.md", "status": "modified"}]
        result, fetch = self.run_check(
            files,
            texts=["Megatron Bridge", "Megatron Bridge\nGPU Operator"],
        )
        self.assertFalse(result["passed"])
        self.assertEqual(fetch.call_count, 2)

    def test_non_ancestral_baseline_fails_closed(self):
        def fake_json(url):
            if url.endswith("/branches/main"):
                return {"commit": {"sha": "head"}}
            return {"status": "diverged", "files": []}

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(gate, "_json", side_effect=fake_json):
                with self.assertRaisesRegex(RuntimeError, "not an ancestor"):
                    gate.check(self.config(directory))

    def test_text_fetch_failure_propagates(self):
        files = [{"filename": "2026/6000/6000.md", "status": "added"}]
        with self.assertRaisesRegex(OSError, "network unavailable"):
            self.run_check(files, texts=OSError("network unavailable"))


if __name__ == "__main__":
    unittest.main()
