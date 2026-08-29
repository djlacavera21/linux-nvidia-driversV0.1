"""Command-line interface for nvlx."""
from __future__ import annotations
import argparse, json, platform, subprocess, sys
from pathlib import Path
from . import __version__
from .build import BuildError, build_modules, fetch_source, install_modules
from .compat import compatibility_report
from .config import load_driver_config
from .dcgm_telemetry import exporter_state, reliability_rows
from .distro import build_distro_plan
from .dkms import dkms_state
from .doctor import has_failures, run_doctor
from .gpu_db import classify_devices, default_database_path, load_gpu_database, sync_gpu_database
from .gpu_operator import gpu_operator_plan
from .health import health_report
from .immutable import immutable_plan
from .initramfs import initramfs_plan, regenerate_initramfs
from .mig import mig_fabric_report
from .mig_lifecycle import apply_mig_profile, plan_mig_profile
from .nvsdm import nvsdm_report
from .package_state import capture_package_state
from .prime import prime_report
from .report import write_report_bundle
from .repository import repository_plan
from .rollback import apply_snapshot, create_snapshot, list_snapshots
from .rollback_preflight import check_rollback_availability
from .secureboot import enroll_command, generate_mok, secure_boot_plan, sign_modules, verify_installed_modules
from .session import session_report
from .system import detect_nvidia_devices, host_snapshot
from .telemetry import json_health, prometheus_text
from .topology import topology_report
from .transaction import install_boot_guard, load_pending, validate_pending
from .watchdog import WatchdogPolicy

def _json(payload): print(json.dumps(payload,indent=2,sort_keys=True))
def _print_checks():
    checks=run_doctor(); width=max(len(c.name) for c in checks)
    for c in checks: print(f"{c.status.upper():5}  {c.name:<{width}}  {c.detail}")
    return 2 if has_failures(checks) else 0

def cmd_detect(a): _json(host_snapshot(Path(a.sysfs_root))); return 0
def cmd_doctor(_): return _print_checks()
def cmd_plan(_):
    c=load_driver_config(); s=host_snapshot(); arch=platform.machine(); ok=arch in c.architectures
    print(f"Driver release:        {c.version}\nUpstream source:       {c.upstream_repo}\nHost architecture:     {arch}\nArchitecture support:  {'yes' if ok else 'no'}\nOpen-module GPU floor: {c.open_module_gpu_floor}\nDetected NVIDIA PCI:   {len(s['nvidia_devices'])}\nDistro adapter:        {build_distro_plan().adapter}")
    print("GPU eligibility:       use gpu-db-sync once, then gpu-support for official PCI classification")
    print("Safety:                install requires rollback-version availability before snapshots and module replacement\n")
    status=_print_checks(); return 2 if not ok else status
def cmd_fetch(a):
    c=load_driver_config(); fetch_source(Path(a.dest),c); print(f"Fetched NVIDIA open GPU kernel modules {c.version} into {a.dest}"); return 0
def cmd_build(a):
    c=load_driver_config(); build_modules(Path(a.source),c,jobs=a.jobs); print(f"Built NVIDIA kernel modules for release {c.version}"); return 0
def cmd_install(a):
    c=load_driver_config(); tid=install_modules(Path(a.source),c,confirmed=a.yes,jobs=a.jobs,rollback_root=Path(a.rollback_root) if a.rollback_root else None,transaction_root=Path(a.transaction_root) if a.transaction_root else None)
    print(f"Armed driver transaction: {tid}\nRegenerate initramfs if required and reboot; nvlx boot-validate checks the transaction after boot."); return 0
def cmd_gpu_db_sync(a):
    c=load_driver_config(); p=Path(a.path) if a.path else default_database_path(c); n=sync_gpu_database(p,c); print(f"Synced {n} official NVIDIA GPU support records for {c.version} to {p}"); return 0
