"""Command-line interface for nvlx."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sys

from . import __version__
from .build import BuildError, build_modules, fetch_source, install_modules
from .config import load_driver_config
from .doctor import has_failures, run_doctor
from .system import host_snapshot


def _print_checks() -> int:
    checks = run_doctor()
    width = max(len(check.name) for check in checks)
    for check in checks:
        print(f"{check.status.upper():5}  {check.name:<{width}}  {check.detail}")
    return 2 if has_failures(checks) else 0


def cmd_detect(args: argparse.Namespace) -> int:
    snapshot = host_snapshot(Path(args.sysfs_root))
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    return _print_checks()


def cmd_plan(_: argparse.Namespace) -> int:
    config = load_driver_config()
    snapshot = host_snapshot()
    arch = platform.machine()
    arch_ok = arch in config.architectures

    print(f"Driver release:        {config.version}")
    print(f"Upstream source:       {config.upstream_repo}")
    print(f"Host architecture:     {arch}")
    print(f"Architecture support:  {'yes' if arch_ok else 'no'}")
    print(f"Open-module GPU floor: {config.open_module_gpu_floor}")
    print(f"Detected NVIDIA PCI:   {len(snapshot['nvidia_devices'])}")
    print("GPU eligibility:       verify the detected PCI ID against the pinned upstream supported-GPU list")
    print("Userspace requirement: install matching NVIDIA user-space/GSP components from the same release")
    print()
    doctor_status = _print_checks()
    if not arch_ok:
        print(f"\nFAIL   architecture {arch!r} is outside the configured build targets", file=sys.stderr)
        return 2
    return doctor_status


def cmd_fetch(args: argparse.Namespace) -> int:
    config = load_driver_config()
    fetch_source(Path(args.dest), config)
    print(f"Fetched NVIDIA open GPU kernel modules {config.version} into {args.dest}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    config = load_driver_config()
    build_modules(Path(args.source), config, jobs=args.jobs)
    print(f"Built NVIDIA kernel modules for release {config.version}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    config = load_driver_config()
    install_modules(Path(args.source), config, confirmed=args.yes, jobs=args.jobs)
    print(f"Installed NVIDIA kernel modules for release {config.version}; reboot or perform a controlled module transition")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nvlx", description="Linux NVIDIA driver build and diagnostics toolkit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    detect = sub.add_parser("detect", help="print a JSON snapshot of the Linux/NVIDIA host")
    detect.add_argument("--sysfs-root", default="/sys/bus/pci/devices", help="alternate PCI sysfs root for testing")
    detect.set_defaults(func=cmd_detect)

    doctor = sub.add_parser("doctor", help="run build/install preflight checks")
    doctor.set_defaults(func=cmd_doctor)

    plan = sub.add_parser("plan", help="show the configured driver path and preflight state")
    plan.set_defaults(func=cmd_plan)

    fetch = sub.add_parser("fetch", help="clone the pinned NVIDIA open-kernel-module source")
    fetch.add_argument("--dest", default="vendor/open-gpu-kernel-modules")
    fetch.set_defaults(func=cmd_fetch)

    build = sub.add_parser("build", help="build kernel modules from a pinned source tree")
    build.add_argument("--source", required=True)
    build.add_argument("--jobs", type=int, default=None)
    build.set_defaults(func=cmd_build)

    install = sub.add_parser("install", help="install already-built kernel modules")
    install.add_argument("--source", required=True)
    install.add_argument("--jobs", type=int, default=None)
    install.add_argument("--yes", action="store_true", help="acknowledge the guarded installation step")
    install.set_defaults(func=cmd_install)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BuildError as exc:
        print(f"nvlx: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("nvlx: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
