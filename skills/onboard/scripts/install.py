#!/usr/bin/env python3
"""install.py — put the framework in place, and report in facts.

Runs the whole install and prints a JSON verdict the agent narrates. Idempotent: it
re-links what is already linked and reports "already done" instead of failing, so a
half-finished install can simply be run again.

  python3 install.py [--skills-dir ~/.claude/skills] [--check] [--json]

`--check` changes nothing and only reports what the state currently is.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

def _abu_root(start=None):
    p = Path(start or __file__).resolve()
    for c in [p, *p.parents]:
        if (c / "engine" / "agenticstory").is_dir():
            return c
    raise SystemExit("abu: cannot locate the ABU root from " + str(p))


REPO = _abu_root()
sys.path.insert(0, str(REPO / "engine"))

from agenticstory import providers  # noqa: E402

KEYS = {"gpt-image-2": "OPENAI_API_KEY", "nano-banana-pro": "GEMINI_API_KEY"}


def link_skills(skills_dir: Path, apply: bool) -> dict:
    """Symlink every skill into the harness's skill directory."""
    src = REPO / "skills"
    linked, already, failed = [], [], []
    for d in sorted(src.iterdir()):
        if not (d / "SKILL.md").is_file():
            continue
        dst = skills_dir / d.name
        try:
            if dst.is_symlink() and dst.resolve() == d.resolve():
                already.append(d.name)
                continue
            if apply:
                skills_dir.mkdir(parents=True, exist_ok=True)
                if dst.is_symlink() or dst.exists():
                    if dst.is_dir() and not dst.is_symlink():
                        failed.append(f"{d.name}: a real directory is already there")
                        continue
                    dst.unlink()
                dst.symlink_to(d)
            linked.append(d.name)
        except OSError as e:
            failed.append(f"{d.name}: {e}")
    return {"linked": linked, "already": already, "failed": failed,
            "dir": str(skills_dir), "total": len(linked) + len(already)}


def check_providers() -> list[dict]:
    out = []
    for p, key in KEYS.items():
        try:
            script = str(providers.resolve(p))
            found = True
        except FileNotFoundError:
            script, found = "", False
        out.append({"provider": p, "script": script, "script_found": found,
                    "key_env": key, "key_set": bool(os.environ.get(key))})
    return out


def check_tools() -> list[dict]:
    return [{"tool": t, "found": bool(shutil.which(t)),
             "why": w} for t, w in (
        ("git", "version control; a canon you cannot diff is not versioned"),
        ("uv", "how the provider scripts are run"),
    )]


def run_tests() -> dict:
    r = subprocess.run(["./run-tests.sh"], cwd=REPO, capture_output=True, text=True)
    tail = (r.stdout or "").strip().splitlines()[-3:]
    return {"ok": r.returncode == 0, "summary": " | ".join(t.strip() for t in tail)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", default="~/.claude/skills")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip-tests", action="store_true")
    a = ap.parse_args()

    skills_dir = Path(a.skills_dir).expanduser()
    result = {
        "repo": str(REPO),
        "python": sys.version.split()[0],
        "skills": link_skills(skills_dir, apply=not a.check),
        "providers": check_providers(),
        "tools": check_tools(),
        "tests": {"skipped": True} if a.skip_tests else run_tests(),
        "mode": "check" if a.check else "install",
    }
    blockers = []
    if not any(p["script_found"] and p["key_set"] for p in result["providers"]):
        have_script = any(p["script_found"] for p in result["providers"])
        blockers.append("no usable image provider: "
                        + ("set OPENAI_API_KEY or GEMINI_API_KEY" if have_script
                           else "no provider script resolves"))
    for t in result["tools"]:
        if not t["found"]:
            blockers.append(f"{t['tool']} is not installed ({t['why']})")
    if result["skills"]["failed"]:
        blockers.append(f"{len(result['skills']['failed'])} skill(s) could not be linked")
    result["blockers"] = blockers
    result["ready"] = not blockers

    if a.json:
        print(json.dumps(result, indent=2))
        return 0
    s = result["skills"]
    print(f"skills : {s['total']} available in {s['dir']} "
          f"({len(s['linked'])} newly linked, {len(s['already'])} already)")
    for p in result["providers"]:
        print(f"provider {p['provider']:16} script={'yes' if p['script_found'] else 'NO'} "
              f"{p['key_env']}={'set' if p['key_set'] else 'NOT SET'}")
    if not a.skip_tests:
        print(f"tests  : {'green' if result['tests']['ok'] else 'FAILING'} "
              f"({result['tests']['summary']})")
    print("ready  : " + ("yes" if result["ready"] else "no"))
    for b in blockers:
        print(f"  - {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
