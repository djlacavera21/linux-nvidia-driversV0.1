"""Official NVIDIA GPU support database ingestion and PCI classification."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.request import urlopen

from .config import DriverConfig
from .system import NvidiaDevice

_HEX4 = re.compile(r"^[0-9A-Fa-f]{4}$")


@dataclass(frozen=True)
class GpuRecord:
    product_name: str
    device_id: str
    subsystem_vendor_id: str | None = None
    subsystem_device_id: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class GpuClassification:
    address: str
    status: str
    product_name: str | None
    device_id: str
    subsystem_vendor_id: str
    subsystem_device_id: str
    match_specificity: str | None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def upstream_readme_url(config: DriverConfig) -> str:
    repo = config.upstream_repo.removesuffix(".git")
    return f"{repo}/raw/refs/tags/{config.version}/README.md"


def default_database_path(config: DriverConfig) -> Path:
    return Path.home() / ".cache" / "nvlx" / f"gpu-support-{config.version}.json"


def parse_supported_gpu_table(markdown: str) -> list[GpuRecord]:
    """Parse NVIDIA's Compatible GPUs Markdown table from the official README."""
    records: list[GpuRecord] = []
    in_section = False
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line == "## Compatible GPUs":
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("## ") and line != "## Compatible GPUs":
            break
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        name, pci = cells
        tokens = pci.split()
        if len(tokens) not in (1, 3) or not all(_HEX4.fullmatch(token) for token in tokens):
            continue
        records.append(
            GpuRecord(
                product_name=name,
                device_id=tokens[0].lower(),
                subsystem_vendor_id=tokens[1].lower() if len(tokens) == 3 else None,
                subsystem_device_id=tokens[2].lower() if len(tokens) == 3 else None,
            )
        )
    return records


def sync_gpu_database(path: Path, config: DriverConfig) -> int:
    url = upstream_readme_url(config)
    with urlopen(url, timeout=20) as response:  # nosec B310: fixed HTTPS GitHub URL derived from config
        markdown = response.read().decode("utf-8")
    records = parse_supported_gpu_table(markdown)
    if not records:
        raise RuntimeError("official NVIDIA README yielded no supported GPU records")
    payload = {
        "schema": 1,
        "driver_version": config.version,
        "source": url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": [record.to_dict() for record in records],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return len(records)


def load_gpu_database(path: Path, config: DriverConfig) -> list[GpuRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("driver_version") != config.version:
        raise RuntimeError(
            f"GPU database is for driver {payload.get('driver_version')}, expected {config.version}; run gpu-db-sync"
        )
    return [GpuRecord(**record) for record in payload.get("records", [])]


def _clean(value: str) -> str:
    return value.lower().removeprefix("0x")


def classify_device(device: NvidiaDevice, records: list[GpuRecord]) -> GpuClassification:
    device_id = _clean(device.device_id)
    subvendor = _clean(device.subsystem_vendor_id)
    subdevice = _clean(device.subsystem_device_id)

    specific = [
        record
        for record in records
        if record.device_id == device_id
        and record.subsystem_vendor_id == subvendor
        and record.subsystem_device_id == subdevice
    ]
    generic = [record for record in records if record.device_id == device_id and record.subsystem_vendor_id is None]
    match = specific[0] if specific else (generic[0] if generic else None)
    return GpuClassification(
        address=device.address,
        status="supported" if match else "unknown",
        product_name=match.product_name if match else None,
        device_id=device.device_id,
        subsystem_vendor_id=device.subsystem_vendor_id,
        subsystem_device_id=device.subsystem_device_id,
        match_specificity="subsystem" if specific else ("device" if generic else None),
    )


def classify_devices(devices: list[NvidiaDevice], records: list[GpuRecord]) -> list[GpuClassification]:
    return [classify_device(device, records) for device in devices]
