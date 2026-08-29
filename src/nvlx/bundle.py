"""Deterministic production configuration bundle manifests."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json
from pathlib import Path

@dataclass(frozen=True)
class BundleManifest:
    schema: int
    files: tuple[tuple[str,str], ...]
    digest: str
    def to_dict(self): return {"schema":self.schema,"files":[{"path":p,"sha256":h} for p,h in self.files],"digest":self.digest}

def build(root: Path, paths: list[str]|tuple[str,...]) -> BundleManifest:
    entries=[]
    for rel in sorted(set(paths)):
        p=(root/rel).resolve()
        if not p.is_file(): raise FileNotFoundError(rel)
        try: p.relative_to(root.resolve())
        except ValueError: raise ValueError(f"bundle path escapes root: {rel}")
        entries.append((rel,hashlib.sha256(p.read_bytes()).hexdigest()))
    payload=json.dumps(entries,sort_keys=True,separators=(",", ":")).encode()
    return BundleManifest(1,tuple(entries),hashlib.sha256(payload).hexdigest())

def verify(root: Path, manifest: BundleManifest) -> tuple[bool, tuple[str,...]]:
    errors=[]
    rebuilt=build(root,[p for p,_ in manifest.files])
    expected=dict(manifest.files); actual=dict(rebuilt.files)
    for p,h in expected.items():
        if actual.get(p)!=h: errors.append(f"digest mismatch: {p}")
    if rebuilt.digest != manifest.digest: errors.append("bundle digest mismatch")
    return (not errors,tuple(errors))

def cosign_verify_blob_plan(manifest_path: str, signature_path: str, certificate_identity: str, oidc_issuer: str="https://token.actions.githubusercontent.com") -> list[str]:
    return ["cosign","verify-blob","--signature",signature_path,"--certificate-identity",certificate_identity,"--certificate-oidc-issuer",oidc_issuer,manifest_path]
