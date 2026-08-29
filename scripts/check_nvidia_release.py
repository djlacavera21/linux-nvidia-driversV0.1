#!/usr/bin/env python3
"""Detect/apply newer numeric NVIDIA open-gpu-kernel-module tags."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from urllib.request import Request, urlopen

TAG=re.compile(r'^\d+(?:\.\d+)+$')
def version_key(v:str): return tuple(int(p) for p in v.split('.'))
def newest(current:str,tags:list[str])->str|None:
    candidates=[t for t in tags if TAG.fullmatch(t) and version_key(t)>version_key(current)]
    return max(candidates,key=version_key) if candidates else None

def fetch_tags()->list[str]:
    req=Request('https://api.github.com/repos/NVIDIA/open-gpu-kernel-modules/tags?per_page=100',headers={'Accept':'application/vnd.github+json','User-Agent':'nvlx-release-check'})
    with urlopen(req,timeout=20) as r: return [item['name'] for item in json.load(r)]
def current_version(path:Path)->str:
    text=path.read_text(); m=re.search(r'^version\s*=\s*"([^"]+)"',text,re.M)
    if not m: raise SystemExit('driver version not found')
    return m.group(1)
def apply(path:Path,old:str,new:str)->None:
    text=path.read_text(); path.write_text(text.replace(f'version = "{old}"',f'version = "{new}"',1))

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--config',default='config/driver-series.toml'); ap.add_argument('--apply',action='store_true'); args=ap.parse_args(); path=Path(args.config); current=current_version(path); candidate=newest(current,fetch_tags())
    if candidate and args.apply: apply(path,current,candidate)
    print(candidate or '')
    return 0
if __name__=='__main__': raise SystemExit(main())
