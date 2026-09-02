#!/usr/bin/env python3
"""Fail when NVIDIA changes security material relevant to nvlx-managed components."""
from __future__ import annotations

import argparse
import difflib
import json
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath


API = "https://api.github.com/repos/{repo}"
RAW = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"


def _json(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "nvlx-security-gate",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "nvlx-security-gate"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8", "replace")


def _raw_url(repo: str, ref: str, path: str) -> str:
    return RAW.format(
        repo=repo,
        ref=urllib.parse.quote(ref, safe=""),
        path=urllib.parse.quote(path, safe="/"),
    )


def _is_dedicated_bulletin(path: str) -> bool:
    """Return whether path lives below a YYYY/numeric-bulletin directory."""
    parts = PurePosixPath(path).parts
    return (
        len(parts) >= 3
        and len(parts[0]) == 4
        and parts[0].isdigit()
        and parts[1].isdigit()
    )


def _patch_changes(patch: str) -> str:
    """Extract changed lines only, excluding unified-diff file markers and context."""
    changed = []
    for line in patch.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            changed.append(line[1:])
    return "\n".join(changed)


def _content_changes(before: str, after: str) -> str:
    changed = []
    for line in difflib.ndiff(before.splitlines(), after.splitlines()):
        if line.startswith(("+ ", "- ")):
            changed.append(line[2:])
    return "\n".join(changed)


def _inspection_text(
    change: dict[str, object], repo: str, baseline: str, head: str
) -> tuple[str, str]:
    """Return security-relevant delta text and the best source URL for a change."""
    path = change.get("filename")
    if type(path) is not str or not path:
        raise ValueError("NVIDIA comparison returned a file without a valid path")

    previous_path = change.get("previous_filename", path)
    if type(previous_path) is not str or not previous_path:
        previous_path = path
    status = change.get("status")
    head_url = _raw_url(repo, head, path)
    baseline_url = _raw_url(repo, baseline, previous_path)

    if status == "added":
        return _text(head_url), head_url
    if status == "removed":
        return _text(baseline_url), baseline_url

    # A dedicated bulletin is a security unit: any modification to one that
    # names a managed component needs review, even when the product name is
    # unchanged context around a version or severity edit.
    if _is_dedicated_bulletin(path) or _is_dedicated_bulletin(previous_path):
        before = _text(baseline_url)
        after = _text(head_url)
        return before + "\n" + after, head_url

    # Aggregate indexes contain historical references to managed products.
    # Searching their entire current contents turns every unrelated bulletin
    # into a false positive, so inspect only added and removed lines.
    patch = change.get("patch")
    if type(patch) is str:
        return _patch_changes(patch), head_url

    # GitHub may omit a patch for a large text file. Reconstruct the delta;
    # fetch failures intentionally propagate so the security gate fails closed.
    before = _text(baseline_url)
    after = _text(head_url)
    return _content_changes(before, after), head_url


def check(config_path: Path) -> dict[str, object]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    repo = config["repository"]
    baseline = config["baseline_commit"]
    terms = tuple(config["relevant_terms"])
    if type(repo) is not str or not repo:
        raise ValueError("repository must be a non-empty string")
    if type(baseline) is not str or not baseline:
        raise ValueError("baseline_commit must be a non-empty string")
    if not terms or any(type(term) is not str or not term for term in terms):
        raise ValueError("relevant_terms must contain non-empty strings")

    branch = _json(API.format(repo=repo) + "/branches/main")
    head = branch["commit"]["sha"]
    if head == baseline:
        return {
            "passed": True,
            "baseline": baseline,
            "head": head,
            "relevant_changes": [],
        }

    comparison = _json(API.format(repo=repo) + f"/compare/{baseline}...{head}")
    if comparison.get("status") != "ahead":
        raise RuntimeError(
            "NVIDIA security baseline is not an ancestor of upstream main "
            f"(comparison status: {comparison.get('status')!r})"
        )
    files = comparison.get("files")
    if type(files) is not list:
        raise ValueError("NVIDIA comparison did not include a file list")
    if len(files) >= 300:
        raise RuntimeError("NVIDIA comparison reached the 300-file review limit")

    hits = []
    for change in files:
        if type(change) is not dict:
            raise ValueError("NVIDIA comparison returned an invalid file entry")
        path = change.get("filename", "")
        previous_path = change.get("previous_filename", "")
        if not (
            type(path) is str
            and (
                path.endswith(".md")
                or (type(previous_path) is str and previous_path.endswith(".md"))
            )
        ):
            continue
        text, source_url = _inspection_text(change, repo, baseline, head)
        folded = text.casefold()
        matched = [term for term in terms if term.casefold() in folded]
        if matched:
            hits.append(
                {
                    "path": path,
                    "status": change.get("status"),
                    "terms": matched,
                    "raw_url": source_url,
                }
            )

    return {
        "passed": not hits,
        "baseline": baseline,
        "head": head,
        "relevant_changes": hits,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/security-baseline.json")
    args = parser.parse_args(argv)
    try:
        result = check(Path(args.config))
    except Exception as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
