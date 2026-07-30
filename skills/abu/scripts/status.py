#!/usr/bin/env python3
"""status.py — everything the front door needs to know, as one JSON blob.

The agent does the talking. This does the finding, the grading, the diffing and the
selecting, so the narration is over FACTS rather than over a guess about what the
user probably has.

  python3 status.py                 # the universe you are standing in, else registered
  python3 status.py <universe>      # a specific one
  python3 status.py --json          # machine-readable (the agent's path)
  python3 status.py --no-record     # do not update the "last seen" score

Exit code is 0 even with no universes at all: "you have none yet" is a legitimate
answer to "where am I", not a failure.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[1]
sys.path.insert(0, str(REPO / "engine"))

from agenticstory import workspace  # noqa: E402

GRADER = REPO / "skills" / "universe-doctor" / "scripts" / "grade.py"


def grade(universe: Path) -> dict | None:
    """Run the doctor. The rubric lives there and is not duplicated here."""
    if not GRADER.is_file():
        return {"error": f"grader missing at {GRADER}"}
    r = subprocess.run([sys.executable, str(GRADER), str(universe), "--json"],
                       capture_output=True, text=True)
    if r.returncode != 0 and not r.stdout.strip():
        return {"error": (r.stderr or r.stdout).strip()[:400]}
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"error": f"grader returned unparseable output: {r.stdout[:200]}"}


def report(universe: Path, record: bool = True) -> dict:
    g = grade(universe)
    if g is None or "error" in (g or {}):
        return {"universe": str(universe), "name": universe.name,
                "error": (g or {}).get("error", "unknown grading failure")}
    progress = (workspace.record(universe, g["score"], g["grade"]) if record
                else {"now": {"score": g["score"], "grade": g["grade"]},
                      "previous": workspace.last_seen(universe), "delta": None})
    return {
        "universe": str(universe),
        "name": g.get("universe", universe.name),
        "grade": g["grade"],
        "score": g["score"],
        "to_100": 100 - int(g["score"]),
        "dimensions": g.get("dimensions", {}),
        "weakest": sorted(
            ({"key": k, **v, "gap": v["max"] - v["score"]}
             for k, v in g.get("dimensions", {}).items()),
            key=lambda d: -d["gap"])[:3],
        "progress": progress,
        "plan": workspace.plan(g.get("issues", [])),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe", nargs="?", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-record", action="store_true")
    a = ap.parse_args()

    try:
        universes = workspace.resolve(a.universe)
    except ValueError as e:
        print(json.dumps({"error": str(e)}) if a.json else f"status: {e}")
        return 1

    out = {
        "universes": [report(u, record=not a.no_record) for u in universes],
        "registered": [str(p) for p in workspace.registered()],
        "cwd_universe": str(workspace.find_upward() or ""),
    }

    if a.json:
        print(json.dumps(out, indent=2))
        return 0

    if not out["universes"]:
        print("No universes yet. This is the onboarding moment, not an error.")
        print("Next: `onboard` to install, or `start-new-story-universe` to make one.")
        return 0

    for r in out["universes"]:
        if "error" in r:
            print(f"{r['name']}: could not grade ({r['error']})")
            continue
        d = r["progress"].get("delta")
        move = "" if d is None else (f"  ({d:+d} since {r['progress']['previous']['on']})"
                                     if d else "  (no change)")
        print(f"{r['name']}: {r['grade']} {r['score']}/100{move}")
        p = r["plan"]
        if p["headline"]:
            h = p["headline"]
            print(f"  biggest win : {h['fix']}  [{h['count']} item(s), {h['dimension']}]")
        if p["small"]:
            s = p["small"]
            print(f"  if bored    : {s['fix']}  [{s['count']} item(s), {s['dimension']}]")
        print(f"  {p['total_issues']} open item(s) across {len(p['groups'])} kind(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
