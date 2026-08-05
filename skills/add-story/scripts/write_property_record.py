#!/usr/bin/env python3
"""Derive a story's canon/properties/<id>.json from data already on disk.

WHY THIS EXISTS. `universe-doctor` scores a FULL story with no properties
record as its single highest-impact defect, because casting-sweep reads
canon/properties and a story that is missing there is invisible to every
future book's reuse pass. Nothing wrote those records: nation-of-fire
accumulated 173 of them, one whole sweep of which had to be BACKFILLED by
hand on 2026-08-04 with a note apologising that the field "carries the reuse
index" rather than authored curation. That is a manual step every book needs
and no book gets, which is the definition of a path worth paving.

Everything here is DERIVED. The record's `derivedBy` says so, so a later
reader can tell generated bookkeeping from authored curation and rewrite the
`cast` paragraph by hand when the book is next touched.

    write_property_record.py <universe> <story-id> [--render-spec P] [--manifest P]
"""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys

# entity kinds that are NOT part of a casting sweep's reuse index
SKIP_KINDS = {"doctrine", "craft"}


def load(p: pathlib.Path):
    with open(p) as f:
        return json.load(f)


def first_commit(repo: pathlib.Path, rel: str):
    """The day this story's words first landed, read from git, never guessed."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "log", "--diff-filter=A", "--format=%ad",
             "--date=short", "--", rel],
            capture_output=True, text=True, timeout=20)
        lines = [l for l in out.stdout.splitlines() if l.strip()]
        return lines[-1].strip() if lines else None
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe")
    ap.add_argument("story")
    ap.add_argument("--render-spec", default=None,
                    help="the book's render-spec.json; supplies the rendered spread count "
                         "and the book folder, which the story alone does not know")
    ap.add_argument("--manifest", default=None,
                    help="the platform manifest .ts, if the book is already registered")
    ap.add_argument("--order", type=int, default=None,
                    help="explicit order; defaults to one past the highest existing record")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    uroot = pathlib.Path(args.universe).expanduser().resolve()
    sfile = uroot / "stories" / f"{args.story}.json"
    if not sfile.exists():
        print(f"REFUSE: no story at {sfile}", file=sys.stderr)
        return 2
    story = load(sfile)

    props = uroot / "canon" / "properties"
    props.mkdir(parents=True, exist_ok=True)
    out = props / f"{args.story}.json"
    if out.exists():
        print(f"REFUSE: {out} already exists. A properties record is authored curation once "
              f"a human has touched it; delete it deliberately to regenerate.", file=sys.stderr)
        return 2

    # ---- order: one past the highest already recorded ----------------------
    if args.order is not None:
        order = args.order
    else:
        seen = []
        for f in props.glob("*.json"):
            try:
                seen.append(int(load(f).get("order") or 0))
            except Exception:
                pass
        order = (max(seen) + 1) if seen else 1

    # ---- cast: the reuse index a casting sweep actually reads --------------
    cast = set()
    for b in story.get("beats") or []:
        cast.update(b.get("characters") or [])
        if b.get("location"):
            cast.add(b["location"])
    cast.update(story.get("features") or [])
    keep = []
    for eid in sorted(cast):
        ef = uroot / "canon" / "entities" / f"{eid}.json"
        if not ef.exists():
            continue
        if (load(ef).get("kind") or "") in SKIP_KINDS:
            continue
        keep.append(eid)

    # ---- form: what was actually rendered, not what was planned ------------
    beats = len(story.get("beats") or [])
    spreads = None
    home = None
    if args.render_spec:
        rs = pathlib.Path(args.render_spec).expanduser().resolve()
        if rs.exists():
            spec = load(rs)
            spreads = sum(1 for s in spec.get("spreads", [])
                          if str(s.get("id", "")).startswith("spread-"))
            home = spec.get("book")
    genre = story.get("genre") or story.get("spine") or "story"
    form = f"{genre}, {spreads if spreads is not None else '?'} rendered spread(s) in render-spec ({beats} story beats)"

    # ---- status: registered on the platform, or not yet -------------------
    if args.manifest and pathlib.Path(args.manifest).expanduser().exists():
        mf = pathlib.Path(args.manifest).expanduser()
        status = (f"REGISTERED on the platform ({mf.parent.name}/{mf.name}; "
                  f"books.garysheng.com/{args.story})")
    else:
        status = "rendered; not yet registered on the platform"

    logline = " ".join((story.get("logline") or "").split())
    if len(logline) > 900:
        logline = logline[:900].rstrip() + "..."

    refrain = story.get("refrain")
    cast_para = (
        "CAST (reuse index, the field a casting sweep reads): "
        + ", ".join(keep)
        + f". Spine {story.get('spine')}."
        + (f" Genre {story.get('genre')}." if story.get("genre") else "")
        + (f' Refrain "{refrain}".' if refrain else "")
        + f" LOGLINE: {logline}"
    )

    rec = {
        "id": args.story,
        "order": order,
        "property": story.get("title") or args.story,
        "form": form,
        "status": status,
        "home": (f"{uroot.parent.name}/{home}" if home else None),
        "cast": cast_para,
        "derivedBy": (
            "GENERATED by add-story/scripts/write_property_record.py from "
            f"stories/{args.story}.json"
            + (", the book's render-spec" if args.render_spec else "")
            + (" and the platform manifest" if args.manifest else "")
            + ". Every field is derived from data on disk; nothing here is authored "
              "curation. Rewrite the `cast` paragraph by hand when this book is next "
              "touched, to name doctrine, crossovers and dignity rulings the way the "
              "older hand-written records do."),
        "storyFirstCommitted": first_commit(uroot, f"stories/{args.story}.json"),
    }

    if args.dry_run:
        print(json.dumps(rec, indent=2, ensure_ascii=False))
        return 0
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out}  (order {order}, {len(keep)} cast entities)")
    print("Now run: abu build-canon <universe>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
