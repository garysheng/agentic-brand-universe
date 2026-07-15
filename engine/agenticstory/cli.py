"""
Agentic Story CLI.

  agenticstory validate <universe>            # structural validation of all canon + stories
  agenticstory list <universe>                # entities + stories
  agenticstory crossovers <universe> <entity> # crossover relations for an entity
  agenticstory assert-story <universe> <id>   # THE pre-render gate for a whole story
  agenticstory assert-spread <universe> --characters a,b [--location X]

Exit code is non-zero when validation/assertion finds problems, so gen scripts
and CI can gate on it.
"""
from __future__ import annotations

import argparse
import sys

from .store import CanonStore
from . import refs


def _print_problems(title: str, problems: list[str]) -> int:
    if problems:
        print(f"{title}: {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"{title}: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="agenticstory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "list"):
        s = sub.add_parser(name); s.add_argument("universe")
    c = sub.add_parser("crossovers"); c.add_argument("universe"); c.add_argument("entity")
    a = sub.add_parser("assert-story"); a.add_argument("universe"); a.add_argument("story")
    sp = sub.add_parser("assert-spread"); sp.add_argument("universe")
    sp.add_argument("--characters", default=""); sp.add_argument("--location", default="")

    args = ap.parse_args(argv)
    store = CanonStore(args.universe)

    if args.cmd == "validate":
        return _print_problems(f"validate [{store.manifest.get('name', store.dir.name)}]",
                               store.validate_canon())
    if args.cmd == "list":
        print(f"universe: {store.manifest.get('name')}  (assetRoot={store.asset_root})")
        print("entities:")
        for e in store.entities.values():
            tags = [e.kind]
            if e.real_person:
                tags.append("REAL:" + (e.real_person.get("approval", {}).get("state", "?")))
            if e.kind in ("setting", "visual-metaphor"):
                tags.append("locked" if e.is_locked_setting() else "UNLOCKED")
            print(f"  {e.id:24s} [{', '.join(tags)}]")
        print("stories:")
        for s in store.stories.values():
            print(f"  {s.id:24s} spine={s.raw.get('spine')} features={len(s.features)} beats={len(s.beats)}")
        return 0
    if args.cmd == "crossovers":
        rels = store.crossovers(args.entity)
        if not rels:
            print(f"no crossovers for '{args.entity}'"); return 0
        for r in rels:
            other = r.to if r.from_ == args.entity else r.from_
            print(f"  {args.entity} × {other}  ({r.raw.get('story', '?')}): {r.raw.get('note', '')}")
        return 0
    if args.cmd == "assert-story":
        return _print_problems(f"assert-story [{args.story}]",
                               refs.assert_story(store, args.story))
    if args.cmd == "assert-spread":
        chars = [c.strip() for c in args.characters.split(",") if c.strip()]
        return _print_problems(f"assert-spread [{', '.join(chars)}{' @ ' + args.location if args.location else ''}]",
                               refs.assert_spread(store, chars, args.location or None))
    return 2


if __name__ == "__main__":
    sys.exit(main())
