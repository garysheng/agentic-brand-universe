"""
Agentic Brand Universe CLI.

  abu validate <universe>            # structural validation of all canon + stories
  abu list <universe>                # entities + stories
  abu list-craft <universe>          # craft-canon records (spine/genre/register-rule)
  abu crossovers <universe> <entity> # crossover relations for an entity
  abu assert-story <universe> <id>   # THE pre-render gate for a whole story
  abu assert-spread <universe> --characters a,b [--location X]
  abu lock-level <universe> <entity>  # advisory reference-completeness report
  abu build-canon <universe> [--check|--adopt]  # regenerate CANON.md from per-record files
  abu build-docs [--root R] [--check]  # regenerate THIS repo's derived docs (README, REFERENCE)
  abu add-entity <universe> <kind> <eid> [--name N] [--origin S] [--photo path ...]
                                               # scaffold a schema-valid entity stub
  abu archive <universe> <eid> --reason R [--superseded-by ID]
                                               # retire an entity from NEW casting
  abu unarchive <universe> <eid>      # put a retired entity back in service
  abu archived <universe> [--story ID] # what is retired, and who still casts it

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


def build_parser() -> argparse.ArgumentParser:
    """The CLI surface, as data.

    Extracted from `main` so it can be introspected without being run. `docsfile`
    walks these subparsers to emit the CLI reference, which is why every verb
    carries a `help=`: a verb with no help renders as a blank row in the docs,
    and a blank row is how an undocumented verb hides in plain sight.
    """
    ap = argparse.ArgumentParser(prog="abu")
    sub = ap.add_subparsers(dest="cmd", required=True)
    va = sub.add_parser("validate", help="typecheck a universe against the spec schema")
    va.add_argument("universe")
    li = sub.add_parser("list", help="list every entity in a universe")
    li.add_argument("universe")
    lc = sub.add_parser("list-craft", help="list a universe's craft-canon records")
    lc.add_argument("universe")
    c = sub.add_parser("crossovers", help="list the crossovers an entity appears in")
    c.add_argument("universe"); c.add_argument("entity")
    rel = sub.add_parser("relations", help="list an entity's typed relations")
    rel.add_argument("universe"); rel.add_argument("entity")
    a = sub.add_parser("assert-story", help="the pre-render gate: refuse a story whose cast lacks real art on disk")
    a.add_argument("universe"); a.add_argument("story")
    sp = sub.add_parser("assert-spread", help="the pre-render gate for ONE spread's cast and location")
    sp.add_argument("universe")
    sp.add_argument("--characters", default=""); sp.add_argument("--location", default="")
    ll = sub.add_parser("lock-level", help="report how locked an entity is (which matrix slots are filled)")
    ll.add_argument("universe"); ll.add_argument("entity")
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

    msc = sub.add_parser("massing-scaffold",
                         help="write a STARTER massing spec for a rectangular room (shell + "
                              "opposed cameras + notes stub) to edit, so authoring a blueprint "
                              "does not start from a blank file")
    msc.add_argument("title", help="the room's name, e.g. \"Hagin's sickroom\"")
    msc.add_argument("--size", required=True, metavar="WxDxH",
                     help="room size as width x depth x height, e.g. 3.6x3.6x2.4. "
                          "Z is up and the origin is the near-left floor corner.")
    msc.add_argument("--out", required=True, help="output massing spec JSON path")
    msc.add_argument("--cameras", default="c1-master,c2-reverse",
                     help="comma-separated camera ids. A fragment of master/reverse/left/right "
                          "picks that preset placement (default: c1-master,c2-reverse). Two "
                          "OPPOSED cameras by default, because handedness is a property of the "
                          "camera and one camera cannot state it.")
    msc.add_argument("--eye-height", type=float, default=1.55)
    msc.add_argument("--force", action="store_true", help="overwrite an existing spec")

    el = sub.add_parser("elevation", help="render an OBJECT's blueprint as a code-built 2D elevation sheet "
                                         "from a declarative spec (deterministic, no model, no cost)")
    el.add_argument("spec", help="path to the elevation spec JSON (parts + scale + laws)")
    el.add_argument("--out", required=True, help="output PNG path (the entity's contract.blueprint)")
    el.add_argument("--universe", default=None, help="universe path, recorded in the provenance recipe")
    el.add_argument("--entity", default=None, help="entity id, recorded in the provenance recipe")
    el.add_argument("--no-recipe", action="store_true", help="skip writing <out>.recipe.json")

    ae = sub.add_parser("add-entity", help="scaffold a schema-valid entity stub with reference-matrix slots")
    ae.add_argument("universe"); ae.add_argument("kind"); ae.add_argument("eid")
    ae.add_argument("--name", default=""); ae.add_argument("--origin", default=None)
    ae.add_argument("--photo", action="append", default=None, help="a photo-stack path (repeatable)")
    bc = sub.add_parser("build-canon", help="regenerate CANON.md from canon/properties + canon/crossovers")
    bc.add_argument("universe")
    bc.add_argument("--check", action="store_true", help="fail if stale or if any crossover number is duplicated")
    bc.add_argument("--adopt", action="store_true", help="create records for hand-appended rows with no backing record")
    bp = sub.add_parser("backfill-provenance",
                        help="record provenance for art that predates the adapter, without "
                             "regenerating it (never invokes a model)")
    bp.add_argument("universe")
    bp.add_argument("--apply", action="store_true",
                    help="write the recipes; without this it reports the plan and changes nothing")
    bp.add_argument("--entity",
                    help="scope the sweep to one entity's reference/<id>/ subtree, so a "
                         "one-character backfill is a reviewable diff instead of a "
                         "whole-universe rewrite (backfill-prompts already had this)")
    ia = sub.add_parser("import-asset",
                        help="bring an asset made OUTSIDE this universe INTO it, writing its "
                             "provenance chain as a side effect of the copy")
    ia.add_argument("universe")
    ia.add_argument("dest", nargs="?", default=None,
                    help="universe-relative destination path for a single import")
    ia.add_argument("--from", dest="src", default=None, help="the source file to import")
    ia.add_argument("--manifest", default=None,
                    help="import a BATCH from an import manifest (see docs); refuses the "
                         "whole batch before copying anything")
    ia.add_argument("--dest-dir", default=None,
                    help="universe-relative directory every manifest item lands in")
    ia.add_argument("--prompts", default=None,
                    help="JSON map of source-path (or stem) -> the prompt that generated it, "
                         "folded into each item's recipe as sourcePrompt")
    ia.add_argument("--provenance", default="derived", choices=("derived", "source"),
                    help="derived = a stated transform of a known asset (default); "
                         "source = an original input such as a photograph")
    ia.add_argument("--from-repo", default=None, help="the repo the source lives in")
    ia.add_argument("--from-path", default=None, help="the source's path inside that repo")
    ia.add_argument("--from-sha", default=None, help="sha256 (or 16-char prefix) of the source")
    ia.add_argument("--crop", default=None, help="crop box applied to the source: x0,y0,x1,y1")
    ia.add_argument("--source-generator", default=None, help="what generated the SOURCE")
    ia.add_argument("--source-prompt", default=None, help="the prompt that generated the SOURCE")
    ia.add_argument("--source-prompt-file", default=None, help="read --source-prompt from a file")
    ia.add_argument("--blessed-by", default=None, help="who approved this asset, and when")
    ia.add_argument("--note", default=None, help="override the recipe's default note")
    ia.add_argument("--force", action="store_true", help="overwrite an existing destination")
    ia.add_argument("--dry-run", action="store_true", help="report the plan; copy nothing")
    bpr = sub.add_parser("backfill-prompts",
                         help="recover a scaffolded prompts.md from the recipes beside it, so "
                              "a matrix shot outside the framework still records its prompts")
    bpr.add_argument("universe")
    bpr.add_argument("--apply", action="store_true",
                     help="write the prompts.md files; without this it reports the plan and changes nothing")
    bpr.add_argument("--entity", action="append", default=None,
                     help="scope to one entity id (repeatable); default is the whole universe")
    bd = sub.add_parser("build-docs", help="regenerate the framework's own derived docs (README + docs/REFERENCE.md)")
    bd.add_argument("--root", default=None,
                    help="framework repo root (default: inferred from this module's location)")
    bd.add_argument("--check", action="store_true",
                    help="fail if any generated block is stale, instead of rewriting it")
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
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if args.cmd == "massing-scaffold":
        from . import massing as _massing
        try:
            w, d, h = (float(x) for x in str(args.size).lower().split("x"))
        except ValueError:
            print(f"massing-scaffold: --size must be WxDxH, got {args.size!r}", file=sys.stderr)
            return 2
        outp = Path(args.out)
        if outp.exists() and not args.force:
            print(f"massing-scaffold: {args.out} exists (pass --force to overwrite). "
                  f"A scaffold that silently overwrote an authored spec would lose the "
                  f"furniture, which is the only part a human wrote.", file=sys.stderr)
            return 2
        spec = _massing.scaffold_room(
            args.title, w, d, h,
            cameras=[c.strip() for c in args.cameras.split(",") if c.strip()],
            eye_height=args.eye_height)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(spec, indent=2) + "\n")
        print(f"wrote {args.out}: an empty {w} x {d} x {h} shell with "
              f"{len(spec['cameras'])} camera(s).")
        print("  Next: add the furniture as boxes (agenticstory.massing.box / quad), answer the")
        print("  TODO notes, then render it: abu massing " + args.out + " --out <blueprint>.png")
        return 0

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

    # elevation is massing's 2D sibling: an OBJECT is argued flat and head-on, not from a
    # camera, so it declares parts in the object's own units instead of solids and cameras.
    # Like massing it reads no canon and stays usable before a universe exists.
    if args.cmd == "elevation":
        from . import elevation as _elev
        from . import SPEC_VERSION as _SV
        spec = json.load(open(args.spec))
        out = _elev.render_sheet(spec, args.out)
        print(f"wrote {out}")
        if not args.no_recipe:
            rec = _elev.write_recipe(out, args.spec, universe=args.universe,
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

    if args.cmd == "import-asset":
        from pathlib import Path as _P
        from . import importing
        u = _P(args.universe)
        try:
            if args.manifest:
                r = importing.import_manifest(
                    u, _P(args.manifest), spec_version=SPEC_VERSION,
                    dest=args.dest_dir, prompts=_P(args.prompts) if args.prompts else None,
                    force=args.force, dry_run=args.dry_run)
                if args.dry_run:
                    print(f"import-asset [{u.name}]: would import {r['planned']} asset(s)")
                    for it in r["items"]:
                        print(f"  {it['to']}  <- {it['from']}  [{it['provenance']}"
                              f"{', +sourcePrompt' if it['hasPrompt'] else ''}]")
                    print("  (dry run; nothing copied)")
                    return 0
                print(f"import-asset [{u.name}]: imported {r['written']}/{r['planned']} asset(s), "
                      f"{r['withSourcePrompt']} carrying the source prompt")
                for a in r["items"]:
                    print(f"  {a}")
                return 0
            if not (args.src and args.dest):
                print("import-asset: need `--from <src> <dest>` or `--manifest <file>`")
                return 2
            crop = None
            if args.crop:
                crop = [int(x) for x in args.crop.replace(" ", "").split(",")]
            prompt = args.source_prompt
            if args.source_prompt_file:
                prompt = _P(args.source_prompt_file).read_text().strip()
            df = {k: v for k, v in (("repo", args.from_repo), ("path", args.from_path),
                                    ("sha256", args.from_sha),
                                    ("generator", args.source_generator)) if v}
            if args.dry_run:
                print(f"import-asset [{u.name}]: would import {args.src} -> {args.dest} "
                      f"[{args.provenance}] (dry run; nothing copied)")
                return 0
            rec = importing.import_one(
                u, _P(args.src), args.dest, spec_version=SPEC_VERSION, force=args.force,
                provenance=args.provenance, derived_from=df or None,
                transform={"crop": crop} if crop else None, prompt=prompt,
                blessed_by=args.blessed_by, note=args.note, default_repo=args.from_repo)
            print(f"import-asset [{u.name}]: {args.dest}")
            print(f"  provenance -> {_P(rec['asset']).name}.recipe.json [{rec['provenance']}]")
            return 0
        except importing.ImportRefusal as e:
            print(f"import-asset REFUSED: {e}")
            return 1

    if args.cmd == "backfill-provenance":
        from pathlib import Path as _P
        from . import provenance
        u = _P(args.universe)
        ent = getattr(args, "entity", None)
        r = (provenance.apply if args.apply else provenance.plan)(u, SPEC_VERSION, ent)
        scope = f" [{ent} only]" if ent else ""
        print(f"backfill-provenance [{u.name}]{scope}: "
              f"{r['already_have_recipe']}/{r['total_images']} "
              f"already had a recipe; {r['to_backfill']} to backfill")
        for kind, n in sorted(r["by_kind"].items(), key=lambda kv: -kv[1]):
            print(f"  {n:5} {kind}")
        if r["rerunnable_for_true_recipe"]:
            print(f"  note: {r['rerunnable_for_true_recipe']} are code-built; re-run "
                  f"`abu massing`/`elevation` from their specs for a TRUE recipe, free.")
        if args.apply:
            print(f"  wrote {r['written']} recipe file(s)")
        else:
            print("  (plan only; pass --apply to write)")
        print("  NOTE: no image was regenerated. Locked goldens are never re-rendered "
              "to repair metadata.")
        return 0

    if args.cmd == "backfill-prompts":
        from pathlib import Path as _P
        from . import promptsfile
        u = _P(args.universe)
        r = promptsfile.run(u, apply=args.apply, only=args.entity)
        verb = "filled" if args.apply else "would fill"
        print(f"backfill-prompts [{u.name}]: {verb} {r['filled']} shot prompt(s) from recipes, "
              f"{r['appended']} of them into slots the scaffold never had; "
              f"{r['still_todo']} shot(s) have no recipe and stay TODO (never shot).")
        for f in r["files"]:
            if not (f["filled"] or f["appended"]):
                continue
            rel = _P(f["path"]).parent.name
            got = ", ".join(s for s, _ in f["filled"]) or "-"
            line = f"  {rel}: {len(f['filled'])} from recipe ({got})"
            if f["appended"]:
                line += f"; APPENDED {', '.join(s for s, _ in f['appended'])} (slot missing)"
            if f["still_todo"]:
                line += f"; {len(f['still_todo'])} unshot"
            print(line)
        if not args.apply:
            print("  (plan only; pass --apply to write)")
        print("  An authored body is never overwritten, so a re-run is a no-op.")
        return 0

    if args.cmd == "build-docs":
        from pathlib import Path as _P
        from . import docsfile
        droot = _P(args.root) if args.root else docsfile.repo_root()
        if args.check:
            return _print_problems("build-docs --check", docsfile.check(droot))
        changed = docsfile.build(droot)
        if not changed:
            print("build-docs: already current")
        else:
            print(f"build-docs: regenerated {len(changed)} file(s)")
            for c in changed:
                print(f"  ~ {c}")
        return _print_problems("build-docs", [p for p in docsfile.check(droot)
                                              if "stale" not in p and "missing" not in p])

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
            # Lifecycle is the FIRST thing a reader needs and was the one thing this
            # listing hid: an archived entity printed identically to an active one, so
            # `list` invited a casting decision it had already been retired from.
            if e.is_archived:
                sup = e.superseded_by
                tags.append("ARCHIVED" + (f" -> {sup}" if sup else ""))
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
