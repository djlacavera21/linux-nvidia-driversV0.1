"""Transactional NVIDIA driver upgrade state and boot guard."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import json, os, uuid
from .build import BuildError
from .config import DriverConfig
from .package_state import capture_package_state, load_package_snapshot, restore_package_state
from .rollback import apply_snapshot, create_snapshot
from .rollback_preflight import check_rollback_availability
from .system import loaded_modules, nvidia_smi_driver_version, running_kernel

@dataclass(frozen=True)
class Transaction:
    transaction_id:str
    created_at:str
    kernel:str
    source_version:str
    target_version:str
    rollback_snapshot:str
    package_snapshot:str
    boot_id_before:str|None
    state:str
    failure_reason:str|None=None
    def to_dict(self): return asdict(self)

def transaction_root()->Path: return Path("/var/lib/nvlx/transactions")
def pending_path(root:Path|None=None)->Path: return (root or transaction_root())/"pending.json"
def _boot_id()->str|None:
    try: return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    except OSError: return None

def _write(tx:Transaction,root:Path)->Path:
    directory=root/tx.transaction_id; directory.mkdir(parents=True,exist_ok=True)
    path=directory/"transaction.json"; path.write_text(json.dumps(tx.to_dict(),indent=2,sort_keys=True)+"\n",encoding="utf-8"); return path

def begin_transaction(config:DriverConfig, *, rollback_root:Path|None=None, root:Path|None=None)->Transaction:
    if os.geteuid()!=0: raise BuildError("transaction creation must run as root")
    storage=root or transaction_root(); storage.mkdir(parents=True,exist_ok=True)
    tid=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]
    directory=storage/tid; directory.mkdir(parents=True,exist_ok=False)
    package_path=directory/"package-state.json"; snap=capture_package_state()
    package_path.write_text(json.dumps(snap.to_dict(),indent=2,sort_keys=True)+"\n",encoding="utf-8")
    preflight=check_rollback_availability(snap)
    (directory/"rollback-preflight.json").write_text(json.dumps(preflight.to_dict(),indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if not preflight.available:
        raise BuildError("rollback preflight failed; unavailable versions: "+", ".join(preflight.missing))
    module_snapshot=create_snapshot(root=rollback_root)
    tx=Transaction(tid,datetime.now(timezone.utc).isoformat(),running_kernel(),nvidia_smi_driver_version() or "unknown",config.version,module_snapshot.root,str(package_path),_boot_id(),"prepared")
    _write(tx,storage); return tx

def arm_transaction(tx:Transaction, root:Path|None=None)->Transaction:
    storage=root or transaction_root(); armed=Transaction(**{**tx.to_dict(),"state":"pending-reboot"}); _write(armed,storage)
    pending=pending_path(storage); pending.write_text(json.dumps(armed.to_dict(),indent=2,sort_keys=True)+"\n",encoding="utf-8"); return armed

def load_transaction(path:Path)->Transaction: return Transaction(**json.loads(path.read_text(encoding="utf-8")))
def load_pending(root:Path|None=None)->Transaction|None:
    path=pending_path(root)
    if not path.is_file(): return None
    try: return load_transaction(path)
    except (OSError,ValueError,TypeError): return None

def _post_reboot_health_reason(tx:Transaction)->str|None:
    version=nvidia_smi_driver_version()
    if version is None: return "nvidia-smi is unavailable or cannot communicate with the driver"
    if version!=tx.target_version: return f"driver version {version} does not match transaction target {tx.target_version}"
    if "nvidia" not in loaded_modules(): return "nvidia kernel module is not loaded"
    return None

def validate_pending(*, auto_rollback:bool=False, root:Path|None=None)->tuple[Transaction|None,bool,str]:
    storage=root or transaction_root(); tx=load_pending(storage)
    if tx is None: return None,True,"no pending transaction"
    current_boot=_boot_id()
    if tx.boot_id_before and current_boot==tx.boot_id_before:
        waiting=Transaction(**{**tx.to_dict(),"state":"pending-reboot","failure_reason":None}); _write(waiting,storage)
        return waiting,False,"transaction is awaiting a reboot before health validation"
    reason=_post_reboot_health_reason(tx)
    if reason is None:
        done=Transaction(**{**tx.to_dict(),"state":"validated","failure_reason":None}); _write(done,storage); pending_path(storage).unlink(missing_ok=True); return done,True,"driver healthy"
    failed=Transaction(**{**tx.to_dict(),"state":"failed","failure_reason":reason}); _write(failed,storage)
    if not auto_rollback: return failed,False,reason
    try:
        restore_package_state(load_package_snapshot(Path(tx.package_snapshot)))
        apply_snapshot(Path(tx.rollback_snapshot),confirmed=True)
        from .initramfs import regenerate_initramfs
        try: regenerate_initramfs(kernel=tx.kernel,confirmed=True)
        except Exception: pass
    except Exception as exc:
        rollback_failed=Transaction(**{**failed.to_dict(),"state":"rollback-failed","failure_reason":f"{reason}; rollback error: {exc}"}); _write(rollback_failed,storage); return rollback_failed,False,rollback_failed.failure_reason or reason
    rolled=Transaction(**{**failed.to_dict(),"state":"rolled-back"}); _write(rolled,storage); pending_path(storage).unlink(missing_ok=True); return rolled,False,reason

def install_boot_guard(*, confirmed:bool, retries:int=3, restart_sec:int=20, timeout_sec:int=90)->Path:
    from .watchdog import WatchdogPolicy, install_watchdog
    return install_watchdog(WatchdogPolicy(retries,restart_sec,timeout_sec),confirmed=confirmed)