def cmd_gpu_support(a):
    c=load_driver_config(); p=Path(a.database) if a.database else default_database_path(c)
    if not p.is_file(): raise BuildError(f"GPU support database not found: {p}; run nvlx gpu-db-sync")
    devices=detect_nvidia_devices(Path(a.sysfs_root)); _json([x.to_dict() for x in classify_devices(devices,load_gpu_database(p,c))]); return 0 if devices else 1
def cmd_distro_plan(_): _json(build_distro_plan().to_dict()); return 0
def cmd_repo_plan(_): _json(repository_plan(load_driver_config()).to_dict()); return 0
def cmd_dkms(_): _json(dkms_state().to_dict()); return 0
def cmd_prime(a): _json(prime_report(Path(a.sysfs_root)).to_dict()); return 0
def cmd_session(_):
    r=session_report(); _json(r.to_dict()); return 2 if r.warnings else 0
def cmd_topology(_):
    r=topology_report(); _json(r.to_dict()); return 0 if r.available else 1
def cmd_mig(_):
    r=mig_fabric_report(); _json(r.to_dict()); return 2 if r.fabric_manager_aligned is False or r.dcgm_compatible is False else 0
def cmd_mig_plan(a): _json(plan_mig_profile(a.target).to_dict()); return 0
def cmd_mig_apply(a): _json(apply_mig_profile(a.target,confirmed=a.yes,maintenance=a.maintenance).to_dict()); return 0
def cmd_dcgm(a):
    rows=reliability_rows(); exp=exporter_state(a.url); _json({"gpus":[r.to_dict() for r in rows],"exporter":exp.to_dict()}); return 0 if rows or exp.reachable else 1
def cmd_nvsdm(_):
    r=nvsdm_report(); _json(r.to_dict()); return 2 if r.aligned is False else 0
def cmd_health(a):
    r=health_report(require_expected_version=not a.allow_other_version); _json(r.to_dict()); return 0 if r.healthy else 2
def cmd_packages(_): _json(capture_package_state().to_dict()); return 0
def cmd_rollback_preflight(_):
    r=check_rollback_availability(); _json(r.to_dict()); return 0 if r.available else 2
def cmd_pending(_):
    tx=load_pending(); _json(tx.to_dict() if tx else None); return 0 if tx else 1
def cmd_boot_validate(a):
    tx,ok,message=validate_pending(auto_rollback=a.auto_rollback); _json({"transaction":tx.to_dict() if tx else None,"healthy":ok,"message":message}); return 0 if ok else 2
def cmd_watchdog_plan(a): _json(WatchdogPolicy(a.retries,a.restart_sec,a.timeout_sec,a.start_limit_sec).to_dict()); return 0
def cmd_boot_guard(a):
    path=install_boot_guard(confirmed=a.yes,retries=a.retries,restart_sec=a.restart_sec,timeout_sec=a.timeout_sec); print(f"Installed and enabled boot guard: {path}"); return 0
def cmd_gpu_operator(a): _json(gpu_operator_plan(load_driver_config(),mig_strategy=a.mig_strategy).to_dict()); return 0
def cmd_immutable(_): _json(immutable_plan().to_dict()); return 0
def cmd_initramfs_plan(a): _json(initramfs_plan(a.kernel).to_dict()); return 0
def cmd_initramfs_regen(a): _json(regenerate_initramfs(kernel=a.kernel,confirmed=a.yes).to_dict()); return 0
def cmd_sb_plan(_): _json(secure_boot_plan().to_dict()); return 0
def cmd_sb_keygen(a):
    key,cert=generate_mok(Path(a.key_dir),a.common_name,confirmed=a.yes); print(f"Generated private key: {key}\nGenerated DER certificate: {cert}\nEnroll with: {enroll_command(cert)}\nEnrollment completes through the firmware MOK screen after reboot."); return 0
def cmd_sb_sign(a):
    n=sign_modules(Path(a.source),Path(a.key),Path(a.cert),confirmed=a.yes,kernel=a.kernel); print(f"Signed {n} built NVIDIA kernel modules"); return 0
