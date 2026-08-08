#!/usr/bin/env python3
"""Normalize a legacy prompts.md to the canonical heading dialect, in place.

chain_matrix parses exactly one heading form:

    ## <shot-stem>  -> reference/<entity>/<shot-stem>.png  [(WxH)]

The wild carries every dialect that predates it, and each one reads as a refusal
whose remedy used to be a hand edit. All of these were hand-rewritten during one
sweep (2026-08-07), six separate times across ten files:

    ## face-neutral                                       (no arrow at all)
    ## master (1536x1024) → `master.png`                  (unicode arrow, bare filename)
    ## master (state 1: open-fire) → `reference/...png`   (prose in the name)
    ## single-ida -> `reference/.../single-ida.png`       (backticked path; fine, kept)
    ## Era variants (...)                                 (prose section at level 2)

This tool does that rewrite once, mechanically, and reports what it cannot decide:

- A level-2 heading WITH a resolvable path (arrow of either kind, backticks or
  not, bare filename or full path) becomes canonical. The stem comes from the
  FILE, which is what the parser keys on.
- A level-2 heading with NO path and a name that is not a known matrix slot is
  PROSE and is demoted to level-3.
- A heading with no path whose name IS a declared sheet key or standard slot
  gets the path derived from the entity id.
- Declared sheet keys whose key differs from their file stem (camelCase key over
  kebab file) are REPORTED: the fix is a sheet alias in the entity, which this
  tool does not edit.

Dry-run by default; --write applies. Always show the diff to a human.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

STANDARD_SLOTS = {
    "face-neutral", "face-3q", "expressions", "forward-fullbody",
    "profile-left", "profile-right", "back", "signature-pose",
    "turnaround", "blueprint", "master", "blocking", "scale",
}

HEAD = re.compile(r"^## (?P<name>[^\n]+?)\s*$", re.M)
# an arrow of either dialect followed by something that ends in .png
PATHY = re.compile(
    r"(?:->|→)\s*`?(?P<path>[\w./-]+?\.png)`?\s*(?:\((?P<size>\d+x\d+)\))?\s*$"
)
LEAD_SIZE = re.compile(r"\((?P<size>\d+x\d+)\)")


def canonical(stem: str, eid: str, size: str | None) -> str:
    tail = f"  ({size})" if size else ""
    return f"## {stem}  -> reference/{eid}/{stem}.png{tail}"


def normalize(text: str, eid: str, declared: dict[str, str]) -> tuple[str, list[str]]:
    notes: list[str] = []
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        if not line.startswith("## "):
            out.append(line)
            continue
        name = line[3:].strip()
        m = PATHY.search(name)
        if m:
            stem = Path(m.group("path")).stem
            size = m.group("size")
            if not size:
                lm = LEAD_SIZE.search(name[: m.start()])
                size = lm.group("size") if lm else None
            out.append(canonical(stem, eid, size))
            continue
        # no path: a slot name gets one derived; anything else is prose
        bare = name.split("(")[0].strip()
        if bare in declared or bare in STANDARD_SLOTS:
            lm = LEAD_SIZE.search(name)
            out.append(canonical(bare, eid, lm.group("size") if lm else None))
            continue
        out.append("###" + line[2:])
        notes.append(f"demoted prose heading to level-3: {name!r}")
    for key, path in declared.items():
        stem = Path(path).stem
        if key != stem:
            notes.append(
                f"sheet key {key!r} differs from its file stem {stem!r}: the parser "
                f"keys on the stem, so add a sheet alias {stem!r} -> {path!r} in the "
                f"entity (this tool does not edit canon)"
            )
    return "\n".join(out), notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("universe")
    ap.add_argument("entity")
    ap.add_argument("--write", action="store_true", help="apply (default: dry-run diff)")
    args = ap.parse_args(argv)
    uroot = Path(args.universe).expanduser()
    pm = uroot / "reference" / args.entity / "prompts.md"
    ent = uroot / "canon" / "entities" / f"{args.entity}.json"
    if not pm.exists():
        print(f"REFUSE: {pm} does not exist", file=sys.stderr)
        return 2
    declared = {}
    if ent.exists():
        declared = (json.loads(ent.read_text()).get("structured") or {}).get("sheets") or {}
    before = pm.read_text()
    after, notes = normalize(before, args.entity, declared)
    if after == before and not notes:
        print(f"{pm.name}: already canonical")
        return 0
    for n in notes:
        print(f"  note: {n}")
    diff = difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile=str(pm), tofile=str(pm) + " (normalized)",
    )
    sys.stdout.writelines(d for d in diff if d.startswith(("---", "+++", "@@", "+##", "-##")))
    if args.write:
        pm.write_text(after)
        print(f"\nwrote {pm}")
    else:
        print("\ndry-run: pass --write to apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
