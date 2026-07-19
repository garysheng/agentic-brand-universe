"""
Agentic Story CLI.

  agenticstory validate <universe>            # structural validation of all canon + stories
  agenticstory list <universe>                # entities + stories
  agenticstory list-craft <universe>          # craft-canon records (spine/genre/register-rule)
  agenticstory crossovers <universe> <entity> # crossover relations for an entity
  agenticstory assert-story <universe> <id>   # THE pre-render gate for a whole story
  agenticstory assert-spread <universe> --characters a,b [--location X]
  agenticstory lock-level <universe> <entity>  # advisory reference-completeness report
  agenticstory add-entity <universe> <kind> <eid> [--name N] [--origin S] [--photo path ...]
                                               # scaffold a schema-valid entity stub

Exit code is non-zero when validation/assertion finds problems, so gen scripts
and CI can gate on it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    lc = sub.add_parser("list-craft"); lc.add_argument("universe")
    c = sub.add_parser("crossovers"); c.add_argument("universe"); c.add_argument("entity")
    rel = sub.add_parser("relations"); rel.add_argument("universe"); rel.add_argument("entity")
    a = sub.add_parser("assert-story"); a.add_argument("universe"); a.add_argument("story")
    sp = sub.add_parser("assert-spread"); sp.add_argument("universe")
    sp.add_argument("--characters", default=""); sp.add_argument("--location", default="")
    ll = sub.add_parser("lock-level"); ll.add_argument("universe"); ll.add_argument("entity")
    ls2 = sub.add_parser("lock-shot", help="lock a generated reference shot into an entity")
    ls2.add_argument("universe"); ls2.add_argument("eid"); ls2.add_argument("shot"); ls2.add_argument("path")
    ae = sub.add_parser("add-entity", help="scaffold a schema-valid entity stub with reference-matrix slots")
    ae.add_argument("universe"); ae.add_argument("kind"); ae.add_argument("eid")
    ae.add_argument("--name", default=""); ae.add_argument("--origin", default=None)
    ae.add_argument("--photo", action="append", default=None, help="a photo-stack path (repeatable)")
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
    if args.cmd == "list-craft":
        for c in sorted(store.craft.values(), key=lambda c: (c.kind, c.id)):
            print(f"{c.kind:14} {c.id:32} {c.raw.get('name', '')}")
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
    if args.cmd == "lock-level":
        print(refs.lock_level(store, args.entity))
        return 0
    if args.cmd == "add-entity":
        from .authoring import scaffold_entity
        uni = Path(args.universe)
        ent = scaffold_entity(args.kind, args.eid, args.name or args.eid,
                              origin_story=args.origin, photo_stack=args.photo)
        dest = uni / "canon" / "entities" / f"{args.eid}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(ent, indent=2) + "\n")
        (uni / "reference" / args.eid).mkdir(parents=True, exist_ok=True)
        if args.photo:
            (uni / "reference" / args.eid / "photos").mkdir(parents=True, exist_ok=True)
        store = CanonStore(uni)
        print(f"wrote {dest.relative_to(uni)}  (lock_level: {refs.lock_level(store, args.eid)})")
        return 0
    if args.cmd == "lock-shot":
        from .authoring import lock_shot
        uni = Path(args.universe)
        entp = uni / "canon" / "entities" / f"{args.eid}.json"
        ent = json.loads(entp.read_text())
        lock_shot(ent, args.shot, args.path)
        entp.write_text(json.dumps(ent, indent=2) + "\n")
        print(f"locked {args.eid}.{args.shot} -> {args.path}  (lock_level: {refs.lock_level(CanonStore(uni), args.eid)})")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