def cmd_sb_verify(_):
    rows=verify_installed_modules(); _json([r.to_dict() for r in rows]); return 2 if any(not r.signed for r in rows) else 0
def cmd_snapshot(a): _json(create_snapshot(root=Path(a.root) if a.root else None,kernel=a.kernel).to_dict()); return 0
def cmd_snapshot_list(a): _json([s.to_dict() for s in list_snapshots(Path(a.root) if a.root else None)]); return 0
def cmd_rollback(a):
    s=apply_snapshot(Path(a.snapshot),confirmed=a.yes); print(f"Restored NVIDIA module snapshot {s.snapshot_id} for kernel {s.kernel}\nReboot or perform a controlled module transition before validating the restored driver."); return 0
def cmd_compat(_):
    r=compatibility_report(); _json(r.to_dict()); return 2 if r.cuda_compatible is False or r.container_packages_aligned is False else 0
def cmd_telemetry(a):
    if a.format=="prometheus": print(prometheus_text(),end="")
    else: _json(json_health())
    return 0
def cmd_report(a):
    path=write_report_bundle(Path(a.destination)); print(f"Wrote sanitized diagnostics bundle to {path}"); return 0

def build_parser():
    p=argparse.ArgumentParser(prog="nvlx",description="Linux NVIDIA driver transaction, fleet health, and diagnostics toolkit"); p.add_argument("--version",action="version",version=f"%(prog)s {__version__}"); sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("detect"); q.add_argument("--sysfs-root",default="/sys/bus/pci/devices"); q.set_defaults(func=cmd_detect)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor); sub.add_parser("plan").set_defaults(func=cmd_plan)
    q=sub.add_parser("fetch"); q.add_argument("--dest",default="vendor/open-gpu-kernel-modules"); q.set_defaults(func=cmd_fetch)
    q=sub.add_parser("build"); q.add_argument("--source",required=True); q.add_argument("--jobs",type=int); q.set_defaults(func=cmd_build)
    q=sub.add_parser("install"); q.add_argument("--source",required=True); q.add_argument("--jobs",type=int); q.add_argument("--rollback-root"); q.add_argument("--transaction-root"); q.add_argument("--yes",action="store_true"); q.set_defaults(func=cmd_install)
    q=sub.add_parser("gpu-db-sync"); q.add_argument("--path"); q.set_defaults(func=cmd_gpu_db_sync)
    q=sub.add_parser("gpu-support"); q.add_argument("--database"); q.add_argument("--sysfs-root",default="/sys/bus/pci/devices"); q.set_defaults(func=cmd_gpu_support)
    sub.add_parser("distro-plan").set_defaults(func=cmd_distro_plan); sub.add_parser("repo-plan").set_defaults(func=cmd_repo_plan); sub.add_parser("dkms-status").set_defaults(func=cmd_dkms)
    q=sub.add_parser("prime"); q.add_argument("--sysfs-root",default="/sys/bus/pci/devices"); q.set_defaults(func=cmd_prime)
    sub.add_parser("session").set_defaults(func=cmd_session); sub.add_parser("topology").set_defaults(func=cmd_topology); sub.add_parser("mig-fabric").set_defaults(func=cmd_mig)
    q=sub.add_parser("mig-profile-plan"); q.add_argument("target"); q.set_defaults(func=cmd_mig_plan)
    q=sub.add_parser("mig-profile-apply"); q.add_argument("target"); q.add_argument("--maintenance",action="store_true"); q.add_argument("--yes",action="store_true"); q.set_defaults(func=cmd_mig_apply)
    q=sub.add_parser("dcgm-telemetry"); q.add_argument("--url",default="http://127.0.0.1:9400/metrics"); q.set_defaults(func=cmd_dcgm)
    sub.add_parser("nvsdm").set_defaults(func=cmd_nvsdm)
    q=sub.add_parser("health"); q.add_argument("--allow-other-version",action="store_true"); q.set_defaults(func=cmd_health)
    sub.add_parser("package-state").set_defaults(func=cmd_packages); sub.add_parser("rollback-preflight").set_defaults(func=cmd_rollback_preflight); sub.add_parser("transaction-pending").set_defaults(func=cmd_pending)
    q=sub.add_parser("boot-validate"); q.add_argument("--auto-rollback",action="store_true"); q.set_defaults(func=cmd_boot_validate)
    q=sub.add_parser("watchdog-plan"); q.add_argument("--retries",type=int,default=3); q.add_argument("--restart-sec",type=int,default=20); q.add_argument("--timeout-sec",type=int,default=90); q.add_argument("--start-limit-sec",type=int,default=300); q.set_defaults(func=cmd_watchdog_plan)
    q=sub.add_parser("boot-guard-install"); q.add_argument("--retries",type=int,default=3); q.add_argument("--restart-sec",type=int,default=20); q.add_argument("--timeout-sec",type=int,default=90); q.add_argument("--yes",action="store_true"); q.set_defaults(func=cmd_boot_guard)
    q=sub.add_parser("gpu-operator-plan"); q.add_argument("--mig-strategy",choices=("none","single","mixed"),default="none"); q.set_defaults(func=cmd_gpu_operator)
    sub.add_parser("immutable-plan").set_defaults(func=cmd_immutable)
    q=sub.add_parser("initramfs-plan"); q.add_argument("--kernel"); q.set_defaults(func=cmd_initramfs_plan)
    q=sub.add_parser("initramfs-regenerate"); q.add_argument("--kernel"); q.add_argument("--yes",action="store_true"); q.set_defaults(func=cmd_initramfs_regen)
    sub.add_parser("secureboot-plan").set_defaults(func=cmd_sb_plan)
    q=sub.add_parser("secureboot-keygen"); q.add_argument("--key-dir",required=True); q.add_argument("--common-name",default="nvlx NVIDIA module signing"); q.add_argument("--yes",action="store_true"); q.set_defaults(func=cmd_sb_keygen)
    q=sub.add_parser("secureboot-sign"); q.add_argument("--source",required=True); q.add_argument("--key",required=True); q.add_argument("--cert",required=True); q.add_argument("--kernel"); q.add_argument("--yes",action="store_true"); q.set_defaults(func=cmd_sb_sign)
    sub.add_parser("secureboot-verify").set_defaults(func=cmd_sb_verify)
    q=sub.add_parser("rollback-snapshot"); q.add_argument("--root"); q.add_argument("--kernel"); q.set_defaults(func=cmd_snapshot)
    q=sub.add_parser("rollback-list"); q.add_argument("--root"); q.set_defaults(func=cmd_snapshot_list)
    q=sub.add_parser("rollback-apply"); q.add_argument("snapshot"); q.add_argument("--yes",action="store_true"); q.set_defaults(func=cmd_rollback)
    sub.add_parser("compat").set_defaults(func=cmd_compat)
    q=sub.add_parser("telemetry"); q.add_argument("--format",choices=("json","prometheus"),default="json"); q.set_defaults(func=cmd_telemetry)
    q=sub.add_parser("report"); q.add_argument("destination"); q.set_defaults(func=cmd_report)
    return p

def main(argv=None):
    args=build_parser().parse_args(argv)
    try: return int(args.func(args))
    except (BuildError,RuntimeError,OSError,ValueError) as exc: print(f"nvlx: {exc}",file=sys.stderr); return 2
    except subprocess.CalledProcessError as exc: print(f"nvlx: command failed with exit code {exc.returncode}: {exc.cmd}",file=sys.stderr); return 2
    except KeyboardInterrupt: print("nvlx: interrupted",file=sys.stderr); return 130
if __name__=="__main__": raise SystemExit(main())
