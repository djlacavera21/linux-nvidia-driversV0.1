#!/usr/bin/env python3
"""Fail when NVIDIA publishes or changes a security bulletin relevant to nvlx-managed components."""
from __future__ import annotations
import argparse, json, sys, urllib.request
from pathlib import Path

API="https://api.github.com/repos/{repo}"

def _json(url:str):
    req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","User-Agent":"nvlx-security-gate"})
    with urllib.request.urlopen(req,timeout=15) as r: return json.loads(r.read().decode("utf-8"))

def _text(url:str)->str:
    req=urllib.request.Request(url,headers={"User-Agent":"nvlx-security-gate"})
    with urllib.request.urlopen(req,timeout=15) as r: return r.read().decode("utf-8","replace")

def check(config_path:Path)->dict[str,object]:
    cfg=json.loads(config_path.read_text(encoding="utf-8")); repo=cfg["repository"]; baseline=cfg["baseline_commit"]; terms=tuple(cfg["relevant_terms"])
    branch=_json(API.format(repo=repo)+"/branches/main"); head=branch["commit"]["sha"]
    if head==baseline: return {"passed":True,"baseline":baseline,"head":head,"relevant_changes":[]}
    compare=_json(API.format(repo=repo)+f"/compare/{baseline}...{head}")
    hits=[]
    for f in compare.get("files",[]):
        path=f.get("filename","")
        if not path.endswith(".md"): continue
        raw=f"https://raw.githubusercontent.com/{repo}/{head}/{path}"
        try: text=_text(raw)
        except Exception: continue
        matched=[t for t in terms if t.lower() in text.lower()]
        if matched: hits.append({"path":path,"status":f.get("status"),"terms":matched,"raw_url":raw})
    return {"passed":not hits,"baseline":baseline,"head":head,"relevant_changes":hits}

def main(argv=None)->int:
    p=argparse.ArgumentParser(); p.add_argument("--config",default="config/security-baseline.json"); a=p.parse_args(argv)
    try: result=check(Path(a.config))
    except Exception as exc:
        print(json.dumps({"passed":False,"error":str(exc)},indent=2)); return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result["passed"] else 2

if __name__=="__main__": raise SystemExit(main())
