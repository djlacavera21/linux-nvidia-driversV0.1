from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from nvlx.build import BuildError, source_version, validate_runtime_alignment, validate_source
from nvlx.config import DEFAULT, DriverConfig


class SourceValidationTests(unittest.TestCase):
    def _make_source(self, root: Path, version: str) -> Path:
        source = root / "open-gpu-kernel-modules"
        source.mkdir()
        (source / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
        (source / "kernel-open").mkdir()
        (source / "version.mk").write_text(f"NVIDIA_VERSION = {version}\n", encoding="utf-8")
        return source

    def test_reads_upstream_version_mk(self) -> None:
        with TemporaryDirectory() as tmp:
            source = self._make_source(Path(tmp), DEFAULT.version)
            self.assertEqual(source_version(source), DEFAULT.version)

    def test_refuses_version_mismatch(self) -> None:
        with TemporaryDirectory() as tmp:
            source = self._make_source(Path(tmp), "999.0")
            with self.assertRaises(BuildError):
                validate_source(source, DEFAULT)

    def test_accepts_matching_source(self) -> None:
        with TemporaryDirectory() as tmp:
            config = DriverConfig(
                version="123.45",
                upstream_repo="https://example.invalid/repo.git",
                minimum_kernel="4.15",
                architectures=("x86_64",),
                open_module_gpu_floor="Turing or newer",
            )
            source = self._make_source(Path(tmp), config.version)
            validate_source(source, config)


class RuntimeAlignmentTests(unittest.TestCase):
    @patch("nvlx.build.nvidia_smi_driver_version", return_value=DEFAULT.version)
    def test_accepts_matching_runtime(self, _mock_version) -> None:
        validate_runtime_alignment(DEFAULT)

    @patch("nvlx.build.nvidia_smi_driver_version", return_value="999.0")
    def test_refuses_mixed_runtime(self, _mock_version) -> None:
        with self.assertRaises(BuildError):
            validate_runtime_alignment(DEFAULT)

    @patch("nvlx.build.nvidia_smi_driver_version", return_value=None)
    def test_allows_absent_runtime(self, _mock_version) -> None:
        validate_runtime_alignment(DEFAULT)


if __name__ == "__main__":
    unittest.main()
