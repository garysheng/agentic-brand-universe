"""
Agentic Story CLI.

  agenticstory validate <universe>            # structural validation of all canon + stories
  agenticstory list <universe>                # entities + stories
  agenticstory list-craft <universe>          # craft-canon records (spine/genre/register-rule)
  agenticstory crossovers <universe> <entity> # crossover relations for an entity
  agenticstory assert-story <universe> <id>   # THE pre-render gate for a whole story
  agenticstory assert-spread <universe> --characters a,b [--location X]
  agenticstory lock-level <universe> <entity>  # advisory reference-completeness report
  agenticstory build-canon <universe> [--check|--adopt]  # regenerate CANON.md from per-record files
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
from . import canonfile, refs, scaffold, SPEC_VERSION, SPEC_WIKI


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
    ls2.add_argument("--look", default=None,
                     help="lock this shot into structured.altLooks[LOOK].sheets instead of the "
                          "default matrix, for an alt-look or declared-future era plate. Never "
                          "touches requiredForRender, which is the DEFAULT look's gate")
    ls2.add_argument("--recipe", default=None,
                     help="path to the recipe JSON that produced this shot; freezes provenance "
                          "at approval as <path>.recipe.json so a divergence check can run later")
    ae = sub.add_parser("add-entity", help="scaffold a schema-valid entity stub with reference-matrix slots")
    ae.add_argument("universe"); ae.add_argument("kind"); ae.add_argument("eid")
    ae.add_argument("--name", default=""); ae.add_argument("--origin", default=None)
    ae.add_argument("--photo", action="append", default=None, help="a photo-stack path (repeatable)")
    bc = sub.add_parser("build-canon", help="regenerate CANON.md from canon/properties + canon/crossovers")
    bc.add_argument("universe")
    bc.add_argument("--check", action="store_true", help="fail if stale or if any crossover number is duplicated")
    bc.add_argument("--adopt", action="store_true", help="create records for hand-appended rows with no backing record")
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

    if args.cmd == "build-canon":
        from pathlib import Path as _P
        uroot = _P(args.universe)
        if args.adopt:
            made = canonfile.adopt(uroot)
            print(f"build-canon: adopted {len(made)} orphan row(s)")
            for m in made:
                print(f"  + {m}")
        problems = canonfile.check(uroot)
        if args.check:
            return _print_problems("build-canon --check", problems)
        dupes = [p for p in problems if p.startswith("duplicate")]
        if dupes:
            return _print_problems("build-canon", dupes)
        (uroot / "CANON.md").write_text(canonfile.build(uroot))
        props = len(canonfile.load_properties(uroot))
        xs = len(canonfile.load_crossovers(uroot))
        print(f"build-canon: CANON.md regenerated from {props} property + {xs} crossover record(s)")
        return 0

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
        refdir = uni / "reference" / args.eid
        refdir.mkdir(parents=True, exist_ok=True)
        # Emit the prompts.md skeleton shoot-references reads. Never clobber an
        # existing one: re-scaffolding must not destroy authored prompts.
        promptsp = refdir / "prompts.md"
        if not promptsp.exists():
            from .authoring import prompts_skeleton
            try:
                ident = json.loads((uni / "universe.json").read_text()).get("identity", {})
            except Exception:
                ident = {}
            promptsp.write_text(prompts_skeleton(ent, ident.get("register")))
        if args.photo:
            (uni / "reference" / args.eid / "photos").mkdir(parents=True, exist_ok=True)
        store = CanonStore(uni)
        print(f"wrote {dest.relative_to(uni)}  (lock_level: {refs.lock_level(store, args.eid)})")
        return 0
    if args.cmd == "lock-shot":
        from .authoring import lock_shot, recipe_sidecar_path
        uni = Path(args.universe)
        entp = uni / "canon" / "entities" / f"{args.eid}.json"
        ent = json.loads(entp.read_text())
        recipe = None
        if args.recipe:
            recipe = json.loads(Path(args.recipe).read_text())
        lock_shot(ent, args.shot, args.path, recipe=recipe, root=str(uni), look=args.look)
        entp.write_text(json.dumps(ent, indent=2) + "\n")
        prov = (f"  provenance -> {recipe_sidecar_path(uni / args.path).name}" if recipe is not None
                else "  (no --recipe: un-auditable, no divergence check can run against it)")
        print(f"locked {args.eid}.{args.shot} -> {args.path}  (lock_level: {refs.lock_level(CanonStore(uni), args.eid)}){prov}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
