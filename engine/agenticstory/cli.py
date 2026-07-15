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
from . import refs, scaffold, SPEC_VERSION, SPEC_WIKI


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
    rel = sub.add_parser("relations"); rel.add_argument("universe"); rel.add_argument("entity")
    a = sub.add_parser("assert-story"); a.add_argument("universe"); a.add_argument("story")
    sp = sub.add_parser("assert-spread"); sp.add_argument("universe")
    sp.add_argument("--characters", default=""); sp.add_argument("--location", default="")
    ini = sub.add_parser("init", help="scaffold a new universe (conforms to spec v" + SPEC_VERSION + ")")
    ini.add_argument("universe", help="target directory for the new universe")
    ini.add_argument("--name", required=True, help="universe name (slug)")
    ini.add_argument("--asset-root", default=".", help="where entity asset paths resolve (default: the universe dir)")
    ini.add_argument("--example", action="store_true", help="also scaffold a worked example (character/setting/story/relation)")
    ini.add_argument("--force", action="store_true", help="overwrite an existing universe.json")

    args = ap.parse_args(argv)

    # init does not load a store (the universe does not exist yet)
    if args.cmd == "init":
        try:
            written = scaffold.scaffold_universe(
                args.universe, name=args.name, asset_root=args.asset_root,
                example=args.example, force=args.force)
        except FileExistsError as e:
            print(f"init: {e}"); return 1
        print(f"init [{args.name}]: scaffolded {len(written)} file(s), conforms to spec v{SPEC_VERSION} ({SPEC_WIKI})")
        for p in written:
            print(f"  + {p}")
        # confirm the scaffold is structurally valid out of the box
        problems = CanonStore(args.universe).validate_canon()
        print("next: `validate` →", "OK" if not problems else f"{len(problems)} problem(s): {problems}")
        print("      then `assert-story <id>` before rendering (it refuses until real assets exist).")
        return 0 if not problems else 1

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
    if args.cmd == "relations":
        rels = store.relations_of(args.entity)
        if not rels:
            print(f"no relations for '{args.entity}'"); return 0
        for r in rels:
            arrow = "→" if r.from_ == args.entity else "←"
            other = r.to if r.from_ == args.entity else r.from_
            print(f"  {r.rel:16s} {arrow} {other:22s} {r.raw.get('note', '')}")
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
