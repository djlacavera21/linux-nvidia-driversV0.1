#!/usr/bin/env python3
"""Build a deterministic source archive and SHA-256 manifest for nvlx releases."""
from __future__ import annotations
import gzip, hashlib, io, os, tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INCLUDE=("src","config","docs","scripts","tests","README.md","LICENSE","pyproject.toml","Makefile")

def files():
    for name in INCLUDE:
        p=ROOT/name
        if p.is_file(): yield p
        elif p.is_dir():
            for f in sorted(x for x in p.rglob("*") if x.is_file() and "__pycache__" not in x.parts): yield f

def build(version:str,out:Path)->tuple[Path,Path]:
    out.mkdir(parents=True,exist_ok=True); archive=out/f"nvlx-{version}.tar.gz"
    raw=io.BytesIO()
    with tarfile.open(fileobj=raw,mode="w",format=tarfile.PAX_FORMAT) as tf:
        for path in files():
            rel=path.relative_to(ROOT); info=tf.gettarinfo(str(path),arcname=f"nvlx-{version}/{rel}")
            info.uid=0; info.gid=0; info.uname="root"; info.gname="root"; info.mtime=0
            with path.open("rb") as fh: tf.addfile(info,fh)
    with archive.open("wb") as fh:
        with gzip.GzipFile(filename="",mode="wb",fileobj=fh,mtime=0,compresslevel=9) as gz: gz.write(raw.getvalue())
    digest=hashlib.sha256(archive.read_bytes()).hexdigest(); manifest=out/"SHA256SUMS"
    manifest.write_text(f"{digest}  {archive.name}\n",encoding="utf-8")
    return archive,manifest

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("version"); p.add_argument("--out",default="dist/repro")
    a=p.parse_args(); archive,manifest=build(a.version,Path(a.out)); print(archive); print(manifest)
