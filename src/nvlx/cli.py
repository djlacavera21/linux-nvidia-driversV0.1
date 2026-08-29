"""Command-line interface for nvlx."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys

from . import __version__
from .build import BuildError, build_modules, fetch_source, install_modules
from .compat import compatibility_report
from .config import load_driver_config
from .distro import build_distro_plan
from .dkms import dkms_state
from .doctor import has_failures, run_doctor
from .gpu_db import classify_devices, default_database_path, load_gpu_database, sync_gpu_database
from .rollback import apply_snapshot, create_snapshot, list_snapshots
from .secureboot import enroll_command, generate_mok, secure_boot_plan, sign_modules
from .system import detect_nvidia_devices, host_snapshot


def _print_checks() -> int:
    checks = run_doctor()
    width = max(len(check.name) for check in checks)
    for check in checks:
        print(f"{check.status.upper():5}  {check.name:<{width}}  {check.detail}")
    return 2 if has_failures(checks) else 0


def _json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def cmd_detect(args: argparse.Namespace) -> int:
    _json(host_snapshot(Path(args.sysfs_root)))
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
    print(f"Distro adapter:        {build_distro_plan().adapter}")
    print("GPU eligibility:       use gpu-db-sync once, then gpu-support for official PCI classification")
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


def cmd_gpu_db_sync(args: argparse.Namespace) -> int:
    config = load_driver_config()
    path = Path(args.path) if args.path else default_database_path(config)
    count = sync_gpu_database(path, config)
    print(f"Synced {count} official NVIDIA GPU support records for {config.version} to {path}")
    return 0


def cmd_gpu_support(args: argparse.Namespace) -> int:
    config = load_driver_config()
    path = Path(args.database) if args.database else default_database_path(config)
    if not path.is_file():
        raise BuildError(f"GPU support database not found: {path}; run nvlx gpu-db-sync")
    records = load_gpu_database(path, config)
    devices = detect_nvidia_devices(Path(args.sysfs_root))
    _json([classification.to_dict() for classification in classify_devices(devices, records)])
    return 0 if devices else 1


def cmd_distro_plan(_: argparse.Namespace) -> int:
    _json(build_distro_plan().to_dict())
    return 0


def cmd_dkms_status(_: argparse.Namespace) -> int:
    _json(dkms_state().to_dict())
    return 0


def cmd_secureboot_plan(_: argparse.Namespace) -> int:
    _json(secure_boot_plan().to_dict())
    return 0


def cmd_secureboot_keygen(args: argparse.Namespace) -> int:
    key, cert = generate_mok(Path(args.key_dir), args.common_name, confirmed=args.yes)
    print(f"Generated private key: {key}")
    print(f"Generated DER certificate: {cert}")
    print(f"Enroll with: {enroll_command(cert)}")
    print("Enrollment completes through the firmware MOK screen after reboot.")
    return 0


def cmd_secureboot_sign(args: argparse.Namespace) -> int:
    count = sign_modules(
        Path(args.source),
        Path(args.key),
        Path(args.cert),
        confirmed=args.yes,
        kernel=args.kernel,
    )
    print(f"Signed {count} built NVIDIA kernel modules")
    return 0


def cmd_rollback_snapshot(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    snapshot = create_snapshot(root=root, kernel=args.kernel)
    _json(snapshot.to_dict())
    return 0


def cmd_rollback_list(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else None
    _json([snapshot.to_dict() for snapshot in list_snapshots(root)])
    return 0


def cmd_rollback_apply(args: argparse.Namespace) -> int:
    snapshot = apply_snapshot(Path(args.snapshot), confirmed=args.yes)
    print(f"Restored NVIDIA module snapshot {snapshot.snapshot_id} for kernel {snapshot.kernel}")
    print("Reboot or perform a controlled module transition before validating the restored driver.")
    return 0


def cmd_compat(_: argparse.Namespace) -> int:
    report = compatibility_report()
    _json(report.to_dict())
    if report.cuda_compatible is False or report.container_packages_aligned is False:
        return 2
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

    gpu_sync = sub.add_parser("gpu-db-sync", help="sync the official NVIDIA supported-GPU table for the pinned release")
    gpu_sync.add_argument("--path", default=None)
    gpu_sync.set_defaults(func=cmd_gpu_db_sync)

    gpu_support = sub.add_parser("gpu-support", help="classify detected PCI devices against NVIDIA's official support table")
    gpu_support.add_argument("--database", default=None)
    gpu_support.add_argument("--sysfs-root", default="/sys/bus/pci/devices")
    gpu_support.set_defaults(func=cmd_gpu_support)

    distro = sub.add_parser("distro-plan", help="show the detected distribution adapter and package/DKMS plan")
    distro.set_defaults(func=cmd_distro_plan)

    dkms = sub.add_parser("dkms-status", help="inspect installed DKMS state and NVIDIA entries")
    dkms.set_defaults(func=cmd_dkms_status)

    sb_plan = sub.add_parser("secureboot-plan", help="inspect Secure Boot signing prerequisites")
    sb_plan.set_defaults(func=cmd_secureboot_plan)

    sb_keygen = sub.add_parser("secureboot-keygen", help="generate a local Machine Owner Key pair")
    sb_keygen.add_argument("--key-dir", required=True)
    sb_keygen.add_argument("--common-name", default="nvlx NVIDIA module signing")
    sb_keygen.add_argument("--yes", action="store_true")
    sb_keygen.set_defaults(func=cmd_secureboot_keygen)

    sb_sign = sub.add_parser("secureboot-sign", help="sign built .ko files with an enrolled Machine Owner Key")
    sb_sign.add_argument("--source", required=True)
    sb_sign.add_argument("--key", required=True)
    sb_sign.add_argument("--cert", required=True)
    sb_sign.add_argument("--kernel", default=None)
    sb_sign.add_argument("--yes", action="store_true")
    sb_sign.set_defaults(func=cmd_secureboot_sign)

    snapshot = sub.add_parser("rollback-snapshot", help="back up installed NVIDIA kernel modules")
    snapshot.add_argument("--root", default=None)
    snapshot.add_argument("--kernel", default=None)
    snapshot.set_defaults(func=cmd_rollback_snapshot)

    rollback_list = sub.add_parser("rollback-list", help="list available NVIDIA module rollback snapshots")
    rollback_list.add_argument("--root", default=None)
    rollback_list.set_defaults(func=cmd_rollback_list)

    rollback_apply = sub.add_parser("rollback-apply", help="restore a NVIDIA module rollback snapshot")
    rollback_apply.add_argument("snapshot")
    rollback_apply.add_argument("--yes", action="store_true")
    rollback_apply.set_defaults(func=cmd_rollback_apply)

    compat = sub.add_parser("compat", help="check NVIDIA driver, CUDA, and Container Toolkit compatibility")
    compat.set_defaults(func=cmd_compat)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (BuildError, RuntimeError, OSError, ValueError) as exc:
        print(f"nvlx: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"nvlx: command failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("nvlx: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
