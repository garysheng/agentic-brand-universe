#!/usr/bin/env python3
"""Translate a render-spec out of the retired NoF `compile_render.py` dialect.

THE PROMISE THIS KEEPS. `assemble_prompt.py`'s BAKE-USED-AS-A-SELECTOR refusal has
named `migrate_render_spec.py` since the day the guard shipped, and no such file
existed anywhere in the repo: the refusal pointed every operator at a phantom tool.
The takeoff-thursdays run (hyperagentic-age, 2026-08) hand-rolled the bake-to-plate
translation as declared debt, which is the second hand-roll of the same translation
and therefore the framework's bug to fix. Either the tool ships or the refusal stops
naming it; this ships the tool.

WHAT IT TRANSLATES. In the retired dialect, `bake` on a cast entry SELECTED which
locked reference state to pass. In the current assembler `bake` is FREE PROSE, and
the selector is `plate` (non-characters) / `pose` (characters). For every cast entry
whose `bake` is really a selector, this sets the right selector field and drops the
bake. Detection is `assemble_prompt.bake_selector_hit`, the SAME predicate the
refusal fires on, so a translated spec cannot still be refused for the entry it
translated.

Dry-run by default; `--write` rewrites the spec in place (previous bytes saved
beside it as `<spec>.pre-migrate.bak`).

Usage:
  migrate_render_spec.py translate <universe> <spec> [--write]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from assemble_prompt import bake_selector_hit  # noqa: E402


def load(p: Path):
    with open(p) as f:
        return json.load(f)


def translate(uroot: Path, spec: dict) -> list[dict]:
    """Mutate `spec` in place; return one row per rewritten cast entry."""
    rows: list[dict] = []
    ent_cache: dict[str, dict | None] = {}
    for sp in spec.get("spreads", []):
        for c in sp.get("cast", []):
            eid = c.get("id")
            if not eid or not c.get("bake"):
                continue
            if eid not in ent_cache:
                p = uroot / "canon" / "entities" / f"{eid}.json"
                ent_cache[eid] = load(p) if p.exists() else None
            ent = ent_cache[eid]
            if ent is None:
                continue  # assemble refuses unknown ids with its own message
            hit = bake_selector_hit(c.get("bake"), ent)
            if not hit:
                continue
            field, key = hit
            old = c.pop("bake")
            c[field] = key
            rows.append({"spread": sp.get("id"), "cast": eid,
                         "bake": old, "field": field, "key": key})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("verb", choices=["translate"])
    ap.add_argument("universe")
    ap.add_argument("spec")
    ap.add_argument("--write", action="store_true",
                    help="rewrite the spec in place (default is a dry run that only reports)")
    args = ap.parse_args()

    uroot = Path(args.universe)
    if not (uroot / "canon" / "entities").is_dir():
        print(f"REFUSE: {uroot} is not a universe (no canon/entities/)", file=sys.stderr)
        return 2
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"REFUSE: no such spec: {spec_path}", file=sys.stderr)
        return 2
    original = spec_path.read_text()
    spec = json.loads(original)

    rows = translate(uroot, spec)
    if not rows:
        print("nothing to translate: no cast entry's `bake` names one of its own "
              "reference slots (the spec is not in the retired dialect, or already migrated)")
        return 0

    for r in rows:
        print(f"{r['spread']} / {r['cast']}: bake={r['bake']!r} -> "
              f"\"{r['field']}\": \"{r['key']}\"")
    if not args.write:
        print(f"\nDRY RUN: {len(rows)} entr{'y' if len(rows) == 1 else 'ies'} would be "
              f"rewritten. Re-run with --write to apply.")
        return 0

    bak = spec_path.with_suffix(spec_path.suffix + ".pre-migrate.bak")
    bak.write_text(original)
    spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    print(f"\nWROTE {spec_path} ({len(rows)} entries translated; previous bytes at {bak.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
