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
  agenticstory archive <universe> <eid> --reason R [--superseded-by ID]
                                               # retire an entity from NEW casting
  agenticstory unarchive <universe> <eid>      # put a retired entity back in service
  agenticstory archived <universe> [--story ID] # what is retired, and who still casts it

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
    ar = sub.add_parser("archive", help="retire an entity from NEW casting (history keeps rendering)")
    ar.add_argument("universe"); ar.add_argument("eid")
    ar.add_argument("--reason", required=True,
                    help="why it is being retired; an archive with no recorded reason is unauditable")
    ar.add_argument("--superseded-by", default=None,
                    help="the entity an author should cast instead")
    ar.add_argument("--on", default=None, help="ISO date; defaults to today")
    ua = sub.add_parser("unarchive", help="put a retired entity back in service")
    ua.add_argument("universe"); ua.add_argument("eid")
    ad = sub.add_parser("archived", help="list retired entities, or who still casts them")
    ad.add_argument("universe"); ad.add_argument("--story", default=None)
    ls2 = sub.add_parser("lock-shot", help="lock a generated reference shot into an entity")
    ls2.add_argument("universe"); ls2.add_argument("eid"); ls2.add_argument("shot"); ls2.add_argument("path")
    ls2.add_argument("--look", default=None,
                     help="lock this shot into structured.altLooks[LOOK].sheets instead of the "
                          "default matrix, for an alt-look or declared-future era plate. Never "
                          "touches requiredForRender, which is the DEFAULT look's gate")
    ls2.add_argument("--recipe", default=None,
                     help="path to the recipe JSON that produced this shot; freezes provenance "
                          "at approval as <path>.recipe.json so a divergence check can run later")
    ms = sub.add_parser("massing", help="render a setting's blueprint as a code-built 3D massing sheet "
                                        "from a declarative spec (deterministic, no model, no cost)")
    ms.add_argument("spec", help="path to the massing spec JSON (solids + cameras + notes)")
    ms.add_argument("--out", required=True, help="output PNG path (the entity's contract.blueprint)")
    ms.add_argument("--universe", default=None, help="universe path, recorded in the provenance recipe")
    ms.add_argument("--entity", default=None, help="entity id, recorded in the provenance recipe")
    ms.add_argument("--no-recipe", action="store_true", help="skip writing <out>.recipe.json")

    ae = sub.add_parser("add-entity", help="scaffold a schema-valid entity stub with reference-matrix slots")
    ae.add_argument("universe"); ae.add_argument("kind"); ae.add_argument("eid")
    ae.add_argument("--name", default=""); ae.add_argument("--origin", default=None)
    ae.add_argument("--photo", action="append", default=None, help="a photo-stack path (repeatable)")
    bc = sub.add_parser("build-canon", help="regenerate CANON.md from canon/properties + canon/crossovers")
    bc.add_argument("universe")
    bc.add_argument("--check", action="store_true", help="fail if stale or if any crossover number is duplicated")
    bc.add_argument("--adopt", action="store_true", help="create records for hand-appended rows with no backing record")
    ld = sub.add_parser("land", help="merge a finished work branch home, or queue it if that is not safe yet")
    ld.add_argument("repo", help="any git repo (a universe, a platform repo, anything)")
    ld.add_argument("--branch", default=None, help="the work branch (default: the current branch of --repo)")
    ld.add_argument("--onto", default=None, help="target branch (default: main, else master)")
    ld.add_argument("--keep-branch", action="store_true", help="do not delete the work branch after landing")
    ld.add_argument("--keep-worktree", action="store_true", help="do not remove the work branch's worktree after landing")
    ld.add_argument("--drain-only", action="store_true", help="only retry previously queued merges, land nothing new")
    ld.add_argument("--no-drain", action="store_true", help="skip draining the queue first")
    ld.add_argument("--dry-run", action="store_true", help="report what would happen and change nothing")
    ld.add_argument("--prune-stale", action="store_true",
                    help="also remove worktrees whose branch is already fully merged into the target")
    ini = sub.add_parser("init", help="scaffold a new universe (conforms to spec v" + SPEC_VERSION + ")")
    ini.add_argument("universe", help="target directory for the new universe")
    ini.add_argument("--name", required=True, help="universe name (slug)")
    ini.add_argument("--asset-root", default=".", help="where entity asset paths resolve (default: the universe dir)")
    ini.add_argument("--example", action="store_true", help="also scaffold a worked example (character/setting/story/relation)")
    ini.add_argument("--force", action="store_true", help="overwrite an existing universe.json")

    args = ap.parse_args(argv)

    # massing does not load a store: it draws a blueprint from a standalone spec file
    # and never reads canon, so it stays usable before a universe exists.
    if args.cmd == "massing":
        from . import massing as _massing
        from . import SPEC_VERSION as _SV
        spec = json.load(open(args.spec))
        out = _massing.render_sheet(spec, args.out)
        print(f"wrote {out}")
        if not args.no_recipe:
            rec = _massing.write_recipe(out, args.spec, universe=args.universe,
                                        spec_version=_SV, entity=args.entity)
            print(f"wrote {rec}")
        return 0

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

    if args.cmd == "land":
        from . import land as landing
        repo = Path(args.repo)
        results: list[landing.Result] = []
        if not args.no_drain:
            results += landing.drain(repo, dry_run=args.dry_run)
        if not args.drain_only:
            branch = args.branch or landing.current_branch(repo)
            if not branch:
                print("land: --repo is on a detached HEAD and no --branch was given")
                return 2
            onto = args.onto or landing.default_target(repo)
            already = any(r.branch == branch and r.onto == onto for r in results)
            if not already:
                results.append(landing.land(
                    repo, branch, args.onto,
                    delete_branch=not args.keep_branch,
                    remove_worktree=not args.keep_worktree,
                    dry_run=args.dry_run,
                ))
        if not results:
            print("land: nothing to do (queue empty)")
        for r in results:
            print(f"[{r.outcome}] {r.branch} -> {r.onto}: {r.detail}")
            for c in r.cleaned:
                print(f"         {c}")
        if args.prune_stale:
            pruned = landing.prune_stale(repo, dry_run=args.dry_run)
            if pruned:
                print(f"\npruned {len(pruned)} finished worktree(s):")
                for line in pruned:
                    print(f"  {line}")
        else:
            stale = landing.stale_worktrees(repo)
            if stale:
                print(f"\n{len(stale)} worktree(s) hold branches already merged into the target "
                      f"and can be removed (--prune-stale):")
                for w in stale:
                    print(f"  - {w.path}  [{w.branch}]")
        # Only a conflict or a hard error is a failure. A QUEUED merge is a
        # success: the work is safe and a later run finishes it, which is the
        # entire point of the queue.
        return 1 if any(r.outcome in ("conflict", "error") for r in results) else 0

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
    if args.cmd in ("archive", "unarchive"):
        uni = Path(args.universe)
        e = store.entity(args.eid)
        if e is None:
            print(f"unknown entity '{args.eid}'")
            return 1
        path = uni / "canon" / "entities" / f"{args.eid}.json"
        raw = json.loads(path.read_text())
        if args.cmd == "archive":
            import datetime
            raw["lifecycle"] = "archived"
            raw["archived"] = {
                "on": args.on or datetime.date.today().isoformat(),
                "reason": args.reason,
                "supersededBy": args.superseded_by,
            }
            path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
            print(f"archived {args.eid}")
            if args.superseded_by:
                print(f"  cast '{args.superseded_by}' instead")
            # Tell the author what this just made stale, without breaking any of it.
            still = []
            for sid in store.stories:
                if any(args.eid in n for n in refs.archived_casts(store, sid)):
                    still.append(sid)
            if still:
                print(f"  {len(still)} existing stor{'y' if len(still) == 1 else 'ies'} still cast it "
                      f"and REMAIN RENDERABLE (archiving never breaks history):")
                for sid in still:
                    print(f"    - {sid}")
            return 0
        raw.pop("archived", None)
        raw["lifecycle"] = "active"
        path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
        print(f"unarchived {args.eid}")
        return 0
    if args.cmd == "archived":
        if args.story:
            notes = refs.archived_casts(store, args.story)
            if not notes:
                print(f"{args.story}: casts no archived entity")
                return 0
            print(f"{args.story} casts {len(notes)} archived entit(ies):")
            for n in notes:
                print(f"  - {n}")
            return 0
        notes = refs.archived_entities(store)
        if not notes:
            print("no archived entities")
            return 0
        for n in notes:
            print(f"  - {n}")
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
            # `path` is universe-relative (line below, and in every doc example), so a
            # universe-relative --recipe beside it has to work too. It used to resolve
            # ONLY against the CWD, which made the invocation lock-references documents
            # (run from the engine dir, both paths universe-relative) die on
            # FileNotFoundError, pushing callers toward locking with no recipe at all.
            # CWD first keeps every absolute and cwd-relative caller working.
            rp = Path(args.recipe)
            if not rp.is_absolute() and not rp.exists():
                rp = uni / args.recipe
            recipe = json.loads(rp.read_text())
        lock_shot(ent, args.shot, args.path, recipe=recipe, root=str(uni), look=args.look)
        entp.write_text(json.dumps(ent, indent=2) + "\n")
        prov = (f"  provenance -> {recipe_sidecar_path(uni / args.path).name}" if recipe is not None
                else "  (no --recipe: un-auditable, no divergence check can run against it)")
        print(f"locked {args.eid}.{args.shot} -> {args.path}  (lock_level: {refs.lock_level(CanonStore(uni), args.eid)}){prov}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
