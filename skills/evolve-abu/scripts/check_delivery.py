#!/usr/bin/env python3
"""Prove a framework change actually REACHED the sessions that will need it.

Shipping is a chain of three links, and every one of them fails silently:

    working tree  --commit-->  HEAD  --push-->  origin  --/plugin update-->  installed

`evolve-abu` step 6 used to end at "tell Gary to run /plugin update", which is
only the third link. When an earlier link is the broken one, that instruction is
worse than useless: it sends Gary to run a command that correctly does nothing,
and its "already at the latest version" is read as confirmation. That is exactly
how 1.7.0 sat unpushed while `/plugin update` reported success (docs/GAPS.md G40,
whose own filing commit was one of the three that had not been pushed).

So the point of this script is NOT to print three version numbers. It is to name
WHOSE MOVE IT IS, because the two answers are not interchangeable:

    exit 1  ->  the agent's move. Nothing has left this machine. Fix it now.
    exit 2  ->  Gary's move. Everything is published; only he can run
                /plugin update, so this is a genuine handoff and not a failure.

Conflating those is the defect. An agent that reports exit 2 as "shipped" is
lying by one link; an agent that reports exit 1 as "over to you, Gary" is
handing him a command that cannot possibly work.

Usage:
    check_delivery.py [--repo PATH] [--expect REL_PATH ...] [--no-fetch] [--json]

`--expect` is the part that survives a forgotten version bump. Versions are a
proxy for content, and a proxy is what fails: if the bump is missed, every
number matches and the artifact is still absent. Naming the file you just built
checks the thing you actually care about.

    check_delivery.py --expect skills/create-style-pack/scripts/bless_ref.py
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CACHE_ROOT = Path.home() / ".claude" / "plugins" / "cache"


def sh(args, cwd=None):
    """Run a command, returning (ok, stdout). Never raises on non-zero."""
    try:
        p = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=60
        )
        return p.returncode == 0, p.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return False, ""


def semver(text):
    """('1.10.0') -> (1, 10, 0). Unparseable sorts lowest, never crashes."""
    parts = re.findall(r"\d+", text or "")
    return tuple(int(p) for p in parts[:3]) + (0,) * (3 - len(parts[:3]))


def version_of(blob):
    try:
        return json.loads(blob).get("version", "")
    except (ValueError, AttributeError):
        return ""


def main():
    ap = argparse.ArgumentParser(description="Verify a framework change reached the installed plugin.")
    ap.add_argument("--repo", default=None, help="Framework repo root (default: infer from this script).")
    ap.add_argument("--expect", action="append", default=[],
                    help="Repo-relative path that MUST exist in the installed plugin. Repeatable.")
    ap.add_argument("--no-fetch", action="store_true", help="Skip `git fetch` (offline).")
    ap.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = ap.parse_args()

    repo = Path(args.repo).expanduser() if args.repo else Path(__file__).resolve().parents[3]
    manifest = repo / ".claude-plugin" / "plugin.json"
    market = repo / ".claude-plugin" / "marketplace.json"
    if not manifest.exists():
        print(f"  no plugin manifest at {manifest}", file=sys.stderr)
        return 3

    declared = version_of(manifest.read_text())
    plugin_name = json.loads(manifest.read_text()).get("name", "abu")
    market_name = "agentic-brand-universe"
    if market.exists():
        market_name = json.loads(market.read_text()).get("name", market_name)

    ok, branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    if not ok or not branch:
        print("  not a git repo, or no branch", file=sys.stderr)
        return 3

    _, head_blob = sh(["git", "show", "HEAD:.claude-plugin/plugin.json"], cwd=repo)
    head_v = version_of(head_blob)

    if not args.no_fetch:
        sh(["git", "fetch", "-q", "origin", branch], cwd=repo)
    remote_ref = f"origin/{branch}"
    has_remote, _ = sh(["git", "rev-parse", "--verify", "-q", remote_ref], cwd=repo)
    _, remote_blob = sh(["git", "show", f"{remote_ref}:.claude-plugin/plugin.json"], cwd=repo)
    remote_v = version_of(remote_blob) if has_remote else ""
    _, ahead = sh(["git", "rev-list", "--count", f"{remote_ref}..HEAD"], cwd=repo)
    ahead_n = int(ahead) if ahead.isdigit() else 0

    cache_dir = CACHE_ROOT / market_name / plugin_name
    installed_dirs = sorted(
        (d for d in cache_dir.iterdir() if d.is_dir()) if cache_dir.is_dir() else [],
        key=lambda d: semver(d.name),
    )
    installed_v = installed_dirs[-1].name if installed_dirs else ""
    installed_path = installed_dirs[-1] if installed_dirs else None

    # Content check runs against whatever is installed, because "is the artifact
    # there" is the real question and a version number only stands in for it.
    missing = []
    if installed_path:
        missing = [p for p in args.expect if not (installed_path / p).exists()]

    state = {
        "declared": declared, "committed": head_v, "remote": remote_v,
        "installed": installed_v, "branch": branch, "ahead": ahead_n,
        "missing": missing, "cache": str(installed_path or cache_dir),
    }

    # First broken link wins: these are sequential, so reporting the third break
    # while the first is still open sends the reader to the wrong remedy.
    if declared != head_v:
        verdict, whose, why = "UNCOMMITTED", "yours", (
            f"plugin.json says {declared} in the working tree but {head_v or 'nothing'} at HEAD. "
            "Commit the version bump.")
    elif not has_remote:
        verdict, whose, why = "NO-REMOTE", "yours", (
            f"no {remote_ref}. Nothing can be delivered from a branch that was never pushed.")
    elif ahead_n or declared != remote_v:
        verdict, whose, why = "UNPUSHED", "yours", (
            f"{ahead_n} commit(s) ahead of {remote_ref}, which is at {remote_v or 'nothing'}. "
            f"`/plugin update` pulls from the remote, so it will report 'already at the latest "
            f"version' and be telling the truth. Push to {remote_ref}.")
    elif not installed_v:
        verdict, whose, why = "NOT-INSTALLED", "gary", (
            f"published at {declared}, but no plugin cache at {cache_dir}. "
            "Gary installs it; you cannot.")
    elif semver(installed_v) < semver(declared):
        verdict, whose, why = "STALE-CACHE", "gary", (
            f"published at {declared}; the installed plugin is {installed_v}. Everything that is "
            "yours to do is done. Gary runs `/plugin update`, and until he does, every session "
            f"loads the {installed_v} skill bodies.")
    elif missing:
        verdict, whose, why = "MISSING-CONTENT", "gary", (
            f"the installed plugin is {installed_v} but does not carry: {', '.join(missing)}. "
            "A matching version number is not proof the artifact shipped; if the bump was "
            "skipped, `/plugin update` has nothing to notice. Bump and re-ship.")
    else:
        verdict, whose, why = "DELIVERED", "nobody", (
            f"{declared} is committed, pushed, and installed"
            + (f", carrying {len(args.expect)} named artifact(s)" if args.expect else "") + ".")

    state.update(verdict=verdict, whose=whose, why=why)
    if args.json:
        print(json.dumps(state, indent=2))
    else:
        print(f"\n  {verdict}  ({declared} declared / {head_v or '-'} committed / "
              f"{remote_v or '-'} remote / {installed_v or '-'} installed)")
        print(f"  {why}\n")

    return {"yours": 1, "gary": 2, "nobody": 0}[whose]


if __name__ == "__main__":
    sys.exit(main())
